import tempfile
import unittest
from pathlib import Path

from scripts.import_vocabulary import import_vocabulary
from src.vocabulary import select_words

ROOT = Path(__file__).resolve().parents[1]


class VocabularyTests(unittest.TestCase):
    def test_csv_import_preserves_order_phrases_and_ignores_other_columns(self):
        source = ('\ufeffword,meaning,sort,title,phonetic\n'
                  'Atmosphere,"大气,气氛",1,自然地理,/test/\n'
                  'carbon   dioxide,二氧化碳,1,自然地理,/test/\n'
                  'ATMOSPHERE,大气,2,其他章节,/test/\n'
                  "can't,不能,2,其他章节,/test/\n"
                  'well-known,著名,2,其他章节,/test/\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vocabulary.txt"
            self.assertEqual(import_vocabulary(source, path), 4)
            self.assertEqual(path.read_text(), "atmosphere\ncarbon dioxide\ncan't\nwell-known\n")
            self.assertEqual(select_words(path, {"atmosphere": {}}, 10, "next"),
                             ["carbon dioxide", "can't", "well-known"])

    def test_invalid_csv_does_not_overwrite_vocabulary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vocabulary.txt"
            path.write_text("original\n")
            for source in ("meaning\n解释\n", "word\n", "word\nvalid\ninvalid 12\n",
                           "word\nvalid\n\"\"\n", "word,meaning\n,解释\n"):
                with self.subTest(source=source), self.assertRaises(ValueError):
                    import_vocabulary(source, path)
                self.assertEqual(path.read_text(), "original\n")

    def test_committed_ielts_vocabulary_is_complete_and_selectable(self):
        path = ROOT / "docs/words/vocabulary.txt"
        words = path.read_text().splitlines()
        self.assertEqual(len(words), 3592)
        self.assertEqual(len(set(words)), 3592)
        self.assertEqual(words[:3], ["atmosphere", "hydrosphere", "lithosphere"])
        self.assertEqual(words[-1], "incidentally")
        self.assertEqual(select_words(path, {}, 4000, "next"), words)
        phrases = {"carbon dioxide", "el nino", "bush fire", "dining hall", "ice cream",
                   "living room", "new zealand", "heart attack", "health care"}
        self.assertEqual({word for word in words if " " in word}, phrases)
        generated = dict.fromkeys(words[:-1], {})
        self.assertEqual(select_words(path, generated, 100, "next"), ["incidentally"])
        self.assertEqual(select_words(path, generated, 100, "random"), ["incidentally"])
        self.assertEqual(select_words(path, dict.fromkeys(words), 100, "next"), [])
