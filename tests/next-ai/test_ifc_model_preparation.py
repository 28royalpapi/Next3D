import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_ifc_models.py"
spec = importlib.util.spec_from_file_location("prepare_ifc_models", SCRIPT)
ifc_prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ifc_prep)


class IfcModelPreparationTests(unittest.TestCase):
    def test_only_safe_enum_and_numeric_properties_are_preserved(self):
        self.assertEqual(ifc_prep._safe_scalar("LoadBearing", True), True)
        self.assertEqual(ifc_prep._safe_scalar("FireRating", "REI60"), "REI60")
        self.assertEqual(ifc_prep._safe_scalar("NominalValue", 42.75), 42.75)
        self.assertIsNone(ifc_prep._safe_scalar("OwnerEmail", "architect@example.com"))
        self.assertIsNone(ifc_prep._safe_scalar("Address", "123 Private Road"))
        self.assertIsNone(ifc_prep._safe_scalar("UnrestrictedText", "Alice Student"))

    def test_paired_architecture_and_structure_files_share_one_split_group(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            architecture = root / "IFC-models" / "2026_BIMprojects" / "team-7" / "architecture.ifc"
            structure = root / "IFC-models" / "2026_BIMprojects" / "team-7" / "structure.ifc"
            architecture.parent.mkdir(parents=True)
            architecture.write_text("IFC", encoding="utf-8")
            structure.write_text("IFC", encoding="utf-8")
            group_a = ifc_prep.split_group_for_file(architecture, root)
            group_b = ifc_prep.split_group_for_file(structure, root)
            self.assertEqual(group_a, group_b)
            self.assertEqual(ifc_prep.split_group(group_a), ifc_prep.split_group(group_b))

    def test_separate_2025_student_models_get_independent_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "IFC-models" / "2025_BIMfundamentals"
            folder.mkdir(parents=True)
            first = folder / "model-001.ifc"
            second = folder / "model-002.ifc"
            first.write_text("IFC", encoding="utf-8")
            second.write_text("IFC", encoding="utf-8")
            self.assertNotEqual(
                ifc_prep.split_group_for_file(first, root),
                ifc_prep.split_group_for_file(second, root),
            )


if __name__ == "__main__":
    unittest.main()
