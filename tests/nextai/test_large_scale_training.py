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
from training.nextai.run_large_scale_training import compare_heldout_evaluations
from training.nextai.train_nextai import IndexedJSONL, validate_training_splits


class FakeTokenizer:
    name_or_path = "fake-test-tokenizer"

    def encode(self, text, add_special_tokens=False):
        return text.split()


class LargeScaleTrainingTests(unittest.TestCase):
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
            image = root / "small.jpg"
            image.write_bytes(b"fake-image-bytes")
            rows = {
                "train": [
                    {"record_id": "train-1", "domain": "structural", "source": "authored",
                     "license": "project-authored", "prompt": "Calculate beam reaction",
                     "completion": "Reaction is 12 kN", "images": [str(image)]}
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
            self.assertGreater(report["train_text_tokens"], 0)
            self.assertEqual(report["image_files_total"], 1)
            self.assertEqual(report["missing_image_files"], [])

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
            report = audit_corpus(root, FakeTokenizer())
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
        self.assertIn("validation_by_domain = evaluate_by_domain(validation_rows", source)
        self.assertNotIn("evaluate_by_domain(test_rows", source)
        self.assertIn('"status": "PENDING_POST_TRAINING"', source)
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
                "metrics_by_domain": {
                    "structural": {"token_f1": 0.5, "plan_shape_valid": 0.7, "records": 20}
                },
            }), encoding="utf-8")
            candidate.write_text(json.dumps({
                "model": "candidate",
                "test_records": 20,
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

    def test_large_scale_runner_uses_indexed_jsonl_data_loading(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "training/nextai/train_nextai.py").read_text(encoding="utf-8")
        self.assertIn("train_rows = IndexedJSONL", source)
        self.assertIn("Indexed JSONL byte offsets with on-demand record parsing", source)
        self.assertNotIn("train_rows = read_jsonl", source)


if __name__ == "__main__":
    unittest.main()
