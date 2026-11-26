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

    def test_native_tool_schemas_are_forwarded_to_chat_template(self):
        tool_schema = [{
            "type": "function",
            "function": {
                "name": "create_part_box",
                "description": "Create a native box.",
                "parameters": {"type": "object", "properties": {"length": {"type": "number"}}},
            },
        }]
        kwargs = evaluator.chat_template_kwargs_for({"tools": tool_schema})
        self.assertEqual(kwargs["tools"], tool_schema)

    def test_chat_template_options_are_preserved_with_tool_schemas(self):
        row = {
            "tools": [{"type": "function", "function": {"name": "inspect_model", "parameters": {"type": "object"}}}],
            "chat_template_kwargs": {"enable_thinking": False},
        }
        kwargs = evaluator.chat_template_kwargs_for(row)
        self.assertEqual(kwargs["enable_thinking"], False)
        self.assertEqual(kwargs["tools"], row["tools"])

    def test_invalid_or_conflicting_tool_schemas_fail_closed(self):
        with self.assertRaises(ValueError):
            evaluator.chat_template_kwargs_for({"tools": []})
        with self.assertRaises(ValueError):
            evaluator.chat_template_kwargs_for({
                "tools": [{"type": "function", "function": {"name": "a"}}],
                "chat_template_kwargs": {"tools": [{"type": "function", "function": {"name": "b"}}]},
            })


if __name__ == "__main__":
    unittest.main()
