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
            wall_matches = [
                item for item in result
                if "walls.md" in item["source"] and "parametric wall" in item["excerpt"]
            ]
            self.assertTrue(wall_matches, result)

    def test_bundled_engineering_skill_pack_is_retrievable(self):
        result = knowledge.search("parametric sketch constraints feature tree")
        self.assertTrue(result)
        self.assertTrue(any(item["source"].startswith("nextai/") for item in result))

    def test_guided_design_intake_knowledge_is_retrievable_for_architecture_and_bim(self):
        architecture = knowledge.search(
            "bungalow storey house ensuite shared facilities guest WC plot frontage road access", limit=10
        )
        self.assertTrue(any(item["source"].endswith("design/design-intake.md") for item in architecture))
        bim = knowledge.search(
            "vertical datum employer information requirements IFC schema project coordinates", limit=10
        )
        self.assertTrue(any(item["source"].endswith("design/design-intake.md") for item in bim))
        cam = knowledge.search(
            "feeds speeds stepover machine workholding postprocessor G-code", limit=10
        )
        self.assertTrue(any(item["source"].endswith("design/design-intake.md") for item in cam))
        execution = knowledge.search(
            "native viewport recompute each operation editable parametric feature history "
            "watchtower member schedule inspect modify existing BIM element", limit=10
        )
        self.assertTrue(any(item["source"].endswith("design/design-execution.md") for item in execution))
        bim_native = knowledge.search(
            "BIMCraft list_commands execute inspect_model query_elements todo_write structural_column beam footing", limit=10
        )
        self.assertTrue(any(item["source"].endswith("bim/native-command-playbook.md") for item in bim_native))

    def test_nextcad_runtime_prompt_requires_context_aware_design_clarification(self):
        ui_source = (ROOT / "adapters/nextcad-ai/NextAI/next_ai/ui.py").read_text(encoding="utf-8")
        self.assertIn("DESIGN INTAKE BEFORE MODELLING", ui_source)
        self.assertIn("number of master bedrooms", ui_source)
        self.assertIn("Ask only for unresolved or conflicting requirements", ui_source)
        self.assertIn("return an empty plan", ui_source)
        self.assertIn("edit_native_property", ui_source)
        self.assertIn("show_native_progress", ui_source)
        self.assertIn("Finished: ", ui_source)
        self.assertIn("Part cylinders for shafts, pins, rollers", ui_source)
        self.assertIn("create_part_cylinder", ui_source)
        self.assertIn("create_part_sphere", ui_source)
        self.assertIn("create_part_cone", ui_source)
        self.assertIn("create_arch_wall", ui_source)
        self.assertIn("3D architectural wall shell", ui_source)
        self.assertIn("20-step native-plan limit", ui_source)
        self.assertIn("keep each component separate and labelled", ui_source.lower())

    def test_nextbim_installer_adds_guided_design_intake_to_native_assistant(self):
        installer = (ROOT / "scripts/install-nextbim-ai-knowledge.py").read_text(encoding="utf-8")
        for term in (
            "Before an under-specified design task",
            "master-bedroom counts",
            "ensuite/shared/guest split",
            "coordinate reference and datum",
            "Carry confirmed answers forward",
            "do not call modifying tools",
        ):
            self.assertIn(term, installer)
        compile(installer, "install-nextbim-ai-knowledge.py", "exec")

    def test_nextbim_installer_teaches_staged_model_creation_and_in_place_editing(self):
        installer = (ROOT / "scripts/install-nextbim-ai-knowledge.py").read_text(encoding="utf-8")
        for term in (
            "visible native stages",
            "filter list_commands",
            "update todo_write",
            "query_elements",
            "use modify on that same element",
            "duplicate or delete/recreate it",
            "visual member envelopes as concept placeholders",
        ):
            self.assertIn(term, installer)
        self.assertIn('pack_root.rglob("*.md")', installer)

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
        self.assertIn("create_part_cylinder", names)
        self.assertIn("create_part_sphere", names)
        self.assertIn("create_part_cone", names)

    def test_native_primitive_tools_have_explicit_geometry_schemas(self):
        tools = {item["name"]: item for item in tool_registry.TOOLS}
        self.assertEqual(set(tools["create_part_cylinder"]["parameters"]["required"]), {"radius", "height"})
        self.assertIn("axis", tools["create_part_cylinder"]["parameters"]["properties"])
        self.assertEqual(set(tools["create_part_sphere"]["parameters"]["required"]), {"radius"})
        self.assertEqual(set(tools["create_part_cone"]["parameters"]["required"]), {"radius1", "radius2", "height"})
        for name in ("create_part_cylinder", "create_part_sphere", "create_part_cone"):
            self.assertFalse(tools[name]["read_only"])
            self.assertFalse(tools[name]["parameters"]["additionalProperties"])

    def test_native_cylinder_creation_uses_supplied_axis_and_dimensions(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import math

        class Vector:
            def __init__(self, *values):
                self.values = values
                self.Length = math.sqrt(sum(value * value for value in values))

        class Rotation:
            def __init__(self, *values):
                self.values = values

        class Placement:
            def __init__(self, base, rotation):
                self.Base, self.Rotation = base, rotation

        class FakeObject:
            Name = "NextAICylinder"
            Label = "Cylinder"
            TypeId = "Part::Cylinder"

        class FakeDoc:
            def __init__(self):
                self.created = []
            def addObject(self, type_id, name):
                obj = FakeObject()
                obj.TypeId = type_id
                obj.Name = name
                self.created.append(obj)
                return obj

        app = SimpleNamespace(Vector=Vector, Rotation=Rotation, Placement=Placement)
        doc = FakeDoc()
        with patch.object(freecad_tools, "_apps", return_value=(app, None)):
            result = freecad_tools._create_step(doc, "create_part_cylinder", {
                "radius": 350, "height": 220, "origin": [700, -220, 350],
                "axis": [0, 1, 0], "label": "WH01 — wheel envelope"
            })
            self.assertEqual(result["type"], "Part::Cylinder")
            self.assertEqual(doc.created[0].Radius, 350.0)
            self.assertEqual(doc.created[0].Height, 220.0)
            self.assertEqual(doc.created[0].Placement.Base.values, (700.0, -220.0, 350.0))
            self.assertEqual(doc.created[0].Placement.Rotation.values[1].values, (0.0, 1.0, 0.0))
            with self.assertRaises(ValueError):
                freecad_tools._create_step(doc, "create_part_cylinder", {
                    "radius": 350, "height": 220, "axis": [0, 0, 0]
                })
        self.assertEqual(len(doc.created), 1)

    def test_native_sphere_and_cone_creation_preserve_approved_geometry(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import math

        class Vector:
            def __init__(self, *values):
                self.values = values
                self.Length = math.sqrt(sum(value * value for value in values))
        class Rotation:
            def __init__(self, *values):
                self.values = values
        class Placement:
            def __init__(self, base, rotation):
                self.Base, self.Rotation = base, rotation
        class FakeObject:
            Label = ""
            TypeId = ""
            Name = ""
        class FakeDoc:
            def __init__(self):
                self.objects = []
            def addObject(self, type_id, name):
                obj = FakeObject()
                obj.TypeId, obj.Name = type_id, name
                self.objects.append(obj)
                return obj

        app = SimpleNamespace(Vector=Vector, Rotation=Rotation, Placement=Placement)
        doc = FakeDoc()
        with patch.object(freecad_tools, "_apps", return_value=(app, None)):
            sphere = freecad_tools._create_step(doc, "create_part_sphere", {
                "radius": 35, "center": [10,20,30], "label": "KN01"
            })
            cone = freecad_tools._create_step(doc, "create_part_cone", {
                "radius1": 40, "radius2": 10, "height": 120,
                "origin": [0,0,0], "axis": [0,0,1], "label": "NZ01"
            })
        self.assertEqual(sphere["type"], "Part::Sphere")
        self.assertEqual(doc.objects[0].Radius, 35.0)
        self.assertEqual(doc.objects[0].Placement.Base.values, (10.0,20.0,30.0))
        self.assertEqual(cone["type"], "Part::Cone")
        self.assertEqual(doc.objects[1].Radius1, 40.0)
        self.assertEqual(doc.objects[1].Radius2, 10.0)
        self.assertEqual(doc.objects[1].Height, 120.0)

    def test_write_tools_are_typed_and_approval_gated(self):
        for tool in tool_registry.TOOLS:
            self.assertIn("parameters", tool)
            self.assertIn("read_only", tool)
        self.assertTrue(any(not item["read_only"] for item in tool_registry.TOOLS))

    def test_native_dimension_edit_tool_is_typed_and_approval_gated(self):
        tool = next(item for item in tool_registry.TOOLS if item["name"] == "edit_native_property")
        properties = tool["parameters"]["properties"]
        self.assertEqual(properties["property_name"]["enum"], [
            "Length", "Width", "Height", "Radius", "Radius1", "Radius2", "Label"
        ])
        self.assertEqual(set(tool["parameters"]["required"]), {"object_name", "property_name", "value"})
        self.assertFalse(tool["read_only"])

    def test_native_dimension_edit_changes_only_an_allowlisted_property(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeObject:
            Name = "WatchTowerColumn01"
            Label = "Column 01"
            TypeId = "Part::Box"
            PropertiesList = ["Length", "Width", "Height", "Label"]
            State = []
            Shape = None

            def __init__(self):
                self.Length = 300.0

            def getTypeIdOfProperty(self, name):
                return "App::PropertyLength" if name in {"Length", "Width", "Height"} else "App::PropertyString"

            def getEditorMode(self, name):
                return 0

        class FakeDoc:
            def __init__(self, obj):
                self.obj = obj
                self.recompute_count = 0

            def getObject(self, name):
                return self.obj if name == self.obj.Name else None

            def recompute(self):
                self.recompute_count += 1

        obj = FakeObject()
        doc = FakeDoc(obj)
        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), None)):
            result = freecad_tools._partdesign_step(doc, "edit_native_property", {
                "object_name": "WatchTowerColumn01",
                "property_name": "Length",
                "value": 6500,
            })
            self.assertEqual(result["before"], 300.0)
            self.assertEqual(result["after"], 6500.0)
            self.assertEqual(obj.Length, 6500.0)
            self.assertGreaterEqual(doc.recompute_count, 1)

            with self.assertRaises(ValueError):
                freecad_tools._partdesign_step(doc, "edit_native_property", {
                    "object_name": "WatchTowerColumn01",
                    "property_name": "Placement",
                    "value": 2,
                })

    def test_native_label_edit_is_persistent_object_rename_not_recreation(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeObject:
            Name = "Beam01"
            Label = "Old Beam Label"
            TypeId = "Part::Box"
            PropertiesList = ["Label"]

        class FakeDoc:
            def __init__(self, obj):
                self.obj = obj
            def getObject(self, name):
                return self.obj if name == self.obj.Name else None
            def recompute(self):
                pass

        obj = FakeObject()
        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), None)):
            result = freecad_tools._partdesign_step(FakeDoc(obj), "edit_native_property", {
                "object_name": "Beam01",
                "property_name": "Label",
                "value": "B01 — Primary perimeter beam (concept)",
            })
        self.assertEqual(result["edited"], "Beam01")
        self.assertEqual(obj.Label, "B01 — Primary perimeter beam (concept)")

    def test_plan_execution_reports_each_native_step_and_refreshes_viewport(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeDoc:
            def __init__(self):
                self.events = []
            def openTransaction(self, name):
                self.events.append("open")
            def recompute(self):
                self.events.append("recompute")
            def commitTransaction(self):
                self.events.append("commit")
            def abortTransaction(self):
                self.events.append("abort")

        class FakeGui:
            def __init__(self):
                self.refreshes = 0
            def updateGui(self):
                self.refreshes += 1

        doc, gui = FakeDoc(), FakeGui()
        progress = []
        plan = [
            {"tool": "create_draft_line", "args": {"start": [0, 0], "end": [100, 0]}},
            {"tool": "create_draft_text", "args": {"text": "ROOM LABEL"}},
        ]
        with patch.object(freecad_tools, "_assert_turn", return_value=doc), \
             patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), gui)), \
             patch.object(freecad_tools, "_create_step", side_effect=lambda d, tool, args: {"tool": tool}), \
             patch.object(freecad_tools, "_doc_summary", return_value={"object_count": 2}):
            result = freecad_tools.execute_plan(
                {"document": doc, "name": "Test", "file": ""},
                plan,
                progress_callback=lambda index, total, tool, phase: progress.append((index, total, tool, phase)),
            )
        self.assertTrue(result["success"])
        self.assertEqual(gui.refreshes, 3)
        self.assertEqual(progress, [
            (1, 2, "create_draft_line", "starting"),
            (1, 2, "create_draft_line", "completed"),
            (2, 2, "create_draft_text", "starting"),
            (2, 2, "create_draft_text", "completed"),
        ])
        self.assertEqual(doc.events[-1], "commit")

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


