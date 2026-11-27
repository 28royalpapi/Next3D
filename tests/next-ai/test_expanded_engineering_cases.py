import importlib.util
import math
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/generate_verified_engineering_cases.py"
SPEC = importlib.util.spec_from_file_location("nextai_expanded_analytic_cases", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExpandedEngineeringCaseTests(unittest.TestCase):
    def test_euler_column_buckling_uses_effective_length_and_consistent_units(self):
        inputs = {
            "unsupported_length_m": 3.0,
            "effective_length_factor": 1.0,
            "elastic_modulus_GPa": 200.0,
            "second_moment_mm4": 8.0e7,
            "area_mm2": 5000.0,
        }
        result = MODULE.solve_euler_column_buckling(inputs)
        expected_load = math.pi**2 * 200000.0 * 8.0e7 / 3000.0**2 / 1000.0
        self.assertAlmostEqual(result["values"]["Euler_critical_load_kN"], expected_load, places=5)
        self.assertAlmostEqual(result["values"]["slenderness_ratio"], 3000.0 / math.sqrt(8.0e7 / 5000.0), places=6)
        self.assertEqual(result["units"]["Euler_critical_load_kN"], "kN")

    def test_rankine_pressure_sums_triangular_soil_and_rectangular_surcharge(self):
        result = MODULE.solve_rankine_active_pressure({
            "soil_unit_weight_kN_m3": 18.0,
            "retained_height_m": 6.0,
            "uniform_surcharge_kPa": 10.0,
            "friction_angle_deg": 30.0,
        })
        self.assertAlmostEqual(result["values"]["active_pressure_coefficient_Ka"], 1.0 / 3.0, places=7)
        self.assertAlmostEqual(result["values"]["soil_pressure_resultant_kN_per_m"], 108.0, places=5)
        self.assertAlmostEqual(result["values"]["surcharge_pressure_resultant_kN_per_m"], 20.0, places=5)
        self.assertAlmostEqual(result["values"]["total_active_resultant_kN_per_m"], 128.0, places=5)
        self.assertAlmostEqual(result["values"]["resultant_height_above_base_m"], 2.15625, places=5)

    def test_hydrostatic_gate_force_and_centre_of_pressure(self):
        result = MODULE.solve_hydrostatic_vertical_gate({
            "gate_width_m": 2.0,
            "gate_height_m": 3.0,
            "gate_top_depth_below_free_surface_m": 1.5,
            "water_unit_weight_kN_m3": 9.81,
        })
        self.assertAlmostEqual(result["values"]["hydrostatic_resultant_kN"], 176.58, places=5)
        self.assertAlmostEqual(result["values"]["centre_of_pressure_depth_below_free_surface_m"], 3.25, places=6)
        self.assertAlmostEqual(result["values"]["centre_of_pressure_below_gate_top_m"], 1.75, places=6)

    def test_terzaghi_strip_footing_reports_gross_and_net_allowable_pressure(self):
        result = MODULE.solve_terzaghi_strip_footing({
            "effective_cohesion_kPa": 10.0,
            "surcharge_at_foundation_level_kPa": 20.0,
            "effective_soil_unit_weight_kN_m3": 18.0,
            "footing_width_m": 2.0,
            "bearing_factor_Nc": 37.2,
            "bearing_factor_Nq": 22.5,
            "bearing_factor_Ngamma": 19.7,
            "factor_of_safety": 3.0,
        })
        self.assertAlmostEqual(result["values"]["gross_ultimate_bearing_pressure_kPa"], 1176.6, places=5)
        self.assertAlmostEqual(result["values"]["net_allowable_bearing_pressure_kPa"], (1176.6 - 20.0) / 3.0, places=5)
        self.assertAlmostEqual(result["values"]["gross_allowable_bearing_pressure_kPa"], 20.0 + (1176.6 - 20.0) / 3.0, places=5)

    def test_infinite_slope_checks_effective_stress_and_shear_equilibrium(self):
        inputs = {
            "effective_cohesion_kPa": 5.0,
            "soil_unit_weight_kN_m3": 18.0,
            "normal_soil_thickness_m": 2.0,
            "pore_water_pressure_kPa": 5.0,
            "slope_angle_deg": 30.0,
            "effective_friction_angle_deg": 25.0,
        }
        result = MODULE.solve_infinite_slope_factor_of_safety(inputs)
        beta = math.radians(30.0)
        expected_normal = 18.0 * 2.0 * math.cos(beta)**2
        expected_driving = 18.0 * 2.0 * math.sin(beta) * math.cos(beta)
        expected_strength = 5.0 + (expected_normal - 5.0) * math.tan(math.radians(25.0))
        self.assertAlmostEqual(result["values"]["effective_normal_stress_kPa"], expected_normal - 5.0, places=6)
        self.assertAlmostEqual(result["values"]["factor_of_safety"], expected_strength / expected_driving, places=6)


    def test_new_family_domains_are_included_in_progressive_training_stages(self):
        trainer_path = Path(__file__).resolve().parents[2] / "training/nextai/train_nextai.py"
        trainer_spec = importlib.util.spec_from_file_location("nextai_training_curriculum", trainer_path)
        trainer = importlib.util.module_from_spec(trainer_spec)
        trainer_spec.loader.exec_module(trainer)
        expected_stages = {
            "engineering_structural_euler_column_buckling": "foundations",
            "engineering_geotechnical_rankine_active_pressure": "foundations",
            "engineering_hydraulics_hydrostatic_gate": "foundations",
            "engineering_geotechnical_terzaghi_strip_footing": "foundations",
            "engineering_geotechnical_infinite_slope": "foundations",
            "engineering_hydraulics_rational_method_runoff": "foundations",
            "engineering_hydraulics_water_pump_power": "foundations",
            "engineering_geotechnical_elastic_foundation_settlement": "foundations",
        }
        for domain, expected_stage in expected_stages.items():
            with self.subTest(domain=domain):
                self.assertEqual(
                    trainer.curriculum_stage_for_record({"domain": domain}),
                    expected_stage,
                )

    def test_all_new_family_solvers_return_consistent_output_contracts(self):
        cases = (
            (MODULE.solve_euler_column_buckling, {"unsupported_length_m": 3, "effective_length_factor": 1, "elastic_modulus_GPa": 200, "second_moment_mm4": 8e7, "area_mm2": 5000}),
            (MODULE.solve_rankine_active_pressure, {"soil_unit_weight_kN_m3": 18, "retained_height_m": 6, "uniform_surcharge_kPa": 10, "friction_angle_deg": 30}),
            (MODULE.solve_hydrostatic_vertical_gate, {"gate_width_m": 2, "gate_height_m": 3, "gate_top_depth_below_free_surface_m": 1.5}),
            (MODULE.solve_terzaghi_strip_footing, {"effective_cohesion_kPa": 10, "surcharge_at_foundation_level_kPa": 20, "effective_soil_unit_weight_kN_m3": 18, "footing_width_m": 2, "bearing_factor_Nc": 37.2, "bearing_factor_Nq": 22.5, "bearing_factor_Ngamma": 19.7, "factor_of_safety": 3}),
            (MODULE.solve_infinite_slope_factor_of_safety, {"effective_cohesion_kPa": 5, "soil_unit_weight_kN_m3": 18, "normal_soil_thickness_m": 2, "pore_water_pressure_kPa": 5, "slope_angle_deg": 30, "effective_friction_angle_deg": 25}),
            (MODULE.solve_rational_method_runoff, {"runoff_coefficient": 0.6, "rainfall_intensity_mm_hr": 50, "catchment_area_ha": 10}),
            (MODULE.solve_water_pump_power, {"flow_rate_L_per_s": 10, "total_dynamic_head_m": 20, "pump_efficiency": 0.7, "motor_efficiency": 0.9}),
            (MODULE.solve_elastic_shallow_foundation_settlement, {"net_contact_pressure_kPa": 150, "footing_width_m": 2, "poisson_ratio": 0.3, "soil_elastic_modulus_MPa": 20, "settlement_influence_factor": 1}),
        )
        for solver, inputs in cases:
            with self.subTest(solver=solver.__name__):
                result = solver(inputs)
                self.assertEqual(set(result), {"values", "units", "steps"})
                self.assertTrue(result["values"])
                self.assertEqual(set(result["values"]), set(result["units"]))
                self.assertTrue(result["steps"])

    def test_new_solvers_reject_invalid_physical_inputs(self):
        invalid_cases = (
            (MODULE.solve_euler_column_buckling, {"unsupported_length_m": 0, "effective_length_factor": 1, "elastic_modulus_GPa": 200, "second_moment_mm4": 8e7, "area_mm2": 5000}),
            (MODULE.solve_rankine_active_pressure, {"soil_unit_weight_kN_m3": 18, "retained_height_m": 5, "uniform_surcharge_kPa": 0, "friction_angle_deg": 0}),
            (MODULE.solve_hydrostatic_vertical_gate, {"gate_width_m": 2, "gate_height_m": 0, "gate_top_depth_below_free_surface_m": 1}),
            (MODULE.solve_terzaghi_strip_footing, {"effective_cohesion_kPa": 0, "surcharge_at_foundation_level_kPa": 0, "effective_soil_unit_weight_kN_m3": 18, "footing_width_m": 2, "bearing_factor_Nc": 0, "bearing_factor_Nq": 20, "bearing_factor_Ngamma": 20, "factor_of_safety": 3}),
            (MODULE.solve_infinite_slope_factor_of_safety, {"effective_cohesion_kPa": 0, "soil_unit_weight_kN_m3": 18, "normal_soil_thickness_m": 2, "pore_water_pressure_kPa": 999, "slope_angle_deg": 30, "effective_friction_angle_deg": 25}),
            (MODULE.solve_rational_method_runoff, {"runoff_coefficient": 1.2, "rainfall_intensity_mm_hr": 50, "catchment_area_ha": 10}),
            (MODULE.solve_water_pump_power, {"flow_rate_L_per_s": 10, "total_dynamic_head_m": 20, "pump_efficiency": 0, "motor_efficiency": 0.9}),
            (MODULE.solve_elastic_shallow_foundation_settlement, {"net_contact_pressure_kPa": 150, "footing_width_m": 2, "poisson_ratio": 0.5, "soil_elastic_modulus_MPa": 20, "settlement_influence_factor": 1}),
        )
        for solver, inputs in invalid_cases:
            with self.subTest(solver=solver.__name__):
                with self.assertRaises(ValueError):
                    solver(inputs)


    def test_rational_method_converts_mm_per_hour_and_hectares_before_multiplication(self):
        result = MODULE.solve_rational_method_runoff({
            "runoff_coefficient": 0.6,
            "rainfall_intensity_mm_hr": 50.0,
            "catchment_area_ha": 10.0,
        })
        self.assertAlmostEqual(result["values"]["peak_runoff_m3_per_s"], 0.83333333, places=7)
        self.assertAlmostEqual(result["values"]["peak_runoff_L_per_s"], 833.333333, places=5)

    def test_pump_power_propagates_pump_and_motor_efficiencies(self):
        result = MODULE.solve_water_pump_power({
            "flow_rate_L_per_s": 10.0,
            "total_dynamic_head_m": 20.0,
            "pump_efficiency": 0.7,
            "motor_efficiency": 0.9,
        })
        hydraulic = 1000.0 * 9.80665 * 0.01 * 20.0 / 1000.0
        self.assertAlmostEqual(result["values"]["hydraulic_power_kW"], hydraulic, places=6)
        self.assertAlmostEqual(result["values"]["pump_shaft_power_kW"], hydraulic / 0.7, places=6)
        self.assertAlmostEqual(result["values"]["electrical_input_power_kW"], hydraulic / (0.7 * 0.9), places=6)

    def test_elastic_foundation_settlement_converts_modulus_and_reports_mm(self):
        result = MODULE.solve_elastic_shallow_foundation_settlement({
            "net_contact_pressure_kPa": 150.0,
            "footing_width_m": 2.0,
            "poisson_ratio": 0.3,
            "soil_elastic_modulus_MPa": 20.0,
            "settlement_influence_factor": 1.0,
        })
        self.assertAlmostEqual(result["values"]["soil_elastic_modulus_kPa"], 20000.0, places=6)
        self.assertAlmostEqual(result["values"]["elastic_settlement_mm"], 13.65, places=6)

    def test_new_families_join_deterministic_l0_corpus_generation(self):
        splits, manifest = MODULE.generate_cases(cases_per_domain=3, seed=20261127)
        self.assertEqual(len(MODULE.FAMILY_BUILDERS), 25)
        self.assertEqual(manifest["total_records"], 75)
        rows = [row for split_rows in splits.values() for row in split_rows]
        self.assertEqual(len({row["record_id"] for row in rows}), 75)
        by_family = {}
        for row in rows:
            by_family[row["case_family"]] = by_family.get(row["case_family"], 0) + 1
            self.assertEqual(row["evidence_level"], "L0")
            self.assertEqual(row["calculation_validation"], "deterministic_closed_form_solver")
            expected = row["expected"]
            self.assertTrue(expected["calculation_steps"])
            self.assertTrue(expected["governing_equations"])
            self.assertTrue(expected["assumptions"])
            self.assertTrue(expected["limitations"])
        self.assertEqual(len(by_family), 25)
        self.assertTrue(all(count == 3 for count in by_family.values()))


if __name__ == "__main__":
    unittest.main()
