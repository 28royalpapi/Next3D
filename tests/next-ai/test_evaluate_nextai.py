from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "training" / "nextai" / "evaluate_nextai.py"
SPEC = importlib.util.spec_from_file_location("nextai_evaluator", MODULE_PATH)
evaluator = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(evaluator)


class PromptExtractionTests(unittest.TestCase):
    def test_messages_only_native_record_keeps_assistant_reference(self):
        expected = json.dumps({
            "application": "nextcad",
            "steps": [{"tool": "create_part_box", "arguments": {"length": 100}}],
        })
        row = {
            "record_id": "native-cad-001",
            "messages": [
                {"role": "system", "content": "You are NextAI."},
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": "Create a 100 mm box."},
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": expected}]},
            ],
            "images": ["reference.png"],
        }

        system, prompt, images, actual_expected = evaluator.prompt_for(row)

        self.assertEqual(system, "You are NextAI.")
        self.assertEqual(prompt, "Create a 100 mm box.")
        self.assertEqual(images, ["reference.png"])
        self.assertEqual(actual_expected, expected)

    def test_legacy_prompt_completion_record_still_works(self):
        row = {
            "system": "System instructions",
            "prompt": "Make a beam.",
            "completion": '{"plan": []}',
            "images": [],
        }

        system, prompt, images, expected = evaluator.prompt_for(row)

        self.assertEqual(system, "System instructions")
        self.assertEqual(prompt, "Make a beam.")
        self.assertEqual(images, [])
        self.assertEqual(expected, '{"plan": []}')

    def test_assistant_reference_can_be_plain_text(self):
        row = {
            "messages": [
                {"role": "user", "content": "Explain a sketch constraint."},
                {"role": "assistant", "content": "A constraint defines geometry."},
            ]
        }

        _, prompt, _, expected = evaluator.prompt_for(row)

        self.assertEqual(prompt, "Explain a sketch constraint.")
        self.assertEqual(expected, "A constraint defines geometry.")


if __name__ == "__main__":
    unittest.main()
