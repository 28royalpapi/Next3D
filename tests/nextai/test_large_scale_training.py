from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.nextai.audit_nextai_corpus import audit_corpus, render_record_text
from training.nextai.buildeng_dataset import make_buildeng_record, SOURCE_LICENSE
from training.nextai.generate_verified_engineering_cases import (
    generate_cases,
    solve_beam_udl,
    solve_axial_bar,
    solve_pipe_continuity,
    solve_effective_stress,
    solve_slab_concrete_quantity,
    solve_three_phase_power,
    solve_leveling,
    solve_earthwork_average_end_area,
    FAMILY_BUILDERS,
)
from training.nextai.run_large_scale_training import (
    compare_heldout_evaluations,
    require_token_target,
    validate_native_trace_coverage,
)
from training.nextai.prepare_public_corpora import merge_native_trace_splits
from training.nextai.prepare_large_scale_corpus import (
    build_capability_census_command,
    capability_census_summary,
    inspect_native_trace_inputs,
    native_trace_command_args,
)
from training.nextai.evaluate_nextai import fingerprint_records
from training.nextai.train_nextai import (
    IndexedJSONL,
    validate_training_splits,
    conversation_row_for_collator,
    build_progressive_curriculum_order,
    curriculum_stage_for_record,
    validate_resume_compatibility,
)


class FakeTokenizer:
    name_or_path = "fake-test-tokenizer"

    def encode(self, text, add_special_tokens=False):
        return text.split()


