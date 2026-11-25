from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "training/nextai/capability_census.py"
SPEC = importlib.util.spec_from_file_location("nextai_capability_census", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)

BIM = ROOT / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json"
CAD = ROOT / "docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json"
CAD_COMMIT = "00cb280454069966a2fb0a8e7dc184c46e7b38b3"
BIM_COMMIT = "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"


class CapabilityCensusTests(unittest.TestCase):
    def test_all_214_bim_commands_receive_ten_learning_obligations(self):
        census, obligations = module.build_census(
            BIM, CAD, expected_cad_commit=CAD_COMMIT, expected_bim_commit=BIM_COMMIT
        )
        self.assertEqual(census["counts"]["nextbim_registered_commands"], 214)
        commands = [x for x in census["capabilities"] if x["capability_type"] == "native_command"]
        self.assertEqual(len(commands), 214)
        self.assertEqual(len([x for x in obligations if x["application"] == "nextbim"]), 2140)
        self.assertEqual({x["native_id"] for x in commands},
                         {x["native_id"] for x in obligations if x["application"] == "nextbim"})

    def test_nextcad_source_modules_are_not_misreported_as_runtime_commands(self):
        census, _ = module.build_census(BIM, CAD, expected_cad_commit=CAD_COMMIT)
        self.assertEqual(census["counts"]["nextcad_source_modules"], 30)
        self.assertEqual(census["counts"]["nextcad_runtime_commands"], 0)
        self.assertFalse(census["counts"]["nextcad_runtime_census_complete"])

    def test_runtime_snapshot_adds_live_command_records(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.json"
            index = module.read_json(CAD)
            wb = index["modules"][0]["module"]
            path.write_text(json.dumps({
                "schema_version": "1.0.0", "application": "nextcad",
                "application_version": "1.1.0", "upstream_commit": CAD_COMMIT,
                "runtime_inventory": {
                    "global_command_registry_enumerated": True,
                    "workbenches": [{"id": wb, "toolbar_command_ids": ["Part_Box"], "menu_command_mapping": "not_exposed_by_pinned_python_workbench_wrapper"}],
                    "python_api_enumeration_scope": "Public names of Python modules loaded after workbench activation.",
                    "commands": [{"id": "Part_Box", "menu_text": "Create box",
                                  "toolbar_workbenches": [wb], "ui_contexts": ["toolbar:Primitives"]}],
                    "python_api_modules": [{"name": "Part", "public_members": [
                        {"name": "makeBox", "kind": "callable", "documentation": "Create a box."},
                        {"name": "Shape", "kind": "class", "documentation": "Shape base."}
                    ]}]
                }
            }), encoding="utf-8")
            census, obligations = module.build_census(BIM, CAD, path, CAD_COMMIT, BIM_COMMIT)
            found = next(x for x in census["capabilities"] if x["capability_type"] == "native_gui_command")
            self.assertEqual(found["native_id"], "Part_Box")
            self.assertEqual(found["toolbar_workbenches"], [wb])
            self.assertEqual(census["counts"]["nextcad_runtime_api_members"], 2)
            self.assertIn("Public names of Python modules loaded", census["sources"]["nextcad"]["python_api_enumeration_scope"])
            part_box_obligations = [x for x in obligations
                                    if x["application"] == "nextcad" and x["native_id"] == "Part_Box"]
            self.assertTrue(all(x["native_metadata"]["menu_text"] is None or
                                isinstance(x["native_metadata"]["menu_text"], str)
                                for x in part_box_obligations))
            self.assertEqual(len([x for x in obligations if x["application"] == "nextcad"]), 30)
            self.assertEqual(
                {x["native_id"] for x in census["capabilities"] if x["capability_type"] == "native_api_member"},
                {"Part.makeBox", "Part.Shape"}
            )

    def test_runtime_report_with_wrong_source_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.json"
            path.write_text(json.dumps({
                "schema_version": "1.0.0", "application": "nextcad",
                "upstream_commit": "wrong",
                "runtime_inventory": {"global_command_registry_enumerated": True,
                                      "workbenches": [], "commands": []}
            }), encoding="utf-8")
            with self.assertRaisesRegex(module.CensusError, "pinned source commit"):
                module.build_census(BIM, CAD, path)

    def test_wrong_catalog_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.json"
            value = module.read_json(BIM)
            value["command_count"] = 215
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(module.CensusError, "command_count"):
                module.load_bim_catalog(path)

    def test_duplicate_runtime_command_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.json"
            path.write_text(json.dumps({
                "schema_version": "1.0.0", "application": "nextcad",
                "upstream_commit": CAD_COMMIT,
                "runtime_inventory": {"global_command_registry_enumerated": True,
                    "workbenches": [], "commands": [{"id": "X"}, {"id": "X"}]}
            }), encoding="utf-8")
            with self.assertRaisesRegex(module.CensusError, "Duplicate id"):
                module.build_census(BIM, CAD, path)

    def test_obligations_are_not_training_examples_or_mastery(self):
        census, obligations = module.build_census(BIM, CAD)
        self.assertFalse(census["evidence_rules"]["skill_obligations_are_sft_examples"])
        self.assertTrue(census["evidence_rules"]["mastery_requires_native_execution_and_validation"])
        self.assertTrue(all(x["record_type"] == "skill_obligation_not_training_example" for x in obligations))
        self.assertTrue(all(x["mastery_status"] == "not_assessed" for x in obligations))

    def test_bim_assistant_policy_distinguishes_render_file_and_normal_commands(self):
        census, obligations = module.build_census(BIM, CAD)
        commands = {x["native_id"]: x for x in census["capabilities"]
                    if x["application"] == "nextbim"}
        self.assertEqual(commands["render"]["assistant_execution_status"], "blocked_no_image_output")
        self.assertEqual(commands["save"]["assistant_execution_status"], "user_operated_file_command")
        self.assertEqual(commands["wall"]["assistant_execution_status"],
                         "native_execution_candidate_subject_to_bridge_policy")
        render_obligations = [x for x in obligations
                              if x["application"] == "nextbim" and x["native_id"] == "render"]
        self.assertTrue(all("image-blind" in x.get("special_rule", "") for x in render_obligations))
        self.assertEqual(commands["wall"]["parameter_contract_kind"],
                         "human_readable_registration_description_not_json_schema")
        wall_obligations = [x for x in obligations
                            if x["application"] == "nextbim" and x["native_id"] == "wall"]
        self.assertTrue(all(x["native_metadata"].get("parameter_contract") for x in wall_obligations))
        self.assertTrue(all(x["native_metadata"].get("assistant_execution_status") ==
                            "native_execution_candidate_subject_to_bridge_policy"
                            for x in wall_obligations))

    def test_file_effect_commands_have_a_policy_boundary(self):
        census, obligations = module.build_census(BIM, CAD)
        file_ids = {x["native_id"] for x in census["capabilities"]
                    if x["application"] == "nextbim" and x["file_effect"] != "none"}
        guarded = {x["native_id"] for x in obligations
                   if x["application"] == "nextbim" and x.get("special_rule")}
        self.assertTrue(file_ids)
        self.assertTrue(file_ids.issubset(guarded))


class RuntimeMacroSafetyTests(unittest.TestCase):
    def test_runtime_macro_uses_native_discovery_and_never_runs_commands(self):
        source = (ROOT / "training/nextai/discover_nextcad_runtime.FCMacro").read_text(encoding="utf-8")
        self.assertIn("Gui.listCommands()", source)
        self.assertIn("Gui.Command.get(command_id)", source)
        self.assertIn("Gui.listWorkbenches()", source)
        self.assertIn("getToolbarItems()", source)
        self.assertIn("python_api_modules", source)
        self.assertIn("sys.modules", source)
        self.assertIn('read_member(active_workbench, "name")', source)
        self.assertIn("toolbar_workbenches", source)
        self.assertIn("menu_command_mapping", source)
        self.assertNotIn("Gui.runCommand(", source)
        self.assertNotIn("App.newDocument(", source)
        self.assertNotIn("doc.save(", source)


if __name__ == "__main__":
    unittest.main()
