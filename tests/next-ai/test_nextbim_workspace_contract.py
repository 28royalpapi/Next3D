from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "verify-source-patches.py"
WORKSPACE_PATCHER = ROOT / "scripts" / "apply-nextbim-assistant-workspace.py"


class NextBIMWorkspaceContractTests(unittest.TestCase):
    def test_source_verifier_preserves_the_upstream_default_workspace(self):
        source = VERIFIER.read_text(encoding="utf-8")

        self.assertIn(
            "right: vec![Stack::of(Palette::Properties), Stack::of(Palette::Browser)]",
            source,
        )
        self.assertIn("!closed.contains(&p) && p != Palette::Assistant", source)
        self.assertNotIn(
            'Stack { tabs: vec![Palette::Browser, Palette::Assistant], active: 1 }',
            source,
        )
        self.assertNotIn(
            "Next AI workspace is not visible beside the project browser by default",
            source,
        )

    def test_next_ai_branding_does_not_force_the_assistant_open(self):
        source = WORKSPACE_PATCHER.read_text(encoding="utf-8")

        self.assertIn('Palette::Assistant => msg!("Next AI")', source)
        self.assertIn('if name == "Assistant"', source)
        self.assertNotIn("right: vec!", source)
        self.assertNotIn("Target::Side", source)


if __name__ == "__main__":
    unittest.main()
