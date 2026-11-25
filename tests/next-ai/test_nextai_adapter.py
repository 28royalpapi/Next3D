from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters/nextcad-ai/NextAI"
sys.path.insert(0, str(ADAPTER))

from next_ai import freecad_tools, knowledge, provider, tool_registry


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

    def test_local_runtime_requires_multimodal_ollama_version(self):
        from unittest.mock import patch
        with patch.object(provider, "_local_get", return_value={"version": "0.40.10"}):
            status = provider.runtime_status()
        self.assertFalse(status["ready"])
        self.assertIn("0.40.11", status["message"])

    def test_local_runtime_checks_selected_model_installation(self):
        from unittest.mock import patch
        with patch.object(provider, "_local_get", side_effect=[
            {"version": "0.40.11"},
            {"models": [{"name": provider.DEFAULT_MODEL}]},
        ]):
            status = provider.runtime_status()
        self.assertTrue(status["ready"])
        self.assertEqual(status["model"], provider.DEFAULT_MODEL)

    def test_multimodal_payload_preserves_local_image(self):
        image_uri = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Read this drawing."},
                {"type": "image_url", "image_url": {"url": image_uri}},
            ],
        }]
        payload = provider.build_payload(messages)
        self.assertEqual(payload["model"], provider.DEFAULT_MODEL)
        self.assertEqual(payload["messages"][0]["content"][1]["image_url"]["url"], image_uri)

    def test_multimodal_payload_rejects_remote_image_urls(self):
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "https://example.com/drawing.png"}}
            ],
        }]
        with self.assertRaises(provider.ProviderError):
            provider.build_payload(messages)


