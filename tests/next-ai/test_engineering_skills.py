from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters/nextcad-ai/NextAI"
sys.path.insert(0, str(ADAPTER))

from next_ai import engineering_skills, freecad_tools, knowledge, tool_registry


SKILL_ROOT = ADAPTER / "knowledge_packs" / "skills"


class EngineeringSkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = engineering_skills.EngineeringSkillRegistry(SKILL_ROOT)

    def test_shipped_skill_catalog_covers_several_engineering_disciplines(self):
        names = {item["name"] for item in self.registry.catalog()}
        self.assertTrue({
            "engineering-operator-method",
            "residential-floor-plan",
            "water-storage-tower",
            "mechanical-gear",
            "vehicle-package-design",
            "electrical-control-panel",
            "civil-road-drainage",
        }.issubset(names))

    def test_progressive_retrieval_selects_relevant_skill_for_residential_request(self):
        result = self.registry.retrieve(
            "Create a three bedroom bungalow with master bedrooms, shared toilet and sitting room."
        )
        selected = [item["name"] for item in result["selected"]]
        self.assertTrue(selected)
        self.assertEqual(selected[0], "residential-floor-plan")
        self.assertIn("engineering-operator-method", selected)
        self.assertLessEqual(result["selected_count"], engineering_skills.MAX_SELECTED_SKILLS)
        self.assertGreater(result["available_count"], result["selected_count"])
        self.assertIn("master bedrooms", result["selected"][0]["instructions"])

    def test_wash_tower_synonym_routes_to_water_storage_skill(self):
        result = self.registry.retrieve("Design a wash tower with elevated tank and steel supports.")
        self.assertEqual(result["selected"][0]["name"], "water-storage-tower")
        self.assertIn("storage capacity", result["selected"][0]["instructions"])

    def test_mechanical_gear_request_routes_to_gear_skill(self):
        result = self.registry.retrieve("Design an involute spur gear with module and number of teeth.")
        self.assertEqual(result["selected"][0]["name"], "mechanical-gear")
        self.assertIn("pressure angle", result["selected"][0]["instructions"])

    def test_catalogue_contains_metadata_without_injecting_every_skill_body(self):
        result = self.registry.retrieve("water tank", max_skills=1)
        self.assertGreater(result["available_count"], 1)
        self.assertEqual(result["selected_count"], 1)
        self.assertTrue(all("instructions" not in item for item in result["catalog"]))
        self.assertIn("instructions", result["selected"][0])

    def test_skill_scripts_are_not_loaded_or_executed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill_dir = root / "safe-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: safe-skill\ndescription: Safe test skill\ntags: [safe, test]\n---\n"
                "# Instructions\nDo not execute files.\n",
                encoding="utf-8",
            )
            marker = root / "executed.txt"
            (skill_dir / "handler.py").write_text(
                "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('bad')\n",
                encoding="utf-8",
            )
            registry = engineering_skills.EngineeringSkillRegistry(root)
            result = registry.retrieve("safe test")
            self.assertEqual(result["selected"][0]["name"], "safe-skill")
            self.assertFalse(marker.exists())

    def test_only_explicit_markdown_references_can_be_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill_dir = root / "skill-one"
            refs = skill_dir / "references"
            refs.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: skill-one\ndescription: Reference test\ntags: [reference]\n---\n"
                "Reference instructions.\n",
                encoding="utf-8",
            )
            (refs / "dimensions.md").write_text("Dimensions are in millimetres.\n", encoding="utf-8")
            (skill_dir / "secret.txt").write_text("not allowed", encoding="utf-8")
            registry = engineering_skills.EngineeringSkillRegistry(root)
            self.assertEqual(
                registry.read_reference("skill-one", "references/dimensions.md")["output"],
                "Dimensions are in millimetres.\n",
            )
            self.assertIn("not in the skill's Markdown allow-list", registry.read_reference(
                "skill-one", "../secret.txt"
            )["error"])

    def test_selected_skill_body_is_added_to_native_context_without_changing_authority(self):
        with (
            patch.object(freecad_tools, "discover_capabilities", return_value={"workbenches": ["Part"]}),
            patch.object(freecad_tools, "inspect_document", return_value={"open": False}),
            patch.object(knowledge, "search", return_value=[]),
        ):
            context = tool_registry.read_context("three bedroom house floor plan")
        self.assertEqual(context["engineering_skills"]["selected"][0]["name"], "residential-floor-plan")
        self.assertIn("WHAT", context["context_contract"]["engineering_skills"])
        self.assertIn("HOW", context["context_contract"]["native_capabilities"])
        self.assertEqual(context["available_tools"], tool_registry.TOOLS)
        self.assertTrue(context["ranked_tools"])

    def test_ranked_tools_are_existing_reviewed_tools_only(self):
        ranked = tool_registry.rank_tools("create wall using path height and thickness")
        names = [item["name"] for item in ranked]
        self.assertIn("create_arch_wall", names[:5])
        allowed = {item["name"] for item in tool_registry.TOOLS}
        self.assertTrue(set(names).issubset(allowed))
        self.assertLessEqual(len(names), 12)


if __name__ == "__main__":
    unittest.main()
