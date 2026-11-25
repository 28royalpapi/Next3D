"""Machine-readable tool catalogue and dispatcher for NextAI."""
from __future__ import annotations

from . import freecad_tools, knowledge

TOOLS = [
    {
        "name": "inspect_document",
        "description": "Read the open native document and its objects.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "read_only": True,
    },
    {
        "name": "discover_capabilities",
        "description": "List the workbenches and native commands available in this NextCAD installation.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "read_only": True,
    },
    {
        "name": "create_draft_line",
        "description": "Create a native Draft line from start to end coordinates in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "start": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "end": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["start", "end"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_draft_rectangle",
        "description": "Create a native 2D Draft rectangle in the XY plane, with dimensions in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "exclusiveMinimum": 0},
                "width": {"type": "number", "exclusiveMinimum": 0},
                "origin": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["length", "width"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_arch_wall",
        "description": "Create a parametric native Arch wall along a point path, with height and width in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "points": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}, "minItems": 2, "maxItems": 200},
                "height": {"type": "number", "default": 3000},
                "width": {"type": "number", "default": 200},
                "label": {"type": "string"},
            },
            "required": ["points"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_part_box",
        "description": "Create a native parametric Part box with length, width and height in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "exclusiveMinimum": 0},
                "width": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "origin": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["length", "width", "height"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_part_cylinder",
        "description": "Create an editable native Part cylinder with a chosen axis, radius and height in millimetres; useful for shafts, pins, columns and wheel-envelope concepts.",
        "parameters": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "origin": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "axis": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"}
            },
            "required": ["radius", "height"],
            "additionalProperties": False
        },
        "read_only": False
    },
    {
        "name": "create_part_sphere",
        "description": "Create an editable native Part sphere centred at a specified point, with radius in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"}
            },
            "required": ["radius"],
            "additionalProperties": False
        },
        "read_only": False
    },
    {
        "name": "create_part_cone",
        "description": "Create an editable native Part cone or frustum with two end radii, height and axis in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "radius1": {"type": "number", "minimum": 0},
                "radius2": {"type": "number", "minimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "origin": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "axis": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"}
            },
            "required": ["radius1", "radius2", "height"],
            "additionalProperties": False
        },
        "read_only": False
    },
    {
        "name": "create_draft_wire",
        "description": "Create a native Draft polyline or closed plan outline from 2D/3D points in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "points": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3}, "minItems": 2, "maxItems": 200},
                "closed": {"type": "boolean", "default": False},
                "label": {"type": "string"},
            },
            "required": ["points"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_draft_dimension",
        "description": "Create a native Draft dimension between two points, placed through a third point.",
        "parameters": {
            "type": "object",
            "properties": {
                "start": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "end": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "dimension_line_point": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["start", "end", "dimension_line_point"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_draft_circle",
        "description": "Create a native 2D Draft circle at a position, with radius in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["radius"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_draft_text",
        "description": "Place native Draft annotation text at a 3D position, with text height in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": 2000},
                "position": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "height": {"type": "number", "default": 250},
                "label": {"type": "string"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_arch_structure",
        "description": "Create a parametric native Arch structural element from a rectangular cross-section; height determines column/beam proportions.",
        "parameters": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "exclusiveMinimum": 0},
                "width": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "origin": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
            },
            "required": ["length", "width", "height"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "activate_workbench",
        "description": "Switch to a workbench registered in this installation.",
        "parameters": {
            "type": "object",
            "properties": {"workbench_id": {"type": "string"}},
            "required": ["workbench_id"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "run_native_command",
        "description": "Run an approved, registered FreeCAD GUI command by its exact command id.",
        "parameters": {
            "type": "object",
            "properties": {"command_id": {"type": "string"}},
            "required": ["command_id"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_partdesign_body",
        "description": "Create or retrieve a native parametric PartDesign body. This starts an editable feature-history model, not a static mesh.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 80}},
            "required": ["name"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_partdesign_sketch",
        "description": "Create a native Sketcher sketch attached to the selected body's own XY, XZ or YZ origin plane. Offset is millimetres along the plane normal.",
        "parameters": {
            "type": "object",
            "properties": {
                "body_name": {"type": "string"},
                "name": {"type": "string", "minLength": 1, "maxLength": 80},
                "plane": {"type": "string", "enum": ["XY_Plane", "XZ_Plane", "YZ_Plane"], "default": "XY_Plane"},
                "offset": {"type": "number", "default": 0}
            },
            "required": ["body_name", "name"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_parametric_variables",
        "description": "Create or extend a native FreeCAD App::VarSet of named project parameters. Numbers default to millimetres; choose Integer, Angle, Float, String or Bool explicitly when needed. Returns the exact expression paths to use.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Vars", "minLength": 1, "maxLength": 40},
                "variables": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 80,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "minLength": 1, "maxLength": 40},
                            "value": {"type": ["number", "integer", "string", "boolean"]},
                            "type": {
                                "type": "string",
                                "enum": [
                                    "App::PropertyLength", "App::PropertyFloat",
                                    "App::PropertyInteger", "App::PropertyAngle",
                                    "App::PropertyString", "App::PropertyBool"
                                ],
                                "default": "App::PropertyLength"
                            },
                            "description": {"type": "string", "maxLength": 240}
                        },
                        "required": ["name", "value"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["variables"],
            "additionalProperties": False
        },
        "read_only": False
    },
    {
        "name": "bind_parametric_expression",
        "description": "Bind a native object property or named Sketcher constraint to a validated FreeCAD expression, such as Vars.OverallLength or Vars.Bore * 2. The expression is checked and the document recomputed.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string"},
                "property_name": {"type": "string", "minLength": 1, "maxLength": 100},
                "expression": {"type": "string", "minLength": 1, "maxLength": 240}
            },
            "required": ["object_name", "property_name", "expression"],
            "additionalProperties": False
        },
        "read_only": False
    },
    {
        "name": "add_sketch_line",
        "description": "Add a native line segment to a sketch in millimetres. Both endpoints are fixed by Sketcher constraints; use exact coordinates and don't infer dimensions.",
        "parameters": {
            "type": "object",
            "properties": {
                "sketch_name": {"type": "string"},
                "start": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "end": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
                "construction": {"type": "boolean", "default": False}
            },
            "required": ["sketch_name", "start", "end"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "add_sketch_circle",
        "description": "Add a native, dimension-constrained circle to a sketch. The centre and diameter are constrained; radius is in millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "sketch_name": {"type": "string"},
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
                "label": {"type": "string"},
                "construction": {"type": "boolean", "default": False}
            },
            "required": ["sketch_name", "radius"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "add_sketch_polygon",
        "description": "Add a closed native polygonal Sketcher profile with connected, fully constrained vertices. The points are XY coordinates in millimetres. Only use for a planar, non-self-intersecting outline.",
        "parameters": {
            "type": "object",
            "properties": {
                "sketch_name": {"type": "string"},
                "points": {"type": "array", "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3}, "minItems": 3, "maxItems": 80}
            },
            "required": ["sketch_name", "points"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_partdesign_pad",
        "description": "Create a native parametric PartDesign Pad from a fully constrained sketch in the same body. The result must be one valid solid and increase volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "body_name": {"type": "string"},
                "sketch_name": {"type": "string"},
                "length": {"type": "number", "exclusiveMinimum": 0},
                "name": {"type": "string", "maxLength": 120},
                "symmetric": {"type": "boolean", "default": False}
            },
            "required": ["body_name", "sketch_name", "length"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "create_partdesign_pocket",
        "description": "Create a native parametric PartDesign Pocket from a fully constrained sketch in the same body. The result must remove material from a valid solid or the operation is rolled back.",
        "parameters": {
            "type": "object",
            "properties": {
                "body_name": {"type": "string"},
                "sketch_name": {"type": "string"},
                "length": {"type": "number", "exclusiveMinimum": 0},
                "name": {"type": "string", "maxLength": 120},
                "reversed": {"type": "boolean", "default": True},
                "through_all": {"type": "boolean", "default": False}
            },
            "required": ["body_name", "sketch_name", "length"],
            "additionalProperties": False,
        },
        "read_only": False,
    },
    {
        "name": "edit_native_property",
        "description": "Edit an existing native object dimension or its Label. Use the actual object Name from inspect_document; geometry is recomputed and validated.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "property_name": {"type": "string", "enum": ["Length", "Width", "Height", "Radius", "Radius1", "Radius2", "Label"]},
                "value": {"type": ["number", "string"]}
            },
            "required": ["object_name", "property_name", "value"],
            "additionalProperties": False
        },
        "read_only": False
    },
]


def read_context(query: str = ""):
    return {
        "capabilities": freecad_tools.discover_capabilities(query),
        "document": freecad_tools.inspect_document(),
        "available_tools": TOOLS,
        "relevant_native_documentation": knowledge.search(query),
    }


def execute_approved_plan(token, plan, progress_callback=None):
    allowed = {tool["name"] for tool in TOOLS if not tool["read_only"]}
    for step in plan:
        if not isinstance(step, dict) or step.get("tool") not in allowed:
            raise ValueError("The plan contains a tool that is not in the approved NextCAD registry.")
    return freecad_tools.execute_plan(token, plan, progress_callback=progress_callback)
