from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "training" / "nextai" / "learning_studio" / "index.html"


class StructureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.script_count = 0
        self.title_seen = False

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        if "id" in attrs_map:
            self.ids.append(attrs_map["id"])
        if tag == "script":
            self.script_count += 1

    def handle_data(self, data):
        if "NextAI Learning Studio" in data:
            self.title_seen = True


class LearningStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = APP.read_text(encoding="utf-8")
        cls.parser = StructureParser()
        cls.parser.feed(cls.html)

    def test_entry_file_and_title_exist(self):
        self.assertTrue(APP.is_file())
        self.assertIn("<title>NextAI Learning Studio</title>", self.html)
        self.assertTrue(self.parser.title_seen)

    def test_document_ids_are_unique(self):
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))

    def test_has_single_application_script(self):
        self.assertEqual(self.parser.script_count, 1)
        self.assertIn('renderApp();', self.html)

    def test_all_six_curriculum_layers_are_present(self):
        for text in (
            "Native capability census",
            "Atomic skills",
            "Compound workflows",
            "Complete project scenarios",
            "Human-style design intake",
            "Revision and recovery",
        ):
            self.assertIn(text, self.html)

    def test_evidence_ladder_is_complete(self):
        for level in ("L0", "L1", "L2", "L3", "L4", "L5"):
            self.assertIn('["' + level + '"', self.html)

    def test_each_learning_path_has_lessons(self):
        for track in ("operator", "nextcad", "bim", "architecture", "civil", "systems"):
            self.assertRegex(self.html, r'id:"' + re.escape(track) + r'"')

    def test_progress_is_explicitly_browser_local(self):
        self.assertIn("localStorage", self.html)
        self.assertIn("learner progress", self.html.lower())
        self.assertIn("does not change model weights", self.html)


if __name__ == "__main__":
    unittest.main()
