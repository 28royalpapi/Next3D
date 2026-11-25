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
        self.assertEqual(len(floorplan_data["door_centres"]), 9)
        room_bounds = {room["name"]: room["bounds"] for room in floorplan_data["room_rectangles"]}
        room_areas = {
            name: (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) / 1_000_000
            for name, bounds in room_bounds.items()
        }
        minima = {room["name"]: room.get("minimum_area_m2", 0) for room in floorplan_data["room_program"]}
        for room_name, minimum in minima.items():
            self.assertGreaterEqual(room_areas[room_name], minimum, room_name)

        def on_shared_boundary(a, b, point):
            ax0, ay0, ax1, ay1 = room_bounds[a]
            bx0, by0, bx1, by1 = room_bounds[b]
            px, py = point
            vertical_overlap = max(ay0, by0) < min(ay1, by1)
            horizontal_overlap = max(ax0, bx0) < min(ax1, bx1)
            if vertical_overlap and (ax1 == bx0 or bx1 == ax0):
                return abs(px - (ax1 if ax1 == bx0 else bx1)) <= 1 and max(ay0, by0) <= py <= min(ay1, by1)
            if horizontal_overlap and (ay1 == by0 or by1 == ay0):
                return abs(py - (ay1 if ay1 == by0 else by1)) <= 1 and max(ax0, bx0) <= px <= min(ax1, bx1)
            return False

        for door in floorplan_data["door_centres"]:
            a, b = door["connects"]
            if a == "entrance":
                self.assertEqual(door["point"][1], 0)
            else:
                self.assertTrue(on_shared_boundary(a, b, door["point"]), (a, b, door["point"]))
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
            "cad_geometry_topology",
            "cad_sketch_constraint_diagnosis",
            "cad_boolean_feature_planning",
            "cad_surface_modelling",
            "cad_mesh_quality",
            "cad_fem_preprocessing",
            "cad_cam_preprocessing",
            "bim_room_boundaries",
            "bim_asset_handover",
            "bim_revision_change_impact",
            "construction_4d_sequence",
            "civil_site_coordination",
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

    def test_synthetic_curriculum_is_split_without_record_overlap(self):
        lessons = module.make_synthetic_curriculum()
        splits = module.split_synthetic_curriculum(lessons)
        ids = {
            split: {row["record_id"] for row in rows}
            for split, rows in splits.items()
        }
        self.assertTrue(ids["train"].isdisjoint(ids["validation"]))
        self.assertTrue(ids["train"].isdisjoint(ids["test"]))
        self.assertTrue(ids["validation"].isdisjoint(ids["test"]))
        self.assertEqual(len(ids["train"]) + len(ids["validation"]) + len(ids["test"]), len(lessons))
        self.assertGreater(len(splits["validation"]), 0)
        self.assertGreater(len(splits["test"]), 0)
        for split in splits.values():
            self.assertTrue(all(row["completion"] for row in split))

    def test_swiss_dwellings_directory_admits_only_matching_building_split_records(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets.png").write_bytes(b"test-image")
            base = {
                "domain": "swiss_dwellings_floorplan",
                "source_doi": "10.5281/zenodo.7788422",
                "license": "CC-BY-4.0",
                "source_split": "train",
                "images": [str(root / "assets.png")],
                "completion": "{\"schema\":\"nextai.swiss_dwellings_floorplan.v1\"}",
            }
            for split in ("train", "validation", "test"):
                row = dict(base, source_split=split)
                (root / f"{split}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            rows = module.read_swiss_dwellings_directory(root)
            self.assertEqual({key: len(value) for key, value in rows.items()},
                             {"train": 1, "validation": 1, "test": 1})

            bad = dict(base, source_split="train", license="unknown")
            (root / "validation.jsonl").write_text(json.dumps(bad) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.read_swiss_dwellings_directory(root)

    def test_ifc_model_corpus_reader_requires_provenance_and_keeps_splits(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = {
                "source": "GNI-BIM Dataset",
                "doi": "10.5281/zenodo.19722012",
                "license": "CC-BY-4.0",
                "test_not_used_for_training": True,
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            for split in ("train", "validation", "test"):
                row = {
                    "domain": "ifc_model_summary",
                    "source": manifest["source"],
                    "source_doi": manifest["doi"],
                    "license": manifest["license"],
                    "source_file_sha256": "a" * 64,
                    "split_group": f"group-{split}",
                    "images": [],
                }
                (root / f"{split}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            rows, loaded_manifest = module.read_ifc_model_corpus(root)
            self.assertEqual(loaded_manifest["source"], "GNI-BIM Dataset")
            self.assertEqual({key: len(value) for key, value in rows.items()},
                             {"train": 1, "validation": 1, "test": 1})

            bad = {
                "domain": "ifc_element_inventory",
                "source": manifest["source"],
                "license": manifest["license"],
                "source_file_sha256": "b" * 64,
                "split_group": "group-bad",
            }
            (root / "test.jsonl").write_text(json.dumps(bad) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.read_ifc_model_corpus(root)

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

    def test_native_trace_reader_keeps_app_and_splits_separate(self):
        import tempfile

        message_set = [
            {"role": "system", "content": "NextAI"},
            {"role": "user", "content": "Create a constrained sketch."},
            {"role": "assistant", "content": "{\"steps\":[]}"},
        ]
        source = {
            "source_type": "synthetic",
            "license": "Apache-2.0",
            "terms_reviewed": True,
            "source_group_sha256": "a" * 64,
        }
        privacy = {
            "contains_personal_data": False,
            "redaction_status": "not_needed",
            "user_consent": False,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for split in ("train", "validation", "test"):
                row = {
                    "record_id": f"cad-{split}",
                    "application": "nextcad",
                    "application_version": "1.0",
                    "adapter_schema_version": "1.0",
                    "split": split,
                    "messages": message_set,
                    "source": source,
                    "privacy": privacy,
                }
                (root / f"{split}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            train = module.read_native(root / "train.jsonl", "nextcad_native", "nextcad", "train")
            validation = module.read_native(root / "validation.jsonl", "nextcad_native", "nextcad", "validation")
            test = module.read_native(root / "test.jsonl", "nextcad_native", "nextcad", "test")
            self.assertEqual([row["source_split"] for row in train + validation + test],
                             ["train", "validation", "test"])

            wrong_application = dict(json.loads((root / "train.jsonl").read_text()), application="nextbim")
            (root / "train.jsonl").write_text(json.dumps(wrong_application) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.read_native(root / "train.jsonl", "nextcad_native", "nextcad", "train")

            wrong_split = dict(json.loads((root / "validation.jsonl").read_text()), split="train")
            (root / "validation.jsonl").write_text(json.dumps(wrong_split) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.read_native(root / "validation.jsonl", "nextcad_native", "nextcad", "validation")

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



class GuidedDesignIntakeCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = module.make_design_intake_curriculum()
        cls.by_domain = {}
        for lesson in cls.lessons:
            cls.by_domain.setdefault(lesson["domain"], []).append(lesson)

    def test_residential_floorplan_interviews_for_the_requested_room_programme(self):
        rows = self.by_domain["design_intake_architecture"]
        self.assertEqual(len(rows), 36)
        first = rows[0]
        self.assertIn("3-bedroom floor plan", first["prompt"])
        for required_question in (
            "bungalow or a storey house",
            "How many master bedrooms",
            "How many toilets/bathrooms",
            "one sitting room",
            "store",
            "plot width and depth",
        ):
            self.assertIn(required_question.lower(), first["completion"].lower())

        follow_up = rows[1]["completion"].lower()
        self.assertIn("i will not ask you to repeat", follow_up)
        self.assertIn("plot width and depth", follow_up)
        self.assertIn("preliminary room sizes", follow_up)

        final = rows[2]["completion"].lower()
        self.assertIn("bedrooms: 3", final)
        self.assertIn("master bedrooms:", final)
        self.assertIn("toilets/bathrooms:", final)
        self.assertIn("ensuite", final)
        self.assertIn("shared/guest", final)
        self.assertIn("road on the shorter frontage", final)
        self.assertIn("will not claim permit approval", final)

    def test_vehicle_cad_intake_distinguishes_concept_from_roadworthy_design(self):
        rows = self.by_domain["design_intake_vehicle_cad"]
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[0]["prompt"], "Design a car in CAD.")
        first = rows[0]["completion"].lower()
        for term in ("vehicle type", "occupants", "wheelbase", "powertrain", "manufacturing drawings"):
            self.assertIn(term, first)
        follow_up = rows[1]["completion"].lower()
        self.assertIn("target vehicle envelope", follow_up)
        self.assertIn("editable parameters", follow_up)
        final = rows[2]["completion"].lower()
        self.assertIn("editable exterior and packaging concept", final)
        self.assertIn("not a roadworthy vehicle design", final)
        self.assertIn("crashworthiness", final)

    def test_mechanical_part_and_assembly_intakes_ask_for_interfaces(self):
        part = self.by_domain["design_intake_mechanical_part"]
        assembly = self.by_domain["design_intake_assembly_cad"]
        self.assertEqual(len(part), 30)
        self.assertEqual(len(assembly), 24)
        self.assertIn("mating dimensions", part[0]["completion"])
        self.assertIn("expected loads", part[0]["completion"])
        self.assertIn("named parameters", part[2]["completion"])
        self.assertIn("reference component", assembly[0]["completion"])
        self.assertIn("degrees of freedom", assembly[2]["completion"].lower())

    def test_bim_new_build_and_renovation_intakes_collect_model_information(self):
        new_build = self.by_domain["design_intake_bim_new_build"]
        renovation = self.by_domain["design_intake_bim_renovation"]
        self.assertEqual(len(new_build), 30)
        self.assertEqual(len(renovation), 24)
        for term in ("project location", "coordinate reference", "disciplines", "IFC schema", "classification"):
            self.assertIn(term.lower(), new_build[0]["completion"].lower())
        self.assertIn("information requirements", new_build[1]["completion"].lower())
        self.assertIn("as-built", renovation[1]["completion"].lower())
        self.assertIn("measured survey", renovation[2]["completion"].lower())
        self.assertIn("uncertain geometry flagged", renovation[2]["completion"].lower())

    def test_commercial_enclosure_and_infrastructure_design_families_are_present(self):
        expected = {
            "design_intake_commercial_architecture": 24,
            "design_intake_sheet_metal_cad": 24,
            "design_intake_civil_infrastructure": 24,
        }
        for domain, count in expected.items():
            self.assertEqual(len(self.by_domain[domain]), count)
        self.assertIn("existing floor plan", self.by_domain["design_intake_commercial_architecture"][1]["completion"].lower())
        self.assertIn("flat-pattern", self.by_domain["design_intake_sheet_metal_cad"][2]["completion"].lower())
        self.assertIn("verified survey", self.by_domain["design_intake_civil_infrastructure"][1]["completion"].lower())
        self.assertIn("schematic coordination model", self.by_domain["design_intake_civil_infrastructure"][2]["completion"].lower())

    def test_consumer_product_design_intake_covers_use_ergonomics_and_components(self):
        rows = self.by_domain["design_intake_consumer_product_cad"]
        self.assertEqual(len(rows), 24)
        for term in ("task should it perform", "who will use it", "target size", "material", "manufacturing"):
            self.assertIn(term, rows[0]["completion"].lower())
        self.assertIn("critical user-fit", rows[1]["completion"].lower())
        self.assertIn("separate components", rows[2]["completion"].lower())

    def test_technical_drawing_and_cam_intakes_never_invent_specifications(self):
        drawings = self.by_domain["design_intake_technical_drawing_cad"]
        cam = self.by_domain["design_intake_cam_cad"]
        self.assertEqual(len(drawings), 24)
        self.assertEqual(len(cam), 24)
        for term in ("projection method", "tolerances", "drawing standard", "edition"):
            self.assertIn(term, drawings[0]["completion"].lower())
        self.assertIn("leave them explicitly marked tbd", drawings[1]["completion"].lower())
        self.assertIn("not invent cutting data", cam[1]["completion"].lower())
        self.assertIn("no executable toolpath or g-code", cam[2]["completion"].lower())

    def test_all_three_turns_for_one_design_scenario_remain_in_one_split(self):
        splits = module.split_synthetic_curriculum(self.lessons)
        group_to_splits = {}
        group_to_count = {}
        for split, rows in splits.items():
            for row in rows:
                group = row["split_group"]
                group_to_splits.setdefault(group, set()).add(split)
                group_to_count[group] = group_to_count.get(group, 0) + 1
        self.assertEqual(len(group_to_splits), len(self.lessons) // 3)
        self.assertTrue(all(len(value) == 1 for value in group_to_splits.values()))
        self.assertTrue(all(count == 3 for count in group_to_count.values()))

    def test_guided_design_responses_match_nextai_runtime_json_contract(self):
        for lesson in self.lessons:
            with self.subTest(stage=lesson["stage"], domain=lesson["domain"]):
                response = json.loads(lesson["completion"])
                self.assertEqual(set(response), {"message", "plan"})
                self.assertIsInstance(response["message"], str)
                self.assertTrue(response["message"].strip())
                self.assertEqual(response["plan"], [])

    def test_dialogue_records_have_three_distinct_stages_and_context(self):
        stages = {}
        for lesson in self.lessons:
            stages.setdefault(lesson["split_group"], []).append(lesson["stage"])
        for values in stages.values():
            self.assertEqual(values, [
                "initial_clarification",
                "context_aware_follow_up",
                "confirmed_design_brief",
            ])

class DesignExecutionCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = module.make_design_execution_curriculum()
        cls.by_domain = {row["domain"]: row for row in cls.lessons}

        import ast
        registry_path = SCRIPT.parents[2] / "adapters/nextcad-ai/NextAI/next_ai/tool_registry.py"
        tree = ast.parse(registry_path.read_text(encoding="utf-8"))
        assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "TOOLS" for target in node.targets)
        )
        cls.tool_registry = ast.literal_eval(assignment.value)
        cls.tool_by_name = {item["name"]: item for item in cls.tool_registry}

    def test_watchtower_intake_asks_structure_occupancy_and_site_questions(self):
        rows = [
            row for row in module.make_design_intake_curriculum()
            if row["domain"] == "design_intake_watchtower_architecture"
        ]
        self.assertEqual(len(rows), 24)
        first = json.loads(rows[0]["completion"])["message"].lower()
        for term in ("steel frame", "reinforced concrete", "occupy the cabin", "observation-platform height",
                     "stair or ladder", "wind", "ground information"):
            self.assertIn(term, first)
        final = json.loads(rows[2]["completion"])["message"].lower()
        self.assertIn("visual concept only", final)
        self.assertIn("not engineered", final)
        self.assertIn("foundation", final)

    def test_design_execution_examples_use_real_registered_tools_and_valid_arguments(self):
        expected_domains = {
            "design_execution_residential_floorplan",
            "design_execution_watchtower_concept",
            "design_execution_parametric_mechanical_part",
            "design_execution_edit_existing_model",
        }
        self.assertEqual(set(self.by_domain), expected_domains)
        for domain, lesson in self.by_domain.items():
            response = json.loads(lesson["completion"])
            self.assertEqual(set(response), {"message", "plan"})
            self.assertIsInstance(response["message"], str)
            plan = response["plan"]
            self.assertTrue(1 <= len(plan) <= 20)
            for step in plan:
                self.assertEqual(set(step), {"tool", "args"})
                self.assertIn(step["tool"], self.tool_by_name)
                self.assertIsInstance(step["args"], dict)
                schema = self.tool_by_name[step["tool"]]["parameters"]
                properties = schema.get("properties", {})
                self.assertTrue(set(step["args"]).issubset(properties))
                self.assertTrue(set(schema.get("required", [])).issubset(step["args"]))

    def test_residential_floorplan_plan_builds_named_editable_zones_and_annotations(self):
        response = json.loads(self.by_domain["design_execution_residential_floorplan"]["completion"])
        names = [step["tool"] for step in response["plan"]]
        self.assertEqual(names.count("create_draft_wire"), 9)
        self.assertEqual(names.count("create_draft_text"), 8)
        self.assertEqual(names.count("create_draft_dimension"), 2)
        labels = [step["args"].get("label", "") for step in response["plan"]]
        self.assertTrue(any("Master bedroom" in label for label in labels))
        self.assertTrue(any("Bedroom 2" in label for label in labels))
        self.assertTrue(any("Bedroom 3" in label for label in labels))
        self.assertTrue(any("Shared bathroom" in label for label in labels))
        self.assertIn("not yet modelled or verified", response["message"])

    def test_watchtower_plan_creates_native_component_envelopes_and_member_schedule(self):
        response = json.loads(self.by_domain["design_execution_watchtower_concept"]["completion"])
        plan = response["plan"]
        names = [step["tool"] for step in plan]
        self.assertEqual(names.count("create_arch_structure"), 4)
        self.assertEqual(names.count("create_part_box"), 6)
        self.assertEqual(names.count("create_arch_wall"), 4)
        self.assertEqual(names.count("create_draft_dimension"), 2)
        self.assertEqual(names.count("create_draft_text"), 1)
        labels = [step["args"].get("label", "") for step in plan]
        self.assertTrue(any(label.startswith("C01") for label in labels))
        self.assertTrue(any(label.startswith("B01") for label in labels))
        schedule = next(step for step in plan if step["tool"] == "create_draft_text")
        self.assertIn("NOT engineered sizes", schedule["args"]["text"])
        self.assertIn("foundations", response["message"].lower())
        self.assertIn("not structurally designed", response["message"].lower())

    def test_parametric_part_plan_uses_body_sketch_pad_and_pocket_in_order(self):
        response = json.loads(self.by_domain["design_execution_parametric_mechanical_part"]["completion"])
        names = [step["tool"] for step in response["plan"]]
        self.assertEqual(names, [
            "create_partdesign_body",
            "create_partdesign_sketch",
            "add_sketch_polygon",
            "create_partdesign_pad",
            "create_partdesign_sketch",
            "add_sketch_circle",
            "add_sketch_circle",
            "add_sketch_circle",
            "add_sketch_circle",
            "create_partdesign_pocket",
        ])
        pocket = response["plan"][-1]["args"]
        self.assertTrue(pocket["through_all"])
        self.assertFalse(pocket["reversed"])
        self.assertIn("material, tolerances, loads", response["message"].lower())

    def test_edit_example_modifies_existing_element_without_creating_duplicate(self):
        response = json.loads(self.by_domain["design_execution_edit_existing_model"]["completion"])
        self.assertEqual([step["tool"] for step in response["plan"]], ["edit_native_property"] * 3)
        self.assertEqual([step["args"]["property_name"] for step in response["plan"]],
                         ["Width", "Height", "Label"])
        self.assertTrue(all(step["args"]["object_name"] == "B01Beam" for step in response["plan"]))
        self.assertIn("will not create a duplicate", response["message"].lower())


if __name__ == "__main__":
    unittest.main()