class NativeToolSafetyTests(unittest.TestCase):

    def test_selected_shared_model_identifier(self):
        self.assertEqual(
            provider.DEFAULT_MODEL,
            "hf.co/turintech/Qwen3.5-0.8B-Artemis-GGUF:Q4_K_M",
        )

    def test_model_manifest_requires_vision_and_records_size_gate(self):
        manifest = json.loads((ROOT / "models/nextai/model.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["base_model"], "Qwen/Qwen3.5-0.8B")
        self.assertEqual(manifest["quantization"], "Q4_K_M")
        self.assertTrue(manifest["vision"]["enabled"])
        self.assertTrue(manifest["vision"]["supports_image_input"])
        self.assertEqual(manifest["minimum_ollama_version_for_vision"], "0.40.11")
        self.assertEqual(manifest["runtime_validation"], "pending")
        self.assertEqual(manifest["release_size_validation"], "pending")

    def test_offline_native_manual_retrieval(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "Draft" / "docs"
            docs.mkdir(parents=True)
            (docs / "walls.md").write_text(
                "# Draft walls\n\nCreate a parametric wall from a Draft wire "
                "using the Arch workbench.\n",
                encoding="utf-8",
            )
            result = knowledge.search("Draft Arch parametric wall", root)
            self.assertTrue(result)
            self.assertIn("walls.md", result[0]["source"])
            self.assertIn("parametric wall", result[0]["excerpt"])

    def test_bundled_engineering_skill_pack_is_retrievable(self):
        result = knowledge.search("parametric sketch constraints feature tree")
        self.assertTrue(result)
        self.assertTrue(any(item["source"].startswith("nextai/") for item in result))

    def test_guided_design_intake_knowledge_is_retrievable_for_architecture_and_bim(self):
        architecture = knowledge.search(
            "three bedroom bungalow master bedrooms toilets ensuites shared store plot dimensions"
        )
        self.assertTrue(any(item["source"].endswith("design/design-intake.md") for item in architecture))
        bim = knowledge.search(
            "BIM project coordinate reference IFC schema LOD asset information requirements"
        )
        self.assertTrue(any(item["source"].endswith("design/design-intake.md") for item in bim))

    def test_nextcad_runtime_prompt_requires_context_aware_design_clarification(self):
        ui_source = (ROOT / "adapters/nextcad-ai/NextAI/next_ai/ui.py").read_text(encoding="utf-8")
        self.assertIn("DESIGN INTAKE BEFORE MODELLING", ui_source)
        self.assertIn("number of master bedrooms", ui_source)
        self.assertIn("Ask only for unresolved or conflicting requirements", ui_source)
        self.assertIn("return an empty plan", ui_source)

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
        self.assertIn("create_draft_wire", names)
        self.assertIn("create_draft_dimension", names)
        self.assertIn("create_arch_structure", names)

    def test_write_tools_are_typed_and_approval_gated(self):
        for tool in tool_registry.TOOLS:
            self.assertIn("parameters", tool)
            self.assertIn("read_only", tool)
        self.assertTrue(any(not item["read_only"] for item in tool_registry.TOOLS))

    def test_native_partdesign_tool_contract(self):
        tools = {item["name"]: item for item in tool_registry.TOOLS}
        expected = {
            "create_partdesign_body",
            "create_partdesign_sketch",
            "add_sketch_line",
            "add_sketch_circle",
            "add_sketch_polygon",
            "create_partdesign_pad",
            "create_partdesign_pocket",
            "create_parametric_variables",
            "bind_parametric_expression",
        }
        self.assertTrue(expected.issubset(tools))
        for name in expected:
            self.assertFalse(tools[name]["read_only"])
            self.assertEqual(tools[name]["parameters"]["type"], "object")
            self.assertFalse(tools[name]["parameters"]["additionalProperties"])
        self.assertIn("length", tools["create_partdesign_pad"]["parameters"]["required"])
        self.assertIn("sketch_name", tools["create_partdesign_pocket"]["parameters"]["required"])
        self.assertIn("variables", tools["create_parametric_variables"]["parameters"]["required"])
        self.assertIn("expression", tools["bind_parametric_expression"]["parameters"]["required"])

    def test_sketch_point_pinning_uses_native_dimensions(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        calls = []
        sketch = SimpleNamespace(addConstraint=lambda constraint: calls.append(constraint))
        fake_sketcher = SimpleNamespace(Constraint=lambda *args: args)
        with patch.dict(sys.modules, {"Sketcher": fake_sketcher}):
            freecad_tools._pin_sketch_point(sketch, 4, 1, 0.0, 0.0)
            self.assertEqual(calls[-1], ("Coincident", 4, 1, -1, 1))

            calls.clear()
            freecad_tools._pin_sketch_point(sketch, 5, 2, 0.0, 120.0)
            self.assertEqual(calls[0], ("PointOnObject", 5, 2, -2))
            self.assertEqual(calls[1], ("DistanceY", -1, 1, 5, 2, 120.0))

            calls.clear()
            freecad_tools._pin_sketch_point(sketch, 6, 1, 300.0, 0.0)
            self.assertEqual(calls[0], ("DistanceX", -1, 1, 6, 1, 300.0))
            self.assertEqual(calls[1], ("PointOnObject", 6, 1, -1))

            calls.clear()
            freecad_tools._pin_sketch_point(sketch, 7, 1, 300.0, 120.0)
            self.assertEqual(calls[0], ("DistanceX", -1, 1, 7, 1, 300.0))
            self.assertEqual(calls[1], ("DistanceY", -1, 1, 7, 1, 120.0))

    def test_parametric_variable_creation_uses_unit_aware_native_types(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeVarSet:
            def __init__(self, name):
                object.__setattr__(self, "Name", name)
                object.__setattr__(self, "TypeId", "App::VarSet")
                object.__setattr__(self, "PropertiesList", [])
                object.__setattr__(self, "_types", {})
                object.__setattr__(self, "_groups", {})
                object.__setattr__(self, "_values", {})
            def addProperty(self, property_type, name, group, description):
                self.PropertiesList.append(name)
                self._types[name] = property_type
                self._groups[name] = group
            def getGroupOfProperty(self, name):
                return self._groups.get(name, "Base")
            def getTypeIdOfProperty(self, name):
                return self._types[name]
            def __setattr__(self, name, value):
                if name in {"Name", "TypeId", "PropertiesList", "_types", "_groups", "_values"}:
                    object.__setattr__(self, name, value)
                else:
                    self._values[name] = value
            def __getattr__(self, name):
                if name in self._values:
                    return self._values[name]
                raise AttributeError(name)

        class FakeDoc:
            def __init__(self):
                self.objects = {}
                self.recompute_count = 0
            def getObject(self, name):
                return self.objects.get(name)
            def addObject(self, type_id, name):
                obj = FakeVarSet(name)
                self.objects[name] = obj
                return obj
            def recompute(self):
                self.recompute_count += 1

        doc = FakeDoc()
        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), None)):
            result = freecad_tools._partdesign_step(doc, "create_parametric_variables", {
                "name": "Vars",
                "variables": [
                    {"name": "OverallLength", "value": 6000, "type": "App::PropertyLength"},
                    {"name": "StoreyCount", "value": 2, "type": "App::PropertyInteger"},
                    {"name": "UseBasement", "value": False, "type": "App::PropertyBool"},
                ],
            })
        self.assertEqual(result["expression_paths"]["OverallLength"], "Vars.OverallLength")
        self.assertEqual(doc.objects["Vars"].OverallLength, 6000.0)
        self.assertEqual(doc.objects["Vars"].StoreyCount, 2)
        self.assertFalse(doc.objects["Vars"].UseBasement)
        self.assertGreaterEqual(doc.recompute_count, 2)

    def test_parametric_variable_rejects_unapproved_property_types(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeDoc:
            def getObject(self, name):
                return None
            def addObject(self, type_id, name):
                return SimpleNamespace(Name=name, TypeId=type_id)
            def recompute(self):
                pass

        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), None)):
            with self.assertRaises(ValueError):
                freecad_tools._partdesign_step(FakeDoc(), "create_parametric_variables", {
                    "variables": [{"name": "Bad", "value": 1, "type": "App::PropertyPythonObject"}]
                })

    def test_parametric_expression_checks_before_binding(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeObject:
            Name = "Pad"
            TypeId = "PartDesign::Pad"
            PropertiesList = ["Length"]
            State = []
            Constraints = []
            def __init__(self):
                self.bound = None
            def evalExpression(self, expression):
                if expression == "Vars.Width":
                    return 4000.0
                raise ValueError("unknown variable")
            def setExpression(self, target, expression):
                self.bound = (target, expression)

        class FakeDoc:
            def __init__(self, obj):
                self.obj = obj
            def getObject(self, name):
                return self.obj if name == "Pad" else None
            def recompute(self):
                pass

        obj = FakeObject()
        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), None)):
            result = freecad_tools._partdesign_step(FakeDoc(obj), "bind_parametric_expression", {
                "object_name": "Pad",
                "property_name": "Length",
                "expression": "Vars.Width",
            })
            self.assertEqual(result["evaluated_value"], "4000.0")
            self.assertEqual(obj.bound, ("Length", "Vars.Width"))

            obj.bound = None
            with self.assertRaises(ValueError):
                freecad_tools._partdesign_step(FakeDoc(obj), "bind_parametric_expression", {
                    "object_name": "Pad",
                    "property_name": "Length",
                    "expression": "Vars.Missing",
                })
            self.assertIsNone(obj.bound)


if __name__ == "__main__":
    unittest.main()
