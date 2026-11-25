import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_public_corpora.py"
spec = importlib.util.spec_from_file_location("prepare_public_corpora_calculations", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EngineeringCalculationCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = module.make_advanced_engineering_curriculum()
        cls.by_domain = {}
        for lesson in cls.lessons:
            cls.by_domain.setdefault(lesson["domain"], []).append(lesson)

    def test_beam_reactions_satisfy_force_and_moment_equilibrium(self):
        lesson = self.by_domain["engineering_beam_reactions_calculation"][0]
        data = lesson["completion"]
        self.assertEqual(data["answer"]["left_reaction_kn"], 15.0)
        self.assertEqual(data["answer"]["right_reaction_kn"], 12.0)
        self.assertAlmostEqual(data["answer"]["vertical_force_check_kn"], 0.0, places=9)
        self.assertAlmostEqual(data["answer"]["left_support_moment_check_kn_m"], 0.0, places=9)

    def test_axial_bar_fem_keeps_units_and_boundary_condition(self):
        data = self.by_domain["engineering_fem_axial_bar_calculation"][0]["completion"]
        self.assertEqual(data["element_stiffness_n_per_m"], 30_000_000.0)
        self.assertEqual(data["answer"]["node_2_displacement_mm"], 0.5)
        self.assertEqual(data["answer"]["support_reaction_kn"], -15.0)
        self.assertEqual(data["element_matrix_n_per_m"][0][1], -30_000_000.0)

    def test_pipe_velocity_satisfies_continuity(self):
        data = self.by_domain["engineering_pipe_continuity_calculation"][0]["completion"]
        self.assertAlmostEqual(data["answer"]["mean_velocity_m_s"], 1.27324, places=5)
        self.assertAlmostEqual(data["answer"]["continuity_check_m3_s"], 0.01, places=8)

    def test_concrete_quantity_uses_only_stated_geometry(self):
        data = self.by_domain["construction_concrete_quantity_calculation"][0]["completion"]
        self.assertEqual(data["answer"]["net_concrete_volume_m3"], 3.0)
        self.assertEqual(data["answer"]["plan_area_m2"], 20.0)
        self.assertIn("No waste or overbreak allowance", data["exclusions"])

    def test_worked_calculation_examples_are_varied_and_have_explicit_limits(self):
        expected = {
            "engineering_beam_reactions_calculation",
            "engineering_fem_axial_bar_calculation",
            "engineering_pipe_continuity_calculation",
            "construction_concrete_quantity_calculation",
        }
        self.assertTrue(expected.issubset(self.by_domain))
        for domain in expected:
            rows = self.by_domain[domain]
            self.assertEqual(len(rows), 12)
            self.assertGreater(len({row["prompt"] for row in rows}), 1)
            for row in rows:
                self.assertIn("limits", row["completion"]) if domain != "construction_concrete_quantity_calculation" else self.assertIn("exclusions", row["completion"])
                self.assertTrue(row["prompt"].strip())


if __name__ == "__main__":
    unittest.main()
