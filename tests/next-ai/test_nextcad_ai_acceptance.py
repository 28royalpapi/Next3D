from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MACRO = ROOT / "training/nextai/verify_nextcad_ai_native.FCMacro"
RUNNER = ROOT / "scripts/run_nextcad_ai_acceptance.py"
INSTALLER = ROOT / "scripts/install-nextcad-ai.py"


class NextCADNativeAcceptanceContractTests(unittest.TestCase):
    def test_native_acceptance_macro_exercises_all_added_operator_actions(self):
        source = MACRO.read_text(encoding="utf-8")
        for tool in (
            "create_part_box",
            "boolean_operation",
            "transform_object",
            "duplicate_object",
            "fillet_edges",
            "chamfer_edges",
            "create_partdesign_body",
            "create_partdesign_sketch",
            "add_sketch_polygon",
            "create_partdesign_pad",
            "linear_pattern",
            "polar_pattern",
            "create_model_schedule",
        ):
            with self.subTest(tool=tool):
                self.assertIn('"tool": "' + tool + '"', source)
        self.assertIn("doc.saveAs", source)
        self.assertIn("App.closeDocument", source)
        self.assertIn("App.openDocument", source)
        self.assertIn("AcceptanceModelSchedule", source)
        self.assertIn("partdesign_polar_pattern_with_hub", source)
        self.assertIn("stage_project", source)
        self.assertIn("nextcad-ai-native-acceptance-trace.jsonl", source)
        self.assertIn("tool_schema_version", source)
        self.assertIn('report["status"] = "PASS"', source)
        self.assertIn('report["status"] = "FAIL"', source)

    def test_native_acceptance_report_retains_every_step_result(self):
        source = MACRO.read_text(encoding="utf-8")
        self.assertIn("results = []", source)
        self.assertIn("results.append(step_result)", source)
        self.assertNotIn("results.setdefault", source)

    def test_native_acceptance_runner_has_real_gui_modes_and_saved_project_gate(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('mode.add_argument("--executable"', source)
        self.assertIn('mode.add_argument("--command-prefix"', source)
        self.assertIn('result.get("status") != "PASS"', source)
        self.assertIn("NEXT3D_NEXTCAD_AI_ACCEPTANCE_PROJECT", source)
        self.assertIn("project.is_file()", source)
        self.assertIn("stage_project.is_file()", source)
        self.assertIn("len(trace_rows) != 2", source)

    def test_installer_places_first_party_adapter_where_native_runner_expects_it(self):
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn(' / "src/Mod/NextAI"', source)
        self.assertIn('source / "next_ai/engineering_skills.py"', source)


if __name__ == "__main__":
    unittest.main()
