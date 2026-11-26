"""Small dependency-free JSON Schema validator for NextAI native training records.

Supports the JSON Schema Draft 2020-12 keywords used by
schemas/next-ai-training-record.v1.schema.json. It intentionally fails closed
for unsupported schema keywords so training records cannot silently bypass the
repository's published contract.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class SchemaValidationError(ValueError):
    pass


SUPPORTED = {
    "$schema", "$id", "title", "description", "$defs", "$ref",
    "type", "const", "enum", "required", "properties",
    "additionalProperties", "items", "minItems", "maxItems",
    "uniqueItems", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
}


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise SchemaValidationError(f"Unsupported schema reference: {reference!r}")
    current: Any = root
    for segment in reference[2:].split("/"):
        segment = segment.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or segment not in current:
            raise SchemaValidationError(f"Unresolved schema reference: {reference}")
        current = current[segment]
    if not isinstance(current, dict):
        raise SchemaValidationError(f"Schema reference is not an object: {reference}")
    return current


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise SchemaValidationError(f"Unsupported JSON Schema type: {expected}")


def _fail(path: str, message: str) -> None:
    raise SchemaValidationError(f"{path}: {message}")


def validate_instance(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None,
                      path: str = "$") -> None:
    """Raise SchemaValidationError unless instance satisfies the supplied schema."""
    if root is None:
        root = schema
    if not isinstance(schema, dict):
        _fail(path, "schema node must be an object")

    unknown = set(schema) - SUPPORTED
    if unknown:
        _fail(path, f"schema uses unsupported keyword(s): {', '.join(sorted(unknown))}")

    if "$ref" in schema:
        validate_instance(instance, _resolve_ref(root, schema["$ref"]), root, path)
        siblings = {key: value for key, value in schema.items() if key != "$ref"}
        if siblings:
            validate_instance(instance, siblings, root, path)
        return

    if "type" in schema:
        allowed_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_matches_type(instance, value) for value in allowed_types):
            _fail(path, f"expected type {' or '.join(allowed_types)}")

    if "const" in schema and instance != schema["const"]:
        _fail(path, f"must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        _fail(path, f"value {instance!r} is not in the allowed enumeration")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            _fail(path, f"length must be at least {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            _fail(path, f"length must be at most {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            _fail(path, f"does not match pattern {schema['pattern']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            _fail(path, f"must be >= {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            _fail(path, f"must be <= {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            _fail(path, f"must be > {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            _fail(path, f"must be < {schema['exclusiveMaximum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            _fail(path, f"must contain at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            _fail(path, f"must contain at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
            if len(set(encoded)) != len(encoded):
                _fail(path, "items must be unique")
        if "items" in schema:
            for index, item in enumerate(instance):
                validate_instance(item, schema["items"], root, f"{path}[{index}]")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                _fail(path, f"missing required property {key!r}")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            _fail(path, "properties must be an object")
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            if key in properties:
                validate_instance(value, properties[key], root, child_path)
            elif schema.get("additionalProperties") is False:
                _fail(child_path, "additional properties are not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_instance(value, schema["additionalProperties"], root, child_path)


def load_training_record_schema(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "schemas" / "next-ai-training-record.v1.schema.json"
    schema_path = Path(path)
    try:
        value = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"Could not load training-record schema {schema_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaValidationError("Training-record schema root must be an object.")
    return value


def validate_training_record(record: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """Validate a complete NextAI native record against the checked-in schema."""
    if schema is None:
        schema = load_training_record_schema()
    validate_instance(record, schema, schema, "$")
