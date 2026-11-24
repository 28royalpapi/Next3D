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
]


def read_context(query: str = ""):
    return {
        "capabilities": freecad_tools.discover_capabilities(),
        "document": freecad_tools.inspect_document(),
        "available_tools": TOOLS,
        "relevant_native_documentation": knowledge.search(query),
    }


def execute_approved_plan(token, plan):
    allowed = {tool["name"] for tool in TOOLS if not tool["read_only"]}
    for step in plan:
        if not isinstance(step, dict) or step.get("tool") not in allowed:
            raise ValueError("The plan contains a tool that is not in the approved NextCAD registry.")
    return freecad_tools.execute_plan(token, plan)
