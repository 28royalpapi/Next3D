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
        self.assertIsNone(ifc_prep._safe_scalar("StudentNumber", 20241234))
        self.assertIsNone(ifc_prep._safe_scalar("OwnerPhone", 2348012345678))
        self.assertIsNone(ifc_prep._safe_scalar("GlobalId", "2O2f$k9v5E7u"))

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

    def test_relationships_preserve_non_element_type_material_pset_and_spatial_endpoints(self):
        import sys
        import types
        from unittest.mock import patch

        class Entity:
            def __init__(self, step_id, ifc_class, **attributes):
                self._step_id = step_id
                self._ifc_class = ifc_class
                for key, value in attributes.items():
                    setattr(self, key, value)

            def id(self):
                return self._step_id

            def is_a(self):
                return self._ifc_class

        wall = Entity(1, "IfcWall", PredefinedType="STANDARD")
        door = Entity(2, "IfcDoor", PredefinedType="DOOR")
        wall_type = Entity(20, "IfcWallType")
        material = Entity(30, "IfcMaterial")
        pset = Entity(40, "IfcPropertySet")
        storey = Entity(50, "IfcBuildingStorey")
        opening = Entity(60, "IfcOpeningElement")

        class FakeModel:
            schema = "IFC4"

            def by_type(self, name):
                if name == "IfcElement":
                    return [wall, door]
                if name == "IfcRelDefinesByType":
                    return [Entity(101, name, RelatingType=wall_type, RelatedObjects=[wall])]
                if name == "IfcRelAssociatesMaterial":
                    return [Entity(102, name, RelatingMaterial=material, RelatedObjects=[wall])]
                if name == "IfcRelDefinesByProperties":
                    return [Entity(103, name, RelatingPropertyDefinition=pset, RelatedObjects=[door])]
                if name == "IfcRelContainedInSpatialStructure":
                    return [Entity(104, name, RelatingStructure=storey, RelatedElements=[wall, door])]
                if name == "IfcRelVoidsElement":
                    return [Entity(105, name, RelatingBuildingElement=wall, RelatedOpeningElement=opening)]
                if name == "IfcRelFillsElement":
                    return [Entity(106, name, RelatingOpeningElement=opening, RelatedBuildingElement=door)]
                if name in {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"}:
                    return []
                return []

        package = types.ModuleType("ifcopenshell")
        util = types.ModuleType("ifcopenshell.util")
        element = types.ModuleType("ifcopenshell.util.element")
        element.get_psets = lambda *args, **kwargs: {}
        element.get_container = lambda *args, **kwargs: None
        element.get_type = lambda *args, **kwargs: None
        element.get_materials = lambda *args, **kwargs: []
        package.util = util
        util.element = element
        with patch.dict(sys.modules, {
            "ifcopenshell": package,
            "ifcopenshell.util": util,
            "ifcopenshell.util.element": element,
        }):
            summary, chunks = ifc_prep.extract_model(FakeModel(), element_chunk_size=1)

        self.assertEqual(summary["relationship_edges_extracted"], 6)
        wall_chunk = next(chunk for chunk in chunks if chunk["elements"][0]["ifc_class"] == "IfcWall")
        door_chunk = next(chunk for chunk in chunks if chunk["elements"][0]["ifc_class"] == "IfcDoor")
        wall_edges = wall_chunk["relationships_touching_chunk"]
        door_edges = door_chunk["relationships_touching_chunk"]
        self.assertTrue(any(edge["source_class"] == "IfcWallType" and edge["target_class"] == "IfcWall" for edge in wall_edges))
        self.assertTrue(any(edge["source_class"] == "IfcMaterial" and edge["target_class"] == "IfcWall" for edge in wall_edges))
        self.assertTrue(any(edge["source_class"] == "IfcPropertySet" and edge["target_class"] == "IfcDoor" for edge in door_edges))
        self.assertTrue(any(edge["source_class"] == "IfcBuildingStorey" for edge in wall_edges))
        self.assertTrue(any(edge["target_class"] == "IfcOpeningElement" for edge in wall_edges))
        self.assertTrue(any(edge["source_class"] == "IfcOpeningElement" and edge["target_class"] == "IfcDoor" for edge in door_edges))
        for edge in wall_edges + door_edges:
            self.assertTrue(edge["source"].startswith(("e", "x")))
            self.assertTrue(edge["target"].startswith(("e", "x")))
            self.assertNotIn("GlobalId", json.dumps(edge))

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
