import html
from pathlib import Path

import genanki

from src.config import ROOT
from src.content import FIELDS

MODEL_ID = 1794210801
DECK_ID = 1794210802
NOTE_FIELDS = ("Word", "IPA_UK", "IPA_US", "Audio_UK", "Audio_US", *FIELDS)


def build_package(cards, path):
    templates = ROOT / "templates"
    model = genanki.Model(MODEL_ID, "LearnWord v1",
                          fields=[{"name": key} for key in NOTE_FIELDS],
                          templates=[{"name": "Word", "qfmt": (templates / "front.html").read_text(),
                                      "afmt": (templates / "back.html").read_text()}],
                          css=(templates / "style.css").read_text())
    deck = genanki.Deck(DECK_ID, "LearnWord")
    media = []
    for card in cards:
        fields = []
        for key in NOTE_FIELDS:
            if key.startswith("Audio_"):
                media.append(card[key])
                fields.append(f"[sound:{Path(card[key]).name}]")
            else:
                fields.append(html.escape(card[key]).replace("\n", "<br>"))
        deck.add_note(genanki.Note(model=model, fields=fields,
                                  guid=genanki.guid_for("LearnWord-v1", card["Word"])))
    package = genanki.Package(deck)
    package.media_files = media
    package.write_to_file(str(path))