class NativeOperatorExtensionTests(unittest.TestCase):
    def test_plan_execution_is_limited_to_tool_schemas_supplied_for_the_turn(self):
        from unittest.mock import patch

        token = object()
        plan = [{"tool": "create_part_box", "args": {"length": 10, "width": 10, "height": 10}}]
        with patch.object(freecad_tools, "execute_plan") as execute:
            with self.assertRaises(ValueError):
                tool_registry.execute_approved_plan(
                    token, plan, allowed_tool_names={"create_draft_line"}
                )
            execute.assert_not_called()

        with patch.object(freecad_tools, "execute_plan", return_value={"success": True}) as execute:
            result = tool_registry.execute_approved_plan(
                token, plan, allowed_tool_names={"create_part_box"}
            )
            self.assertEqual(result, {"success": True})
            execute.assert_called_once()

    def test_reusable_freecad_operator_actions_are_available_as_typed_tools(self):
        expected = {
            "boolean_operation",
            "transform_object",
            "duplicate_object",
            "fillet_edges",
            "chamfer_edges",
            "linear_pattern",
            "polar_pattern",
            "create_model_schedule",
        }
        registered = {item["name"] for item in tool_registry.TOOLS}
        self.assertTrue(expected.issubset(registered))
        for name in expected:
            tool = next(item for item in tool_registry.TOOLS if item["name"] == name)
            self.assertFalse(tool["read_only"])
            self.assertFalse(tool["parameters"].get("additionalProperties", True))

    def test_generic_native_command_cannot_run_unreviewed_gui_action(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        class FakeDoc:
            pass

        fake_gui = SimpleNamespace()
        with patch.object(freecad_tools, "_apps", return_value=(SimpleNamespace(), fake_gui)):
            for command in ("Std_Delete", "Std_Save", "Std_Open", "Std_Macro"):
                with self.subTest(command=command):
                    with self.assertRaises(ValueError):
                        freecad_tools._create_step(FakeDoc(), "run_native_command", {
                            "command_id": command,
                        })
        self.assertIn("Std_ViewFitAll", freecad_tools.SAFE_VIEW_COMMANDS)
        self.assertNotIn("Std_Delete", freecad_tools.SAFE_VIEW_COMMANDS)

    def test_edge_reference_validation_requires_explicit_topology_or_all(self):
        from types import SimpleNamespace

        shape = SimpleNamespace(Edges=[object(), object(), object()])
        self.assertEqual(
            freecad_tools._edge_references(shape, ["Edge1", "Edge3"]),
            ["Edge1", "Edge3"],
        )
        self.assertEqual(
            freecad_tools._edge_references(shape, ["all"]),
            ["Edge1", "Edge2", "Edge3"],
        )
        for invalid in (["Edge0"], ["Edge4"], ["Face1"], ["all", "Edge1"], []):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    freecad_tools._edge_references(shape, invalid)

    def test_native_name_sanitisation_produces_freecad_identifier(self):
        self.assertEqual(freecad_tools._native_name("Water Tower / Tank", "Operation"),
                         "Water_Tower___Tank")
        self.assertEqual(freecad_tools._native_name("123 Gear", "Operation"),
                         "NextAI_123_Gear")


class ModelScheduleTests(unittest.TestCase):
    def test_schedule_tool_is_typed_and_mutating(self):
        tool = next(item for item in tool_registry.TOOLS if item["name"] == "create_model_schedule")
        self.assertFalse(tool["read_only"])
        self.assertEqual(tool["parameters"]["properties"]["object_names"]["maxItems"], 200)
        self.assertFalse(tool["parameters"]["additionalProperties"])

    def test_model_schedule_uses_native_measured_geometry_and_properties(self):
        from types import SimpleNamespace

        class FakeShape:
            Volume = 24000.0
            Area = 12400.0
            Solids = [object()]
            Faces = [object()] * 6
            Edges = [object()] * 12
            Vertexes = [object()] * 8
            class Bounds:
                XMin, YMin, ZMin = 0.0, 0.0, 0.0
                XMax, YMax, ZMax = 60.0, 40.0, 10.0
                XLength, YLength, ZLength = 60.0, 40.0, 10.0
            BoundBox = Bounds()
            def isNull(self):
                return False
            def isValid(self):
                return True

        class FakeObject:
            Name = "Beam01"
            Label = "Primary beam"
            TypeId = "Part::Box"
            PropertiesList = ["Length", "Width", "Height"]
            Shape = FakeShape()
            Length, Width, Height = 60.0, 40.0, 10.0

        class FakeSheet:
            TypeId = "Spreadsheet::Sheet"
            def __init__(self, name):
                self.Name = name
                self.Label = name
                self.cells = {}
            def set(self, address, value):
                self.cells[address] = value

        class FakeDoc:
            def __init__(self):
                self.obj = FakeObject()
                self.sheet = None
                self.recompute_count = 0
                self.Objects = [self.obj]
            def getObject(self, name):
                if name == self.obj.Name:
                    return self.obj
                if self.sheet is not None and name == self.sheet.Name:
                    return self.sheet
                return None
            def addObject(self, type_id, name):
                self.sheet = FakeSheet(name)
                self.asserted_type = type_id
                return self.sheet
            def recompute(self):
                self.recompute_count += 1

        doc = FakeDoc()
        result = freecad_tools._create_model_schedule(doc, {
            "name": "BeamSchedule",
            "object_names": ["Beam01"],
        })
        self.assertEqual(result["schedule"], "BeamSchedule")
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(doc.asserted_type, "Spreadsheet::Sheet")
        self.assertEqual(doc.sheet.cells["A1"], "Mark")
        self.assertEqual(doc.sheet.cells["B2"], "Beam01")
        self.assertEqual(doc.sheet.cells["E2"], "60.0")
        self.assertEqual(doc.sheet.cells["F2"], "40.0")
        self.assertEqual(doc.sheet.cells["G2"], "10.0")
        self.assertEqual(doc.sheet.cells["H2"], "12400.0")
        self.assertEqual(doc.sheet.cells["I2"], "24000.0")
        self.assertEqual(doc.sheet.cells["M2"], "TRUE")
        self.assertIn("Length=60.0", doc.sheet.cells["N2"])
        self.assertGreaterEqual(doc.recompute_count, 1)

    def test_model_schedule_does_not_overwrite_existing_schedule(self):
        from types import SimpleNamespace

        class FakeDoc:
            def __init__(self):
                self.model_object = SimpleNamespace(
                    Name="ModelObject", Label="Model object", TypeId="Part::Feature",
                    PropertiesList=[], Shape=None,
                )
                self.Objects = [self.model_object]
            def getObject(self, name):
                if name == "ExistingSchedule":
                    return SimpleNamespace(Name=name)
                return self.model_object if name == "ModelObject" else None
            def addObject(self, type_id, name):
                raise AssertionError("No object should be added on overwrite")
        with self.assertRaises(ValueError):
            freecad_tools._create_model_schedule(FakeDoc(), {"name": "ExistingSchedule"})


if __name__ == "__main__":
    unittest.main()