class CapabilityCensusIntegrationTests(unittest.TestCase):
    def test_builder_forwards_live_runtime_report_and_required_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "nextcad-runtime.json"
            report.write_text("{}", encoding="utf-8")
            command = build_capability_census_command(
                root / "census", runtime_report=report, require_runtime=True
            )
            self.assertIn("--nextcad-runtime-report", command)
            self.assertIn(str(report.resolve()), command)
            self.assertIn("--require-nextcad-runtime", command)

    def test_required_live_runtime_without_report_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires --nextcad-runtime-report"):
            build_capability_census_command(Path("census"), require_runtime=True)

    def test_missing_live_runtime_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "absent.json"
            with self.assertRaisesRegex(FileNotFoundError, "NextCAD runtime census report does not exist"):
                build_capability_census_command(Path(temp) / "census", runtime_report=missing)

    def test_census_summary_distinguishes_live_inventory_from_source_only_catalogue(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "census.json"
            census = {
                "schema": "nextai.capability_census.v1",
                "sources": {"nextcad": {"runtime_capture": "captured", "python_api_enumeration_scope": "loaded public Python names only"}},
                "counts": {
                    "nextcad_runtime_census_complete": True,
                    "nextcad_runtime_commands": 1200,
                    "nextcad_runtime_api_modules": 35,
                    "nextcad_runtime_api_members": 8200,
                    "nextcad_source_modules": 55,
                    "nextbim_registered_commands": 215,
                    "total_discovered_capabilities": 9615,
                    "skill_obligations": 96150,
                },
            }
            path.write_text(json.dumps(census), encoding="utf-8")
            summary = capability_census_summary(path)
            self.assertTrue(summary["nextcad_runtime_census_complete"])
            self.assertEqual(summary["nextcad_runtime_commands"], 1200)
            self.assertEqual(summary["nextcad_runtime_api_members"], 8200)
            self.assertFalse(summary["skill_obligations_are_training_examples"])
            self.assertFalse(summary["native_mastery_claimed"])


class NativeTraceBuildIntegrationTests(unittest.TestCase):
    def _write_trace(self, path: Path, application: str, split: str, record_id: str):
        row = {
            "application": application,
            "split": split,
            "record_id": record_id,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "request"},
                {"role": "assistant", "content": "validated native plan"},
            ],
            "native_trace_evidence": {
                "validation_overall": "passed",
                "round_trip_passed": True,
                "recompute_passed": True,
                "after_state_sha256": "a" * 64,
                "operation_count": 1,
                "applied_operation_count": 1,
                "read_only_operation_count": 0,
                "operation_trace_sha256": "b" * 64,
            },
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_all_six_native_trace_inputs_are_fingerprinted_and_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = {}
            for application in ("nextcad", "nextbim"):
                for split in ("train", "validation", "test"):
                    key = f"{application}_native_{split}"
                    path = root / f"{key}.jsonl"
                    self._write_trace(path, application, split, key)
                    inputs[key] = path
            summary = inspect_native_trace_inputs(inputs, require_all=True)
            self.assertEqual(set(summary), set(inputs))
            self.assertTrue(all(item["status"] == "present" for item in summary.values()))
            self.assertTrue(all(item["records"] == 1 for item in summary.values()))
            self.assertTrue(all(len(item["sha256"]) == 64 for item in summary.values()))
            forwarded = native_trace_command_args(summary)
            self.assertEqual(len(forwarded), 12)
            self.assertEqual(forwarded[0], "--nextcad-native-train")
            self.assertIn("--nextbim-native-test", forwarded)

    def test_full_native_trace_mode_requires_both_applications_and_all_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "one.jsonl"
            self._write_trace(path, "nextcad", "train", "cad-train")
            with self.assertRaisesRegex(ValueError, "all six"):
                inspect_native_trace_inputs({"nextcad_native_train": path}, require_all=True)

    def test_native_trace_file_rejects_wrong_application_or_split(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wrong.jsonl"
            self._write_trace(path, "nextbim", "train", "wrong-app")
            with self.assertRaisesRegex(ValueError, "expected 'nextcad'"):
                inspect_native_trace_inputs({"nextcad_native_train": path})

    def test_native_trace_file_rejects_malformed_json_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            malformed = root / "malformed.jsonl"
            malformed.write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid native trace JSON"):
                inspect_native_trace_inputs({"nextcad_native_train": malformed})
            duplicate = root / "duplicate.jsonl"
            self._write_trace(duplicate, "nextcad", "train", "same")
            with duplicate.open("a", encoding="utf-8") as handle:
                row = {"application": "nextcad", "split": "train", "record_id": "same",
                       "messages": [{"role": "system"}, {"role": "user"}, {"role": "assistant"}]}
                handle.write(json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "Duplicate native trace record_id"):
                inspect_native_trace_inputs({"nextcad_native_train": duplicate})


class NativeTraceRetentionTests(unittest.TestCase):
    def test_native_train_validation_and_test_traces_are_not_lost_by_public_caps(self):
        base_train = [{"record_id": "public-train"}]
        base_validation = [{"record_id": "public-validation"}]
        base_test = [{"record_id": "public-test"}]
        native = {
            "train": [{"record_id": f"cad-train-{i}"} for i in range(100)],
            "validation": [{"record_id": "cad-validation"}, {"record_id": "bim-validation"}],
            "test": [{"record_id": "cad-test"}, {"record_id": "bim-test"}],
        }
        train, validation, test = merge_native_trace_splits(
            base_train, base_validation, base_test, native
        )
        self.assertEqual(len(train), 101)
        self.assertEqual(len(validation), 3)
        self.assertEqual(len(test), 3)
        self.assertEqual(sum(row["record_id"].startswith("cad-train-") for row in train), 100)
        self.assertEqual({row["record_id"] for row in validation}, {
            "public-validation", "cad-validation", "bim-validation"
        })
        self.assertEqual({row["record_id"] for row in test}, {
            "public-test", "cad-test", "bim-test"
        })


class NativeTraceTrainingGateTests(unittest.TestCase):
    def test_strict_training_gate_requires_all_six_non_empty_native_splits(self):
        manifest = {
            "native_execution_traces_retained_outside_public_sampling_caps": True,
            "native_execution_trace_records": {
                app: {split: 3 for split in ("train", "validation", "test")}
                for app in ("nextcad", "nextbim")
            },
        }
        report = validate_native_trace_coverage(manifest, require=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["total_native_execution_trace_records"], 18)
        self.assertFalse(report["native_execution_mastery_claimed"])

    def test_strict_training_gate_blocks_when_native_heldout_split_is_empty(self):
        manifest = {
            "native_execution_traces_retained_outside_public_sampling_caps": True,
            "native_execution_trace_records": {
                app: {split: 2 for split in ("train", "validation", "test")}
                for app in ("nextcad", "nextbim")
            },
        }
        manifest["native_execution_trace_records"]["nextbim"]["test"] = 0
        with self.assertRaisesRegex(RuntimeError, "before model/tokenizer download or GPU use"):
            validate_native_trace_coverage(manifest, require=True)

    def test_non_strict_training_gate_reports_missing_coverage_without_claiming_mastery(self):
        report = validate_native_trace_coverage({}, require=False)
        self.assertEqual(report["status"], "NOT_REQUIRED")
        self.assertEqual(report["total_native_execution_trace_records"], 0)
        self.assertTrue(report["missing_or_empty_splits"])
        self.assertFalse(report["native_execution_mastery_claimed"])


class LargeScaleTrainingTests(unittest.TestCase):
    def test_400m_token_gate_blocks_underfilled_corpus_by_default(self):
        with self.assertRaisesRegex(RuntimeError, "Refusing GPU fine-tuning"):
            require_token_target(125_000_000, 400_000_000)

    def test_400m_token_gate_reports_exact_shortfall(self):
        with self.assertRaisesRegex(RuntimeError, "275,000,000"):
            require_token_target(125_000_000, 400_000_000)

    def test_explicit_pilot_override_is_recorded_not_misreported_as_target_met(self):
        report = require_token_target(125_000_000, 400_000_000, allow_below_target=True)
        self.assertEqual(report["decision"], "PILOT_OVERRIDE")
        self.assertEqual(report["shortfall_tokens"], 275_000_000)
        self.assertFalse(report["target_met"])
        self.assertTrue(report["pilot_override_used"])

    def test_full_token_target_passes_without_pilot_override(self):
        report = require_token_target(400_000_000, 400_000_000)
        self.assertEqual(report["decision"], "PASS")
        self.assertTrue(report["target_met"])
        self.assertFalse(report["pilot_override_used"])

    def test_conversation_text_and_tools_are_counted_separately(self):
        row = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Create a beam"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Need span and loads"}]},
            ],
            "tools": [{"type": "function", "function": {"name": "inspect_model"}}],
        }
        text, schemas = render_record_text(row)
        self.assertIn("<user>", text)
        self.assertIn("Create a beam", text)
        self.assertIn("Need span and loads", text)
        self.assertIn("inspect_model", schemas)

    def test_token_audit_counts_splits_and_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "assets" / "small.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"fake-image-bytes")
            rows = {
                "train": [
                    {"record_id": "train-1", "domain": "structural", "source": "authored",
                     "license": "project-authored", "prompt": "Calculate beam reaction",
                     "completion": "Reaction is 12 kN", "images": ["assets/small.jpg"]}
                ],
                "validation": [
                    {"record_id": "validation-1", "domain": "bim", "source": "public",
                     "license": "MIT", "prompt": "What is IFC?", "completion": "A data schema."}
                ],
                "test": [
                    {"record_id": "test-1", "domain": "cad", "source": "public",
                     "license": "Apache-2.0", "prompt": "List features", "completion": "Pad then pocket."}
                ],
            }
            for split, records in rows.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in records),
                    encoding="utf-8",
                )
            report = audit_corpus(root, FakeTokenizer())
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["missing_image_file_count"], 0)
            self.assertGreater(report["train_text_tokens"], 0)
            self.assertEqual(report["image_files_total"], 1)
            self.assertEqual(report["missing_image_files"], [])

    def test_exact_duplicate_text_within_train_split_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repeated = {"prompt": "Explain a simply supported beam.", "completion": "The reactions are equal for a centred load."}
            records = {
                "train": [
                    {"record_id": "train-1", **repeated},
                    {"record_id": "train-2", **repeated},
                ],
                "validation": [{"record_id": "validation-1", "prompt": "What is IFC?", "completion": "An information schema."}],
                "test": [{"record_id": "test-1", "prompt": "What is a pad?", "completion": "A CAD extrusion feature."}],
            }
            for split, rows in records.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "duplicates within a split"):
                audit_corpus(root, FakeTokenizer())

    def test_cross_split_source_group_leakage_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = {"source_group_sha256": "same-project-hash"}
            records = {
                "train": [{"record_id": "a", "prompt": "A", "completion": "B", **source}],
                "validation": [{"record_id": "b", "prompt": "C", "completion": "D", **source}],
                "test": [{"record_id": "c", "prompt": "E", "completion": "F"}],
            }
            for split, rows in records.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "Cross-split source identity leakage"):
                audit_corpus(root, FakeTokenizer())

    def test_training_split_validation_resolves_relative_images_from_corpus_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "assets" / "small.jpg"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"placeholder-asset-bytes")
            records = {
                "train": [{"record_id": "train-1", "prompt": "A", "completion": "B",
                           "images": ["assets/small.jpg"]}],
                "validation": [{"record_id": "validation-1", "prompt": "C", "completion": "D"}],
                "test": [{"record_id": "test-1", "prompt": "E", "completion": "F"}],
            }
            indices = {}
            for split, rows in records.items():
                path = root / f"{split}.jsonl"
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                indices[split] = IndexedJSONL(path)
            try:
                report = validate_training_splits(
                    indices["train"], indices["validation"], indices["test"]
                )
                self.assertEqual(report["status"], "PASS")
                self.assertEqual(report["splits"]["train"]["image_files"], 1)
            finally:
                for indexed in indices.values():
                    indexed.close()

    def test_missing_image_is_reported_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = {
                "train": [{"record_id": "a", "prompt": "A", "completion": "B", "images": [str(root / "missing.jpg")]}],
                "validation": [{"record_id": "b", "prompt": "C", "completion": "D"}],
                "test": [{"record_id": "c", "prompt": "E", "completion": "F"}],
            }
            for split, rows in records.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "Missing image assets"):
                audit_corpus(root, FakeTokenizer())
            report = audit_corpus(root, FakeTokenizer(), allow_missing_images=True)
            self.assertEqual(report["status"], "OVERRIDE_MISSING_IMAGES")
            self.assertEqual(report["missing_image_file_count"], 1)
            self.assertEqual(len(report["missing_image_files"]), 1)


    def test_buildeng_record_preserves_provenance_and_l0_evidence(self):
        row = {
            "category": "structural/beams",
            "tags": ["reaction", "deterministic"],
            "messages": [
                {"role": "system", "content": "You are a careful engineering assistant."},
                {"role": "user", "content": "A simply supported beam spans 4 m and carries 8 kN/m."},
                {"role": "assistant", "content": "For a simply supported beam with a full-span UDL, each support reaction is wL/2 = 16 kN. The maximum sagging moment is wL^2/8 = 16 kN m. This is a basic statics result, not a member design."},
            ],
        }
        record = make_buildeng_record(row, 17)
        self.assertEqual(record["license"], "Apache-2.0")
        self.assertEqual(record["license"], SOURCE_LICENSE)
        self.assertEqual(record["evidence_level"], "L0")
        self.assertFalse(record["native_execution_verified"])
        self.assertEqual(record["source_category"], "structural/beams")
        self.assertEqual(record["source_split"], "train")
        self.assertIn(record["split"], {"train", "validation", "test"})

    def test_buildeng_identical_user_brief_cannot_leak_across_splits(self):
        first = {
            "category": "structural/beams",
            "tags": ["reaction"],
            "messages": [
                {"role": "system", "content": "Careful engineer."},
                {"role": "user", "content": "Calculate support reactions for a 4 m beam."},
                {"role": "assistant", "content": "The data is incomplete; provide the support arrangement and loading before calculating."},
            ],
        }
        second = {
            "category": "structural/beams",
            "tags": ["adversarial"],
            "messages": [
                {"role": "system", "content": "Different system prompt."},
                {"role": "user", "content": "  Calculate support reactions for a 4 m beam.  "},
                {"role": "assistant", "content": "The support type and loading must be known. A 4 m span alone is not enough to calculate reactions."},
            ],
        }
        a = make_buildeng_record(first, 1)
        b = make_buildeng_record(second, 2)
        self.assertEqual(a["source_group_sha256"], b["source_group_sha256"])
        self.assertEqual(a["split"], b["split"])

    def test_buildeng_rejects_incomplete_or_non_text_conversation(self):
        row = {
            "category": "structural/beams",
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "Please calculate."},
                {"role": "assistant", "content": " "},
            ],
        }
        with self.assertRaises(ValueError):
            make_buildeng_record(row, 1)


