from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters/nextcad-ai/NextAI"
sys.path.insert(0, str(ADAPTER))

from next_ai import freecad_tools, provider, tool_registry


class ProviderBoundaryTests(unittest.TestCase):
    def test_endpoint_is_fixed_loopback(self):
        self.assertEqual(
            provider._validated_endpoint(),
            "http://127.0.0.1:11434/v1/chat/completions",
        )

    def test_remote_endpoint_is_rejected(self):
        for endpoint in (
            "https://example.com/v1/chat/completions",
            "http://localhost:8080/v1/chat/completions",
            "http://192.168.1.10:8080/v1/chat/completions",
            "http://127.0.0.1:8080/v1/chat/completions",
            "http://127.0.0.1:11434/redirect",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(provider.ProviderError):
                    provider._validated_endpoint(endpoint)

    def test_proxy_environment_is_not_used(self):
        import inspect
        source = inspect.getsource(provider.chat)
        self.assertIn("ProxyHandler({})", source)
        self.assertIn("_NoRedirect()", source)


class NativeToolSafetyTests(unittest.TestCase):
    def test_coordinate_validation(self):
        self.assertEqual(freecad_tools._point([10, 20]), [10.0, 20.0, 0.0])
        with self.assertRaises(ValueError):
            freecad_tools._point([float("nan"), 0])

    def test_tool_registry_has_no_arbitrary_code_execution(self):
        names = {tool["name"] for tool in tool_registry.TOOLS}
        self.assertNotIn("execute_code", names)
        self.assertNotIn("run_python", names)
        self.assertIn("create_draft_line", names)
        self.assertIn("create_arch_wall", names)

    def test_write_tools_are_typed_and_approval_gated(self):
        for tool in tool_registry.TOOLS:
            self.assertIn("parameters", tool)
            self.assertIn("read_only", tool)
        self.assertTrue(any(not item["read_only"] for item in tool_registry.TOOLS))


if __name__ == "__main__":
    unittest.main()
