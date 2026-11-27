#!/usr/bin/env python3
"""Regression tests for native runner invocation from upstream submodule directories."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run_nextbim_ai_acceptance.py"


class NativeRunnerImportContextTests(unittest.TestCase):
    def test_nextbim_runner_imports_training_package_from_foreign_working_directory(self):
        # The native workflow invokes the script while cwd is upstream/BIMCraft.
        # This reproduces that execution context without needing a compiled BIMCraft binary.
        with tempfile.TemporaryDirectory(prefix="nextbim-runner-cwd-") as cwd:
            result = subprocess.run(
                [sys.executable, str(RUNNER), "--help"],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--output-dir", result.stdout)


if __name__ == "__main__":
    unittest.main()
