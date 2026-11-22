from __future__ import annotations
import importlib.util, os, tempfile, unittest
from pathlib import Path
MODULE_PATH = Path(__file__).resolve().parents[1] / "apps" / "Next3DLauncher" / "main.py"
spec = importlib.util.spec_from_file_location("next3d_launcher", MODULE_PATH)
launcher = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(launcher)

class RuntimeDiscoveryTests(unittest.TestCase):
    def test_unknown_app_is_rejected(self):
        with self.assertRaises(ValueError):
            launcher._candidate_paths("other")

    def test_env_override_is_first_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            candidate = Path(d) / ("custom-nextcad.exe" if os.name == "nt" else "custom-nextcad")
            candidate.write_text("test executable")
            if os.name != "nt":
                candidate.chmod(0o755)
            old = os.environ.get("NEXTCAD_EXECUTABLE")
            try:
                os.environ["NEXTCAD_EXECUTABLE"] = str(candidate)
                self.assertEqual(launcher._candidate_paths("nextcad")[0], candidate)
                self.assertEqual(launcher.find_runtime("nextcad"), candidate.resolve())
            finally:
                if old is None: os.environ.pop("NEXTCAD_EXECUTABLE", None)
                else: os.environ["NEXTCAD_EXECUTABLE"] = old


    def test_nextbim_env_override_is_first_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            candidate = Path(d) / ("custom-nextbim.exe" if os.name == "nt" else "custom-nextbim")
            candidate.write_text("test executable")
            if os.name != "nt":
                candidate.chmod(0o755)
            old = os.environ.get("NEXTBIM_EXECUTABLE")
            try:
                os.environ["NEXTBIM_EXECUTABLE"] = str(candidate)
                self.assertEqual(launcher._candidate_paths("nextbim")[0], candidate)
                self.assertEqual(launcher.find_runtime("nextbim"), candidate.resolve())
            finally:
                if old is None: os.environ.pop("NEXTBIM_EXECUTABLE", None)
                else: os.environ["NEXTBIM_EXECUTABLE"] = old


    def test_native_build_paths_are_discoverable_from_submodules(self):
        cad = launcher._candidate_paths("nextcad")
        bim = launcher._candidate_paths("nextbim")
        self.assertIn(launcher.APP_ROOT / "upstream" / "FreeCAD" / "build" / "relWithDebInfo" / "bin" / "FreeCAD", cad)
        self.assertIn(launcher.APP_ROOT / "upstream" / "BIMCraft" / "target" / "release" / "bimcraft", bim)

    def test_nextcad_does_not_pass_a_missing_startup_macro(self):
        command, environment = launcher.build_launch_configuration("nextcad", Path("FreeCAD"), [])
        self.assertEqual(command, ["FreeCAD"])
        self.assertIn("NEXT3D_HOME", environment)

    def test_nextbim_disables_upstream_self_update(self):
        command, environment = launcher.build_launch_configuration("nextbim", Path("bimcraft"), [])
        self.assertEqual(command, ["bimcraft"])
        self.assertEqual(environment.get("BIMCRAFT_NO_UPDATE_CHECK"), "1")

    def test_missing_runtimes_are_reported_missing(self):
        old_cad = os.environ.pop("NEXTCAD_EXECUTABLE", None)
        old_bim = os.environ.pop("NEXTBIM_EXECUTABLE", None)
        try:
            self.assertIsNone(launcher.find_runtime("nextcad"))
            self.assertIsNone(launcher.find_runtime("nextbim"))
        finally:
            if old_cad is not None: os.environ["NEXTCAD_EXECUTABLE"] = old_cad
            if old_bim is not None: os.environ["NEXTBIM_EXECUTABLE"] = old_bim

if __name__ == "__main__":
    unittest.main(verbosity=2)
