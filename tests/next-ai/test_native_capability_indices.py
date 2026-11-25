from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify_native_capability_indices.py"
SPEC = importlib.util.spec_from_file_location("verify_native_capability_indices", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class RustCommandRegistryParserTests(unittest.TestCase):
    def test_extracts_all_registration_constructor_kinds(self):
        source = r"""
            pub static ALL: &[Command] = &[
                edit("wall", "Wall", &[], "{points: [[x,y], [x,y]]}", make_wall),
                other("inspect", "Inspect", "{ }", inspect),
                other_files("save", "Save", "{path}", save, Files::Write),
                edit_files("import", "Import", &[], "{path}", import, Files::Read),
            ];
        """
        found = module.extract_command_registrations(source)
        self.assertEqual(found, [
            {"id": "wall", "registration_kind": "edit"},
            {"id": "inspect", "registration_kind": "other"},
            {"id": "save", "registration_kind": "other_files"},
            {"id": "import", "registration_kind": "edit_files"},
        ])

    def test_ignores_constructor_text_inside_comments_and_strings(self):
        source = r"""
            pub static ALL: &[Command] = &[
                edit("box", "Box", &[], "The text other(\"fake\") is not a registration", box),
                // edit("commented", "No", &[], "x", no)
                other("read", "Read", "A string says edit(\"not-real\")", read),
            ];
        """
        found = module.extract_command_registrations(source)
        self.assertEqual([row["id"] for row in found], ["box", "read"])

    def test_duplicate_command_ids_fail(self):
        source = r"""
            pub static ALL: &[Command] = &[
                edit("wall", "Wall", &[], "params", wall),
                other("wall", "Wall again", "params", wall),
            ];
        """
        with self.assertRaisesRegex(module.VerificationError, "Duplicate native command IDs"):
            module.extract_command_registrations(source)


if __name__ == "__main__":
    unittest.main()
