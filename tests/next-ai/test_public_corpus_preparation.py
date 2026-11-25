import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_public_corpora.py"
spec = importlib.util.spec_from_file_location("prepare_public_corpora", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

EVAL_SCRIPT = SCRIPT.parent / "evaluate_nextai.py"
eval_spec = importlib.util.spec_from_file_location("evaluate_nextai", EVAL_SCRIPT)
evaluator = importlib.util.module_from_spec(eval_spec)
eval_spec.loader.exec_module(evaluator)


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

    @unittest.skipUnless(__import__("importlib").util.find_spec("PIL") is not None,
                         "Pillow is installed by the dedicated NextAI pipeline CI step")
    def test_hugging_face_decoded_pil_images_are_saved(self):
        from PIL import Image
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = Image.new("RGB", (12, 9), (120, 40, 20))
            pil_path = root / "pil.jpg"
            module._save_image(image, pil_path)
            self.assertTrue(pil_path.is_file())
            with Image.open(pil_path) as saved:
                self.assertEqual(saved.size, (12, 9))

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            payload = buffer.getvalue()
            bytes_path = root / "bytes.jpg"
            module._save_image(payload, bytes_path)
            self.assertTrue(bytes_path.is_file())

            mapping_path = root / "mapping.jpg"
            module._save_image({"bytes": payload, "path": None}, mapping_path)
            self.assertTrue(mapping_path.is_file())

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

    def test_bim_admission_accepts_published_validated_source_label(self):
        row = {
            "instruction": "Explain IFC material layers.",
            "input": "What is a material layer set?",
            "output": "An IfcMaterialLayerSet describes ordered material layers.",
            "source": "validated-synthetic",
            "score": 4.8,
            "metadata": None,
        }
        accepted = module.make_bim_record(row, "bim-published-example")
        self.assertIsNotNone(accepted)
        self.assertEqual(accepted["source_record_label"], "validated-synthetic")
        row["source"] = "unreviewed"
        self.assertIsNone(module.make_bim_record(row, "bim-unreviewed"))

    def test_cad_validation_split_uses_published_split_name(self):
        import inspect
        source = inspect.getsource(module.prepare)
        self.assertIn('("validation", args.max_cad_validation, "validation")', source)
        self.assertNotIn('("val", args.max_cad_validation, "validation")', source)

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
        self.assertIn("bim_architectural_floorplan", domains)
        self.assertIn("cad_2d_entity_semantics", domains)
        self.assertIn("cad_coordinate_transforms", domains)
        self.assertIn("cad_parametric_features", domains)
        self.assertIn("cad_assembly_design", domains)
        self.assertIn("cad_technical_documentation", domains)
        self.assertIn("cad_interoperability", domains)
        self.assertIn("bim_spatial_hierarchy", domains)
        self.assertIn("bim_type_instance_data", domains)
        self.assertIn("bim_material_properties", domains)
        self.assertIn("bim_ifc_exchange_requirements", domains)
        self.assertIn("bim_georeferencing", domains)
        self.assertIn("bim_phasing_revisions", domains)
        self.assertIn("engineering_structural_workflow", domains)
        self.assertIn("engineering_reinforced_concrete_workflow", domains)
        self.assertIn("engineering_geotechnical_workflow", domains)
        self.assertIn("engineering_water_and_drainage", domains)
        self.assertIn("engineering_survey_and_setting_out", domains)
        self.assertIn("engineering_standards_and_regulations", domains)
        self.assertIn("construction_project_controls", domains)
        self.assertIn("construction_cost_and_quantities", domains)
        self.assertIn("construction_quality_and_safety", domains)
        self.assertIn("bim_structural_model", domains)
        self.assertIn("bim_mep_systems", domains)
        self.assertIn("bim_coordination", domains)
        self.assertIn("bim_quantities", domains)
        self.assertIn("construction_information", domains)
        floorplan = next(row for row in lessons if row["domain"] == "bim_architectural_floorplan")
        floorplan_data = json.loads(floorplan["completion"])
        shell = floorplan_data["shell"]
        room_area = sum(
            (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
            for room in floorplan_data["room_rectangles"]
            for bounds in [room["bounds"]]
        )
        self.assertEqual(room_area, shell["width"] * shell["depth"])
        self.assertEqual(len(floorplan_data["door_centres"]), 8)
        dimension_lesson = next(row for row in lessons if row["domain"] == "cad_2d_drafting")
        self.assertIn("6000", dimension_lesson["completion"])
        self.assertIn("mm", dimension_lesson["completion"])

    def test_advanced_curriculum_covers_cad_bim_and_engineering_disciplines(self):
        lessons = module.make_advanced_engineering_curriculum()
        domains = {lesson["domain"] for lesson in lessons}
        required = {
            "cad_2d_entity_semantics",
            "cad_coordinate_transforms",
            "cad_parametric_features",
            "cad_assembly_design",
            "cad_technical_documentation",
            "cad_interoperability",
            "bim_spatial_hierarchy",
            "bim_type_instance_data",
            "bim_material_properties",
            "bim_ifc_exchange_requirements",
            "bim_georeferencing",
            "bim_phasing_revisions",
            "engineering_structural_workflow",
            "engineering_reinforced_concrete_workflow",
            "engineering_geotechnical_workflow",
            "engineering_water_and_drainage",
            "engineering_survey_and_setting_out",
            "engineering_standards_and_regulations",
            "construction_project_controls",
            "construction_cost_and_quantities",
            "construction_quality_and_safety",
        }
        self.assertTrue(required.issubset(domains), sorted(required - domains))
        self.assertGreaterEqual(len(lessons), 200)
        for lesson in lessons:
            self.assertTrue(lesson["prompt"].strip())
            self.assertIsInstance(lesson["completion"], dict)
            self.assertIn("schema", lesson["completion"])

    def test_advanced_cad_lesson_preserves_dimensions_and_feature_order(self):
        lessons = module.make_advanced_engineering_curriculum()
        plate = next(row for row in lessons if row["domain"] == "cad_parametric_features")
        plan = plate["completion"]
        features = plan["features"]
        self.assertEqual([item["order"] for item in features], [1, 2, 3, 4])
        self.assertEqual(features[0]["width"], 100)
        self.assertEqual(features[1]["length"], 8)
        self.assertEqual(features[2]["termination"], "through_all")

    def test_standards_lesson_requires_jurisdiction_and_edition(self):
        lessons = module.make_advanced_engineering_curriculum()
        lesson = next(row for row in lessons if row["domain"] == "engineering_standards_and_regulations")
        required = lesson["completion"]["required_context"]
        self.assertIn("jurisdiction", required)
        self.assertIn("edition and amendments", required)
        rules = " ".join(lesson["completion"]["rules"]).lower()
        self.assertIn("never assume", rules)
        self.assertIn("copyrighted", rules)

    def test_training_script_compiles_and_keeps_full_precision_lora(self):
        trainer_path = SCRIPT.parents[0] / "train_nextai.py"
        source = trainer_path.read_text(encoding="utf-8")
        compile(source, str(trainer_path), "exec")
        self.assertIn("load_in_4bit=False", source)
        self.assertIn("finetune_vision_layers=True", source)
        self.assertIn("num_train_epochs=args.num_train_epochs", source)
        self.assertIn("max_steps=args.max_steps", source)
        self.assertIn("bf16=use_bf16", source)
        self.assertIn("fp16=not use_bf16", source)
        self.assertIn("held_out_test_metrics_by_domain", source)
        self.assertIn("test_set_used_for_training", source)

    def test_evaluator_json_and_text_metrics(self):
        expected = '{"features": [{"type": "pad", "length": 10}], "units": "mm"}'
        predicted = '{"features": [{"type": "pad", "length": 10}], "units": "mm"}'
        score = evaluator.score_record(expected, predicted)
        self.assertEqual(score["json_parse"], 1.0)
        self.assertEqual(score["key_recall"], 1.0)
        self.assertEqual(score["scalar_match"], 1.0)
        text_score = evaluator.token_f1("IFC wall opening window", "IFC wall opening")
        self.assertGreater(text_score, 0.7)

    def test_evaluator_script_compiles(self):
        source = EVAL_SCRIPT.read_text(encoding="utf-8")
        compile(source, str(EVAL_SCRIPT), "exec")

    def test_compact_projector_export_replaces_f16_only_after_q8_is_valid(self):
        import importlib.util
        import tempfile

        script = SCRIPT.parent / "compact_multimodal_export.py"
        export_spec = importlib.util.spec_from_file_location("compact_multimodal_export", script)
        exporter = importlib.util.module_from_spec(export_spec)
        export_spec.loader.exec_module(exporter)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gguf_dir = root / "gguf"
            gguf_dir.mkdir()
            main = gguf_dir / "nextai-Q4_K_M.gguf"
            main.write_bytes(b"GGUF" + b"main-model")
            old_projector = gguf_dir / "mmproj-F16.gguf"
            old_projector.write_bytes(b"GGUF" + b"old-projector")
            q8 = root / "mmproj-Q8_0.gguf"
            q8.write_bytes(b"GGUF" + b"quantized-projector")

            files = exporter.install_projector(gguf_dir, q8)
            self.assertTrue(main.is_file())
            self.assertFalse(old_projector.exists())
            self.assertTrue((gguf_dir / "mmproj-Q8_0.gguf").is_file())
            self.assertEqual({item["kind"] for item in files}, {"language_model", "vision_projector"})

    def test_compact_projector_export_rejects_invalid_gguf(self):
        import importlib.util
        import tempfile

        script = SCRIPT.parent / "compact_multimodal_export.py"
        export_spec = importlib.util.spec_from_file_location("compact_multimodal_export_invalid", script)
        exporter = importlib.util.module_from_spec(export_spec)
        export_spec.loader.exec_module(exporter)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gguf_dir = root / "gguf"
            gguf_dir.mkdir()
            (gguf_dir / "model.gguf").write_bytes(b"GGUF" + b"main")
            invalid = root / "bad.gguf"
            invalid.write_bytes(b"not-gguf")
            with self.assertRaises(RuntimeError):
                exporter.install_projector(gguf_dir, invalid)

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