class AnalyticEngineeringCurriculumTests(unittest.TestCase):
    def test_engineering_formula_reference_cases(self):
        beam = solve_beam_udl({
            "span_m": 4.0,
            "udl_kN_per_m": 10.0,
            "elastic_modulus_GPa": 200.0,
            "second_moment_mm4": 80_000_000.0,
        })
        self.assertEqual(beam["values"]["reaction_A_kN"], 20.0)
        self.assertEqual(beam["values"]["reaction_B_kN"], 20.0)
        self.assertEqual(beam["values"]["maximum_sagging_moment_kN_m"], 20.0)
        self.assertAlmostEqual(beam["values"]["maximum_deflection_mm"], 2.083333, places=5)

        axial = solve_axial_bar({
            "axial_force_kN": 100.0,
            "area_mm2": 1000.0,
            "length_m": 2.0,
            "elastic_modulus_GPa": 200.0,
        })
        self.assertEqual(axial["values"]["normal_stress_MPa"], 100.0)
        self.assertEqual(axial["values"]["normal_strain"], 0.0005)
        self.assertEqual(axial["values"]["elongation_mm"], 1.0)

        flow = solve_pipe_continuity({
            "flow_L_per_s": 10.0,
            "internal_diameter_mm": 100.0,
        })
        self.assertAlmostEqual(flow["values"]["mean_velocity_m_per_s"], 1.27324, places=5)

        stress = solve_effective_stress({
            "total_vertical_stress_kPa": 250.0,
            "pore_water_pressure_kPa": 100.0,
        })
        self.assertEqual(stress["values"]["effective_vertical_stress_kPa"], 150.0)

        slab = solve_slab_concrete_quantity({
            "slab_length_m": 5.0,
            "slab_width_m": 4.0,
            "slab_thickness_m": 0.15,
        })
        self.assertEqual(slab["values"]["concrete_volume_m3"], 3.0)

        power = solve_three_phase_power({
            "line_voltage_V": 400.0,
            "line_current_A": 10.0,
            "power_factor": 0.8,
        })
        self.assertAlmostEqual(power["values"]["apparent_power_kVA"], 6.928203, places=5)
        self.assertAlmostEqual(power["values"]["active_power_kW"], 5.542563, places=5)

        leveling = solve_leveling({
            "benchmark_reduced_level_m": 100.0,
            "backsight_m": 1.5,
            "foresight_m": 2.2,
        })
        self.assertEqual(leveling["values"]["height_of_instrument_m"], 101.5)
        self.assertEqual(leveling["values"]["new_point_reduced_level_m"], 99.3)

        earthwork = solve_earthwork_average_end_area({
            "section_spacing_m": 20.0,
            "cut_area_1_m2": 5.0,
            "cut_area_2_m2": 7.0,
        })
        self.assertEqual(earthwork["values"]["earthwork_volume_m3"], 120.0)

    def test_generator_has_17_formula_families_and_keeps_all_splits(self):
        self.assertEqual(len(FAMILY_BUILDERS), 17)
        first, manifest = generate_cases(cases_per_domain=3, seed=3407)
        second, _ = generate_cases(cases_per_domain=3, seed=3407)
        self.assertEqual(manifest["total_records"], 17 * 3)
        self.assertEqual(manifest["families"], {key: 3 for key in sorted(FAMILY_BUILDERS)})
        for split in ("train", "validation", "test"):
            self.assertEqual(
                [row["record_id"] for row in first[split]],
                [row["record_id"] for row in second[split]],
            )
        all_rows = [row for split in first.values() for row in split]
        self.assertEqual(len({row["record_id"] for row in all_rows}), 51)
        for row in all_rows:
            expected = row["expected"]
            self.assertEqual(row["evidence_level"], "L0")
            self.assertFalse(row["native_execution_verified"])
            self.assertTrue(expected["governing_equations"])
            self.assertTrue(expected["units"])
            self.assertTrue(expected["assumptions"])
            self.assertEqual(row["source_split"], "original_synthetic")

    def test_all_17_solver_families_match_independent_equations(self):
        import math

        center = solve_beam_udl({
            "span_m": 4.0, "udl_kN_per_m": 10.0,
            "elastic_modulus_GPa": 200.0, "second_moment_mm4": 80_000_000.0,
        })
        center_load = __import__(
            "training.nextai.generate_verified_engineering_cases",
            fromlist=["solve_beam_centre_load"],
        ).solve_beam_centre_load({
            "span_m": 4.0, "central_point_load_kN": 20.0,
            "elastic_modulus_GPa": 200.0, "second_moment_mm4": 80_000_000.0,
        })
        self.assertAlmostEqual(center_load["values"]["maximum_deflection_mm"], 1.666667, places=5)

        from training.nextai.generate_verified_engineering_cases import (
            solve_cantilever_tip_load, solve_solid_shaft_torsion,
            solve_darcy_weisbach, solve_manning_rectangular,
            solve_consolidation, solve_rebar_mass, solve_gear_ratio,
            solve_rectangle_section,
        )
        cantilever = solve_cantilever_tip_load({
            "cantilever_length_m": 2.0, "tip_load_kN": 10.0,
            "elastic_modulus_GPa": 200.0, "second_moment_mm4": 80_000_000.0,
        })
        self.assertEqual(cantilever["values"]["fixed_end_moment_kN_m"], 20.0)
        self.assertAlmostEqual(cantilever["values"]["tip_deflection_mm"], 1.666667, places=5)

        torque, diameter, shaft_length, shear_modulus = 1.0e6, 50.0, 1000.0, 80_000.0
        torsion = solve_solid_shaft_torsion({
            "torque_kN_m": 1.0, "shaft_diameter_mm": 50.0,
            "shaft_length_m": 1.0, "shear_modulus_GPa": 80.0,
        })
        self.assertAlmostEqual(
            torsion["values"]["maximum_shear_stress_MPa"],
            16.0 * torque / (math.pi * diameter**3),
            places=5,
        )
        polar = math.pi * diameter**4 / 32.0
        self.assertAlmostEqual(
            torsion["values"]["angle_of_twist_rad"],
            torque * shaft_length / (shear_modulus * polar),
            places=7,
        )

        q, d, length, f = 0.02, 0.2, 1000.0, 0.02
        area = math.pi * d**2 / 4.0
        velocity = q / area
        darcy = solve_darcy_weisbach({
            "flow_L_per_s": 20.0, "internal_diameter_mm": 200.0,
            "pipe_length_m": length, "darcy_friction_factor": f,
        })
        self.assertAlmostEqual(darcy["values"]["mean_velocity_m_per_s"], velocity, places=5)
        self.assertAlmostEqual(
            darcy["values"]["darcy_head_loss_m"],
            f * (length / d) * velocity**2 / (2.0 * 9.80665),
            places=5,
        )

        b, depth, n, slope = 3.0, 1.0, 0.015, 0.001
        manning_area = b * depth
        radius = manning_area / (b + 2.0 * depth)
        expected_velocity = (1.0 / n) * radius**(2.0 / 3.0) * math.sqrt(slope)
        manning = solve_manning_rectangular({
            "channel_width_m": b, "flow_depth_m": depth,
            "manning_n": n, "energy_slope": slope,
        })
        self.assertAlmostEqual(manning["values"]["discharge_m3_per_s"], manning_area * expected_velocity, places=5)

        cc, h, e0, sigma0, delta = 0.3, 5.0, 0.8, 100.0, 100.0
        consolidation = solve_consolidation({
            "compression_index_Cc": cc, "compressible_layer_thickness_m": h,
            "initial_void_ratio": e0, "initial_effective_stress_kPa": sigma0,
            "stress_increment_kPa": delta,
        })
        expected_settlement = cc * h / (1.0 + e0) * math.log10((sigma0 + delta) / sigma0) * 1000.0
        self.assertAlmostEqual(
            consolidation["values"]["primary_consolidation_settlement_mm"],
            expected_settlement,
            places=5,
        )

        density, bar_d, bar_length = 7850.0, 0.016, 100.0
        rebar = solve_rebar_mass({"bar_diameter_mm": 16.0, "total_bar_length_m": bar_length})
        self.assertAlmostEqual(
            rebar["values"]["total_steel_mass_kg"],
            density * math.pi * bar_d**2 / 4.0 * bar_length,
            places=5,
        )

        gear = solve_gear_ratio({
            "driver_teeth": 20, "driven_teeth": 60, "driver_speed_rpm": 1500.0,
        })
        self.assertEqual(gear["values"]["driven_speed_rpm"], 500.0)

        section = solve_rectangle_section({"breadth_mm": 200.0, "depth_mm": 400.0})
        expected_i = 200.0 * 400.0**3 / 12.0
        self.assertAlmostEqual(section["values"]["second_moment_about_strong_axis_mm4"], expected_i, places=3)
        self.assertAlmostEqual(section["values"]["elastic_section_modulus_mm3"], expected_i / 200.0, places=3)

    def test_generator_rejects_negative_case_count(self):
        with self.assertRaises(ValueError):
            generate_cases(cases_per_domain=-1)


