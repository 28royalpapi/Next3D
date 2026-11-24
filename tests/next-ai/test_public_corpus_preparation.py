import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_public_corpora.py"
spec = importlib.util.spec_from_file_location("prepare_public_corpora", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicCorpusPreparationTests(unittest.TestCase):
    def test_cad_operations_keep_feature_order_and_parameters(self):
        rows = [
            {"op_name": "box", "args": ["width", "depth", "height"], "keywords": [], "lineno": 2},
            {"op_name": "hole", "args": ["diameter"], "keywords": [{"arg": "diameter", "value": "4.0"}], "lineno": 5},
            {"op_name": "fillet", "args": ["radius"], "keywords": [], "lineno": 8},
        ]
        plan = module.cad_plan(rows, 72)
        self.assertEqual([x["feature"] for x in plan["ordered_features"]],
                         ["primitive_box", "hole", "fillet"])
        self.assertEqual(plan["ordered_features"][1]["parameters"]["diameter"], "4.0")
        self.assertEqual(plan["geometry_metadata"]["reference_face_count"], 72)

    def test_bim_admission_filters_unvalidated_and_low_score_rows(self):
        row = {
            "instruction": "Explain IFC material layers.",
            "input": "Create a three-layer wall.",
            "output": "Layer order and thicknesses.",
            "score": 4.8,
            "metadata": '{"validated": true, "category": "Materials"}',
        }
        self.assertIsNotNone(module.make_bim_record(row, "bim-1"))
        row["metadata"] = '{"validated": false}'
        self.assertIsNone(module.make_bim_record(row, "bim-2"))
        row["metadata"] = '{"validated": true}'
        row["score"] = 3.0
        self.assertIsNone(module.make_bim_record(row, "bim-3"))

    def test_bim_qa_has_attribution(self):
        row = {"question": "What is IfcRelVoidsElement?", "answer": "It relates an opening to an element."}
        result = module.make_bim_qa_record(row, "qa-1", "train")
        self.assertEqual(result["license"], "CC-BY-4.0")
        self.assertTrue(result["attribution"])

    def test_synthetic_curriculum_covers_2d_parametric_bim_and_documentation(self):
        lessons = module.make_synthetic_curriculum()
        domains = {row["domain"] for row in lessons}
        self.assertIn("cad_2d_drafting", domains)
        self.assertIn("cad_parametric_sketch", domains)
        self.assertIn("cad_3d_modelling", domains)
        self.assertIn("cad_documentation", domains)
        self.assertIn("bim_concepts", domains)
        self.assertIn("bim_ifc_relationships", domains)
        self.assertIn("bim_documentation", domains)
        self.assertIn("construction_workflows", domains)
        dimension_lesson = next(row for row in lessons if row["domain"] == "cad_2d_drafting")
        self.assertIn("6000", dimension_lesson["completion"])
        self.assertIn("mm", dimension_lesson["completion"])

    def test_training_script_compiles_and_keeps_full_precision_lora(self):
        trainer_path = SCRIPT.parents[0] / "train_nextai.py"
        source = trainer_path.read_text(encoding="utf-8")
        compile(source, str(trainer_path), "exec")
        self.assertIn("load_in_4bit=False", source)
        self.assertIn("finetune_vision_layers=False", source)
        self.assertIn("held_out_test_metrics_by_domain", source)
        self.assertIn("test_set_used_for_training", source)

    def test_sampler_uses_available_domains_and_respects_limit(self):
        groups = {
            "cad_visual": [{"domain": "cad_visual", "id": i} for i in range(30)],
            "bim_ifc_knowledge": [{"domain": "bim_ifc_knowledge", "id": i} for i in range(30)],
            "nextcad_native": [],
        }
        chosen = module.sample_balanced(groups, 20, 3407)
        self.assertEqual(len(chosen), 20)
        domains = {x["domain"] for x in chosen}
        self.assertEqual(domains, {"cad_visual", "bim_ifc_knowledge"})


if __name__ == "__main__":
    unittest.main()
