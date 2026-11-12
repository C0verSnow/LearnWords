import json
import sqlite3
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path

from src.anki import MODEL_ID, build_package
from src.archive import build_archive
from src.content import FIELDS, parse_content
from src.pronunciation import pronunciation
from src.vocabulary import select_words


class CardTests(unittest.TestCase):
    def test_word_selection_normalizes_deduplicates_and_excludes_delivered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "words.txt"
            path.write_text("\ufeffApproach\n\ncontext\nAPPROACH\ninvalid 12\ncan't\nwell-known\n", encoding="utf-8")
            self.assertEqual(select_words(path, {"context": {}}, 10, "next"),
                             ["approach", "can't", "well-known"])
            selected = select_words(path, {}, 2, "random")
            self.assertEqual(len(set(selected)), 2)
            self.assertTrue(set(selected) <= {"approach", "context", "can't", "well-known"})

    def test_content_rejects_missing_empty_and_wrong_word(self):
        data = {"Word": "context", **dict.fromkeys(FIELDS, "说明")}
        self.assertEqual(parse_content("```json\n" + json.dumps(data) + "\n```", "context"), data)
        for invalid in ({}, {**data, "Word": "other"}, {**data, "Examples": []},
                        {**data, "Usage": " "}):
            with self.assertRaises(ValueError):
                parse_content(json.dumps(invalid), "context")

    def test_real_speech_apkg_guid_media_html_and_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card = {"Word": "carbon dioxide", **dict.fromkeys(FIELDS, "<script> & 例句\n翻译"),
                    **pronunciation("carbon dioxide", root / "media")}
            for accent in ("UK", "US"):
                self.assertTrue(card[f"IPA_{accent}"])
                with wave.open(card[f"Audio_{accent}"]) as sound:
                    self.assertGreater(sound.getnframes(), 100)
            apkg = root / "cards.apkg"
            build_package([card], apkg)
            first_guid = None
            for iteration in range(2):
                if iteration:
                    card["Meaning"] = "更新解释"
                    build_package([card], apkg)
                with zipfile.ZipFile(apkg) as package:
                    media = json.loads(package.read("media"))
                    self.assertEqual(set(media.values()), {"learnword_carbon dioxide_uk.wav", "learnword_carbon dioxide_us.wav"})
                    for name in media:
                        self.assertGreater(len(package.read(name)), 44)
                    database = root / f"collection-{iteration}.anki2"
                    database.write_bytes(package.read("collection.anki2"))
                with sqlite3.connect(database) as connection:
                    notes = connection.execute("SELECT guid, mid, flds FROM notes").fetchall()
                    self.assertEqual(len(notes), 1)
                    guid, model_id, fields = notes[0]
                    self.assertEqual(model_id, MODEL_ID)
                    self.assertIn("[sound:learnword_carbon dioxide_us.wav]", fields)
                    self.assertIn("&lt;script&gt; &amp;", fields)
                    self.assertNotIn("<script>", fields)
                    if first_guid:
                        self.assertEqual(guid, first_guid)
                    first_guid = guid
            archive = root / "cards.zip"
            manifest = {"requested": 20, "succeeded": ["carbon dioxide"], "stage": "packaged"}
            build_archive(apkg, manifest, archive)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), {"LearnWord.apkg", "manifest.json", "README.txt"})
                self.assertEqual(json.loads(package.read("manifest.json")), manifest)
                self.assertEqual(package.read("LearnWord.apkg"), apkg.read_bytes())