class HeldOutEvaluationDisciplineTests(unittest.TestCase):
    def test_trainer_does_not_evaluate_test_split_during_training(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/train_nextai.py").read_text(encoding="utf-8")
        self.assertIn("validation_by_domain = {", source)
        self.assertNotIn("evaluate_by_domain(test_rows", source)
        self.assertIn('"status": "PENDING_POST_TRAINING"', source)
        self.assertIn('"status": "PENDING_POST_TRAINING_EVALUATION"', source)
        self.assertIn("eval_dataset=ConversationDataset(validation_rows)", source)

    def test_runner_uses_validation_before_training_and_test_only_after(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/run_large_scale_training.py").read_text(encoding="utf-8")
        train_pos = source.index("execute(training_command, log_path, env)")
        validation_pos = source.index('"--test-jsonl", str(validation_file)')
        test_pos = source.index('"--test-jsonl", str(test_file)')
        self.assertLess(validation_pos, train_pos)
        self.assertGreater(test_pos, train_pos)
        self.assertIn("test_evaluated_only_after_candidate_training", source)

    def test_heldout_comparison_compares_base_and_candidate_by_domain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.json"
            candidate = root / "candidate.json"
            output = root / "comparison.json"
            base.write_text(json.dumps({
                "model": "base",
                "test_records": 20,
                "source_test_split_records": 20,
                "source_test_split_sha256": "full-split-sha256",
                "evaluated_records_sha256": "evaluated-subset-sha256",
                "evaluation_is_partial": False,
                "evaluation_limit": 0,
                "test_split_used_for_training": False,
                "metrics_by_domain": {
                    "structural": {"token_f1": 0.5, "plan_shape_valid": 0.7, "records": 20}
                },
            }), encoding="utf-8")
            candidate.write_text(json.dumps({
                "model": "candidate",
                "test_records": 20,
                "source_test_split_records": 20,
                "source_test_split_sha256": "full-split-sha256",
                "evaluated_records_sha256": "evaluated-subset-sha256",
                "evaluation_is_partial": False,
                "evaluation_limit": 0,
                "test_split_used_for_training": False,
                "metrics_by_domain": {
                    "structural": {"token_f1": 0.6, "plan_shape_valid": 0.8, "records": 20}
                },
            }), encoding="utf-8")
            report = compare_heldout_evaluations(base, candidate, output)
            self.assertTrue(report["same_held_out_test_split"])
            self.assertTrue(report["test_evaluated_only_after_candidate_training"])
            self.assertAlmostEqual(
                report["metrics_by_domain"]["structural"]["token_f1"]["delta"], 0.1
            )
            self.assertTrue(output.is_file())

    def test_heldout_comparison_rejects_same_count_but_different_source_split(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.json"
            candidate = root / "candidate.json"
            output = root / "comparison.json"
            common = {
                "test_records": 20,
                "evaluated_records_sha256": "same-evaluated-subset",
                "test_split_used_for_training": False,
            }
            base.write_text(json.dumps({
                **common,
                "source_test_split_sha256": "source-split-A",
            }), encoding="utf-8")
            candidate.write_text(json.dumps({
                **common,
                "source_test_split_sha256": "source-split-B",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact same source held-out test split fingerprint"):
                compare_heldout_evaluations(base, candidate, output)

    def test_heldout_comparison_rejects_different_evaluated_subsets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.json"
            candidate = root / "candidate.json"
            output = root / "comparison.json"
            common = {
                "test_records": 10,
                "source_test_split_sha256": "same-full-split",
                "test_split_used_for_training": False,
            }
            base.write_text(json.dumps({
                **common,
                "evaluated_records_sha256": "first-ten-records",
            }), encoding="utf-8")
            candidate.write_text(json.dumps({
                **common,
                "evaluated_records_sha256": "different-ten-records",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact same evaluated record subset fingerprint"):
                compare_heldout_evaluations(base, candidate, output)

    def test_evaluation_fingerprint_is_canonical_and_order_sensitive(self):
        first = [
            {"record_id": "one", "value": 1},
            {"record_id": "two", "value": 2},
        ]
        reordered_keys = [
            {"value": 1, "record_id": "one"},
            {"value": 2, "record_id": "two"},
        ]
        reordered_rows = list(reversed(first))
        self.assertEqual(fingerprint_records(first), fingerprint_records(reordered_keys))
        self.assertNotEqual(fingerprint_records(first), fingerprint_records(reordered_rows))
        self.assertNotEqual(
            fingerprint_records(first),
            fingerprint_records([{"record_id": "one", "value": 9}, first[1]]),
        )

    def test_heldout_comparison_rejects_different_test_record_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base.json"
            candidate = root / "candidate.json"
            output = root / "comparison.json"
            base.write_text(json.dumps({"test_records": 20}), encoding="utf-8")
            candidate.write_text(json.dumps({"test_records": 19}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "same record count"):
                compare_heldout_evaluations(base, candidate, output)


class IndexedJSONLTests(unittest.TestCase):
    def test_indexed_jsonl_supports_random_access_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "train.jsonl"
            rows = [
                {"record_id": "r0", "domain": "cad"},
                {"record_id": "r1", "domain": "bim"},
                {"record_id": "r2", "domain": "structural"},
            ]
            path.write_text(
                "\n" + json.dumps(rows[0]) + "\n\n"
                + json.dumps(rows[1]) + "\n"
                + json.dumps(rows[2]) + "\n",
                encoding="utf-8",
            )
            indexed = IndexedJSONL(path)
            self.assertEqual(len(indexed), 3)
            self.assertEqual(indexed[0]["record_id"], "r0")
            self.assertEqual(indexed[2]["record_id"], "r2")
            self.assertEqual(indexed[-1]["record_id"], "r2")
            self.assertEqual(
                [row["record_id"] for row in indexed],
                ["r0", "r1", "r2"],
            )
            indexed.close()

    def test_integrity_gate_accepts_indexed_splits_and_rejects_group_leakage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_record = {
                "messages": [
                    {"role": "user", "content": "Explain the equation."},
                    {"role": "assistant", "content": "Use the supplied assumptions and units."},
                ],
                "source_group_sha256": "one-source-group",
            }
            split_records = {
                "train": [{**source_record, "record_id": "train-1"}],
                "validation": [{"record_id": "val-1", **source_record}],
                "test": [{"record_id": "test-1", "messages": source_record["messages"]}],
            }
            indices = {}
            for split, records in split_records.items():
                path = root / f"{split}.jsonl"
                path.write_text(
                    "".join(json.dumps(record) + "\n" for record in records),
                    encoding="utf-8",
                )
                indices[split] = IndexedJSONL(path)
            with self.assertRaisesRegex(ValueError, "Data leakage detected"):
                validate_training_splits(
                    indices["train"], indices["validation"], indices["test"]
                )
            for indexed in indices.values():
                indexed.close()

    def test_integrity_index_uses_disk_backed_sqlite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = {
                "train": [{"record_id": "t1", "prompt": "A", "completion": "B"}],
                "validation": [{"record_id": "v1", "prompt": "C", "completion": "D"}],
                "test": [{"record_id": "x1", "prompt": "E", "completion": "F"}],
            }
            indices = {}
            for split, records in rows.items():
                path = root / f"{split}.jsonl"
                path.write_text(
                    "".join(json.dumps(record) + "\n" for record in records),
                    encoding="utf-8",
                )
                indices[split] = IndexedJSONL(path)
            report = validate_training_splits(
                indices["train"], indices["validation"], indices["test"]
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(
                report["identity_index_storage"], "temporary_disk_backed_sqlite"
            )
            for indexed in indices.values():
                indexed.close()

    def test_duplicate_record_id_within_split_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = {
                "train": [
                    {"record_id": "same", "prompt": "A", "completion": "B"},
                    {"record_id": "same", "prompt": "C", "completion": "D"},
                ],
                "validation": [{"record_id": "v1", "prompt": "E", "completion": "F"}],
                "test": [{"record_id": "t1", "prompt": "G", "completion": "H"}],
            }
            indices = {}
            for split, records in rows.items():
                path = root / f"{split}.jsonl"
                path.write_text(
                    "".join(json.dumps(record) + "\n" for record in records),
                    encoding="utf-8",
                )
                indices[split] = IndexedJSONL(path)
            with self.assertRaisesRegex(ValueError, "Duplicate record_id"):
                validate_training_splits(
                    indices["train"], indices["validation"], indices["test"]
                )
            for indexed in indices.values():
                indexed.close()

    def test_large_scale_runner_uses_indexed_jsonl_data_loading(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/train_nextai.py").read_text(encoding="utf-8")
        self.assertIn("train_rows = IndexedJSONL", source)
        self.assertIn("Indexed JSONL byte offsets with on-demand record parsing", source)
        self.assertNotIn("train_rows = read_jsonl", source)


class MultimodalConversationCollatorTests(unittest.TestCase):
    def test_message_format_image_placeholders_receive_real_assets(self):
        row = {
            "messages": [
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text", "text": "Identify the CAD feature families."},
                    {"type": "image"},
                ]},
                {"role": "assistant", "content": "A pad and a pocket."},
            ],
            "images": ["view_0.jpg", "view_1.jpg"],
        }
        result = conversation_row_for_collator(
            row,
            image_loader=lambda path: "loaded:" + path,
        )
        content = result["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "image", "image": "loaded:view_0.jpg"})
        self.assertEqual(content[1]["text"], "Identify the CAD feature families.")
        self.assertEqual(content[2], {"type": "image", "image": "loaded:view_1.jpg"})

    def test_images_are_prepended_when_user_message_has_no_image_placeholders(self):
        row = {
            "messages": [
                {"role": "user", "content": "Describe this component."},
                {"role": "assistant", "content": "It is a bracket."},
            ],
            "images": ["front.jpg"],
        }
        result = conversation_row_for_collator(
            row,
            image_loader=lambda path: "loaded:" + path,
        )
        content = result["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "image", "image": "loaded:front.jpg"})
        self.assertEqual(content[1]["text"], "Describe this component.")

    def test_excess_image_placeholders_fail_closed(self):
        row = {
            "messages": [
                {"role": "user", "content": [{"type": "image"}, {"type": "image"}]},
                {"role": "assistant", "content": "Visual explanation."},
            ],
            "images": ["only-one.jpg"],
        }
        with self.assertRaisesRegex(ValueError, "more image placeholders"):
            conversation_row_for_collator(row, image_loader=lambda path: path)


class ProgressiveCurriculumScheduleTests(unittest.TestCase):
    def test_curriculum_orders_five_stages_with_spaced_rehearsal(self):
        rows = (
            [{"domain": "engineering_statics_beam_udl"} for _ in range(2)]
            + [{"domain": "cad_parametric_part"} for _ in range(2)]
            + [{"domain": "engineering_buildeng_reasoning"} for _ in range(2)]
            + [{"domain": "design_intake_residential"} for _ in range(2)]
            + [{"domain": "design_execution_residential"} for _ in range(2)]
        )
        order, manifest = build_progressive_curriculum_order(
            rows,
            seed=42,
            replay_fraction=0.5,
            replay_chunk_size=2,
        )
        self.assertEqual(manifest["stage_order"], [
            "foundations",
            "cad_bim_fluency",
            "engineering_disciplines",
            "operator_methods",
            "integrated_projects",
        ])
        self.assertEqual(manifest["unique_training_records"], 10)
        self.assertEqual(manifest["ordered_training_exposures"], 14)
        self.assertEqual(manifest["spaced_replay_exposures"], 4)
        self.assertEqual(len(set(order)), 10)
        self.assertEqual([manifest["stages"][stage]["unique_records"] for stage in manifest["stage_order"]], [2, 2, 2, 2, 2])
        # After each later stage's two new records, one sample from earlier
        # course material is interleaved before the next stage starts.
        self.assertTrue(all(index in {0, 1} for index in order[4:5]))
        self.assertTrue(any(index in {0, 1, 2, 3} for index in order[7:8]))
        self.assertTrue(any(index in set(range(6)) for index in order[10:11]))
        self.assertTrue(any(index in set(range(8)) for index in order[13:14]))

    def test_curriculum_order_is_deterministic_for_resume(self):
        rows = [
            {"domain": "engineering_statics_beam_udl"},
            {"domain": "cad_parametric_part"},
            {"domain": "engineering_buildeng_reasoning"},
            {"domain": "design_intake_residential"},
            {"domain": "design_execution_residential"},
        ]
        first, first_manifest = build_progressive_curriculum_order(rows, seed=17)
        second, second_manifest = build_progressive_curriculum_order(rows, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(
            first_manifest["ordered_index_sha256"],
            second_manifest["ordered_index_sha256"],
        )

    def test_domain_to_stage_mapping_is_explicit(self):
        self.assertEqual(
            curriculum_stage_for_record({"domain": "engineering_hydraulics_darcy_weisbach"}),
            "foundations",
        )
        self.assertEqual(
            curriculum_stage_for_record({"domain": "bim_native_command_workflow"}),
            "cad_bim_fluency",
        )
        self.assertEqual(
            curriculum_stage_for_record({"domain": "engineering_buildeng_reasoning"}),
            "engineering_disciplines",
        )
        self.assertEqual(
            curriculum_stage_for_record({"domain": "engineering_skill_knowledge"}),
            "operator_methods",
        )
        self.assertEqual(
            curriculum_stage_for_record({"domain": "nextcad_native"}),
            "integrated_projects",
        )



    def test_trainer_uses_sequential_sampler_for_curriculum_order(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/train_nextai.py").read_text(encoding="utf-8")
        self.assertIn('train_sampling_strategy="sequential"', source)
        self.assertIn("shuffle_dataset=False", source)
        self.assertIn(
            "train_dataset=ConversationDataset(train_rows, indices=training_indices)",
            source,
        )

    def test_gpu_runner_forwards_and_publishes_curriculum_manifest(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/run_large_scale_training.py").read_text(encoding="utf-8")
        self.assertIn('"--curriculum-replay-fraction"', source)
        self.assertIn('"--curriculum-replay-chunk-size"', source)
        self.assertIn('"curriculum_schedule.json"', source)



    def test_checkpoint_resume_requires_identical_data_and_curriculum(self):
        previous = {
            "base_model": "Qwen/Qwen3.5-0.8B",
            "max_steps": -1,
            "num_train_epochs": 1.0,
            "max_seq_length": 4096,
            "batch_size": 1,
            "gradient_accumulation": 8,
            "learning_rate": 1.0e-4,
            "lora_rank": 16,
            "precision": "bf16",
            "seed": 3407,
            "train_sampling_strategy": "sequential",
            "curriculum_schedule": {
                "stage_order": ["foundations", "cad_bim_fluency"],
                "training_records_sha256": "train-data",
                "ordered_index_sha256": "order",
                "replay_fraction_per_chunk": 0.1,
                "replay_chunk_size": 32,
                "seed": 3407,
            },
            "data_integrity": {
                "splits": {
                    "train": {"records_sha256": "train-data"},
                    "validation": {"records_sha256": "validation-data"},
                    "test": {"records_sha256": "test-data"},
                }
            },
        }
        validate_resume_compatibility(previous, previous)

        changed = json.loads(json.dumps(previous))
        changed["data_integrity"]["splits"]["test"]["records_sha256"] = "new-test-data"
        with self.assertRaisesRegex(ValueError, "Checkpoint resume refused"):
            validate_resume_compatibility(previous, changed)

    def test_checkpoint_resume_rejects_changed_curriculum_order(self):
        previous = {
            "base_model": "Qwen/Qwen3.5-0.8B",
            "max_steps": -1,
            "num_train_epochs": 1.0,
            "max_seq_length": 4096,
            "batch_size": 1,
            "gradient_accumulation": 8,
            "learning_rate": 1.0e-4,
            "lora_rank": 16,
            "precision": "bf16",
            "seed": 3407,
            "train_sampling_strategy": "sequential",
            "curriculum_schedule": {
                "stage_order": ["foundations", "cad_bim_fluency"],
                "training_records_sha256": "train-data",
                "ordered_index_sha256": "order",
                "replay_fraction_per_chunk": 0.1,
                "replay_chunk_size": 32,
                "seed": 3407,
            },
            "data_integrity": {
                "splits": {
                    "train": {"records_sha256": "train-data"},
                    "validation": {"records_sha256": "validation-data"},
                    "test": {"records_sha256": "test-data"},
                }
            },
        }
        changed = json.loads(json.dumps(previous))
        changed["curriculum_schedule"]["ordered_index_sha256"] = "different-order"
        with self.assertRaisesRegex(ValueError, "curriculum_schedule.ordered_index_sha256"):
            validate_resume_compatibility(previous, changed)

    def test_curriculum_rejects_invalid_replay_configuration(self):
        with self.assertRaises(ValueError):
            build_progressive_curriculum_order([], replay_fraction=0.8)
        with self.assertRaises(ValueError):
            build_progressive_curriculum_order([], replay_chunk_size=0)


if __name__ == "__main__":
    unittest.main()
