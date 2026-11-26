"""Machine-readable tool catalogue and dispatcher for NextAI."""
from __future__ import annotations

import math
import re

from . import engineering_skills, freecad_tools, knowledge

_TOOL_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}")
_TOOL_STOP = {"create", "native", "tool", "the", "with", "from", "and", "for", "use", "read", "only"}

TOOLS = [
    {
        "name": "create_model_schedule",
        "description": "Create a native Spreadsheet schedule from actual model objects. Reports native IDs/types, measured bounding-box spans, shape area/volume/topology and exposed dimension properties; blank fields remain blank when the native model does not expose them.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]{0,39}$"},
                "label": {"type": "string", "maxLength": 120},
                "object_names": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 120},
                    "maxItems": 200,
                    "uniqueItems": True
                }
            },
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "boolean_operation",
        "description": "Create a native fuse, cut or common between two different objects. Two PartDesign Bodies use a PartDesign Boolean feature inside the first Body; other shape combinations use a native Part Boolean object.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["fuse", "cut", "common"]},
                "object1": {"type": "string", "minLength": 1, "maxLength": 120},
                "object2": {"type": "string", "minLength": 1, "maxLength": 120},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["operation", "object1", "object2"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "transform_object",
        "description": "Move and/or rotate an existing native object. Relative mode adds global translation and rotates in place; absolute mode replaces the object's placement. Rotation angles are degrees and translations are millimetres.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "translate_x": {"type": "number"},
                "translate_y": {"type": "number"},
                "translate_z": {"type": "number"},
                "rotate_axis_x": {"type": "number"},
                "rotate_axis_y": {"type": "number"},
                "rotate_axis_z": {"type": "number"},
                "rotate_angle": {"type": "number"},
                "relative": {"type": "boolean", "default": True}
            },
            "required": ["object_name"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "duplicate_object",
        "description": "Create an independent native copy of an object while leaving the original unchanged. It preserves the object's parametric history where FreeCAD copyObject supports it; optional translation and rotation offset the copy.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "translate_x": {"type": "number"},
                "translate_y": {"type": "number"},
                "translate_z": {"type": "number"},
                "rotate_axis_x": {"type": "number"},
                "rotate_axis_y": {"type": "number"},
                "rotate_axis_z": {"type": "number"},
                "rotate_angle": {"type": "number"},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["object_name"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "fillet_edges",
        "description": "Add a native fillet to explicit EdgeN references or all edges. Inside a PartDesign Body it creates a parametric PartDesign Fillet on the current Body tip. For non-PartDesign shapes it creates a separate derived Part shape linked to the source object.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "edges": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 200},
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["object_name", "edges", "radius"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "chamfer_edges",
        "description": "Add a native chamfer to explicit EdgeN references or all edges. Inside a PartDesign Body it creates a parametric PartDesign Chamfer on the current Body tip. For non-PartDesign shapes it creates a separate derived Part shape linked to the source object.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "edges": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 200},
                "size": {"type": "number", "exclusiveMinimum": 0},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["object_name", "edges", "size"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "linear_pattern",
        "description": "Create a parametric PartDesign linear pattern of a feature inside a Body, along the Body's X, Y or Z origin axis.",
        "parameters": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "direction": {"type": "string", "enum": ["X", "Y", "Z"], "default": "X"},
                "length": {"type": "number", "exclusiveMinimum": 0},
                "occurrences": {"type": "integer", "minimum": 2, "maximum": 1000},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["feature_name", "length", "occurrences"],
            "additionalProperties": False
        },
        "read_only": False,
    },
    {
        "name": "polar_pattern",
        "description": "Create a parametric PartDesign circular pattern of a feature inside a Body, about the Body's X, Y or Z origin axis.",
        "parameters": {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string", "minLength": 1, "maxLength": 120},
                "axis": {"type": "string", "enum": ["X", "Y", "Z"], "default": "Z"},
                "angle": {"type": "number", "exclusiveMinimum": 0, "maximum": 360, "default": 360},
                "occurrences": {"type": "integer", "minimum": 2, "maximum": 1000},
                "label": {"type": "string", "maxLength": 120}
            },
            "required": ["feature_name", "occurrences"],
            "additionalProperties": False
        },
        "read_only": False,
    },
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
        "description": "Run only an explicitly reviewed, non-destructive view command. Native model changes must use typed NextAI operations; discovering a GUI command does not authorise executing it.",
        "parameters": {
            "type": "object",
            "properties": {"command_id": {"type": "string", "enum": [
                "Std_ViewFitAll", "Std_ViewIsometric", "Std_ViewAxonometric",
                "Std_ViewTop", "Std_ViewBottom", "Std_ViewFront", "Std_ViewRear",
                "Std_ViewLeft", "Std_ViewRight", "Std_OrthographicCamera", "Std_PerspectiveCamera"
            ]}},
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


def _terms(value: str) -> set[str]:
    return {token.lower() for token in _TOOL_TOKEN.findall(str(value)) if token.lower() not in _TOOL_STOP}


def rank_tools(query: str, limit: int = 12) -> list[dict]:
    """Rank the fixed, reviewed native tool schemas for the current request.

    This is deterministic and local. It is a recommendation signal, not an
    access-control decision: every executable tool remains explicitly listed
    in TOOLS and is still checked by execute_approved_plan.
    """
    limit = max(1, min(int(limit), len(TOOLS)))
    query_terms = _terms(query)
    if not query_terms:
        return [
            {"name": item["name"], "read_only": item["read_only"], "score": 0.0}
            for item in TOOLS[:limit]
        ]
    documents = []
    for item in TOOLS:
        schema_text = str(item.get("parameters", {}))
        documents.append(_terms(item["name"] + " " + item["description"] + " " + schema_text))
    frequency = {}
    for terms in documents:
        for term in terms:
            frequency[term] = frequency.get(term, 0) + 1
    ranked = []
    for item, terms in zip(TOOLS, documents):
        overlap = query_terms.intersection(terms)
        score = sum(math.log((len(TOOLS) + 1) / (frequency.get(term, 0) + 1)) + 1 for term in overlap)
        if item["name"] in {"inspect_document", "discover_capabilities"}:
            score += 0.15
        ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    return [
        {"name": item["name"], "read_only": item["read_only"], "score": round(score, 3)}
        for score, item in ranked[:limit]
    ]


def select_tool_schemas(query: str, limit: int = 14) -> list[dict]:
    """Return only the most relevant reviewed tool schemas for this local turn.

    Read-only inspect/discovery are always retained. A task-specific schedule
    request keeps the native Spreadsheet tool visible even when the noun is
    expressed indirectly. Full capability discovery remains separate.
    """
    limit = max(2, min(int(limit), len(TOOLS)))
    ranked = rank_tools(query, limit=limit)
    selected_names = [item["name"] for item in ranked]
    for required in ("inspect_document", "discover_capabilities"):
        if required not in selected_names:
            selected_names.append(required)
    terms = _terms(query)
    if terms.intersection({"schedule", "schedules", "table", "tables", "bom", "bill", "quantities", "quantity", "component"}):
        if "create_model_schedule" not in selected_names:
            selected_names.append("create_model_schedule")
    if len(selected_names) > limit + 1:
        selected_names = selected_names[:limit + 1]
    selected = [tool for tool in TOOLS if tool["name"] in selected_names]
    # Keep the list ordered by retrieval rank, not by the global source order.
    order = {name: index for index, name in enumerate(selected_names)}
    selected.sort(key=lambda tool: order.get(tool["name"], len(order)))
    return selected


def read_context(query: str = ""):
    """Build a local task context with engineering skills and a progressively selected tool set."""
    skill_context = engineering_skills.EngineeringSkillRegistry().retrieve(query)
    selected_tools = select_tool_schemas(query)
    return {
        "context_contract": {
            "engineering_skills": "Explain WHAT the user wants to build, what to ask, domain components and deliverables.",
            "native_capabilities": "Explain HOW this exact installation can build, inspect, edit and validate it.",
            "authority": "Live native capabilities and reviewed typed tool schemas override any skill suggestion.",
            "locality": "Skill files and manuals are read from this laptop; they are not uploaded to a remote knowledge service.",
            "tool_selection": "Only task-relevant typed tools are supplied this turn. Ask for native capability discovery in a later turn if a new operation becomes necessary.",
        },
        "engineering_skills": skill_context,
        "ranked_tools": [
            {"name": tool["name"], "read_only": tool["read_only"]}
            for tool in selected_tools
        ],
        "tool_selection_summary": {
            "total_reviewed_typed_tools": len(TOOLS),
            "selected_for_this_turn": len(selected_tools),
            "selected_names": [tool["name"] for tool in selected_tools],
        },
        "capabilities": freecad_tools.discover_capabilities(query),
        "document": freecad_tools.inspect_document(),
        "available_tools": selected_tools,
        "relevant_native_documentation": knowledge.search(query),
    }


def execute_approved_plan(token, plan, progress_callback=None, allowed_tool_names=None):
    allowed = {tool["name"] for tool in TOOLS if not tool["read_only"]}
    if allowed_tool_names is not None:
        allowed.intersection_update(set(allowed_tool_names))
    for step in plan:
        if not isinstance(step, dict) or step.get("tool") not in allowed:
            raise ValueError("The plan contains a tool that was not supplied for this turn or is not approved by the NextCAD registry.")
    return freecad_tools.execute_plan(token, plan, progress_callback=progress_callback)
