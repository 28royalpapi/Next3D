#!/usr/bin/env python3
"""Run held-out multimodal SFT evaluation and report scores by domain.

This is an early model-quality diagnostic. It does not replace native FreeCAD,
BIMCraft, IFC schema, geometry or engineering validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def token_f1(expected: str, predicted: str) -> float:
    left = Counter(normalize_tokens(expected))
    right = Counter(normalize_tokens(predicted))
    if not left or not right:
        return 0.0
    common = sum((left & right).values())
    precision = common / sum(right.values())
    recall = common / sum(left.values())
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def parse_json_object(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            if isinstance(value, (dict, list)):
                return value
        except json.JSONDecodeError:
            continue
    return None


def flatten_scalars(value: Any, prefix: str = "") -> dict[str, Any]:
    output = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            output.update(flatten_scalars(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]"
            output.update(flatten_scalars(child, path))
    elif value is not None:
        output[prefix] = value
    return output


def native_plan_metrics(expected_json: Any, predicted_json: Any) -> dict[str, Any]:
    """Score operation sequence and argument-key structure when references contain native plans."""
    expected_plan = expected_json.get("plan") if isinstance(expected_json, dict) else None
    if not isinstance(expected_plan, list):
        return {
            "plan_target_present": None,
            "plan_parse": None,
            "plan_shape_valid": None,
            "tool_sequence_exact": None,
            "tool_recall": None,
            "argument_key_recall": None,
            "plan_step_count_match": None,
        }

    predicted_plan = predicted_json.get("plan") if isinstance(predicted_json, dict) else None
    if not isinstance(predicted_plan, list):
        return {
            "plan_target_present": True,
            "plan_parse": 0.0,
            "plan_shape_valid": 0.0,
            "tool_sequence_exact": 0.0,
            "tool_recall": 0.0,
            "argument_key_recall": 0.0,
            "plan_step_count_match": 0.0,
        }

    def valid_step(step: Any) -> bool:
        return (
            isinstance(step, dict)
            and set(step) == {"tool", "args"}
            and isinstance(step.get("tool"), str)
            and bool(step["tool"].strip())
            and isinstance(step.get("args"), dict)
        )

    target_valid = all(valid_step(step) for step in expected_plan)
    predicted_valid = all(valid_step(step) for step in predicted_plan)
    expected_tools = [step.get("tool") for step in expected_plan if isinstance(step, dict)]
    predicted_tools = [step.get("tool") for step in predicted_plan if isinstance(step, dict)]
    target_set = set(expected_tools)
    predicted_set = set(predicted_tools)
    tool_recall = len(target_set & predicted_set) / max(1, len(target_set))

    expected_argument_keys = {
        f"{index}.{key}"
        for index, step in enumerate(expected_plan)
        if isinstance(step, dict) and isinstance(step.get("args"), dict)
        for key in step["args"]
    }
    predicted_argument_keys = {
        f"{index}.{key}"
        for index, step in enumerate(predicted_plan)
        if isinstance(step, dict) and isinstance(step.get("args"), dict)
        for key in step["args"]
    }
    key_recall = (
        len(expected_argument_keys & predicted_argument_keys)
        / max(1, len(expected_argument_keys))
    )
    return {
        "plan_target_present": True,
        "plan_parse": 1.0,
        "plan_shape_valid": 1.0 if predicted_valid else 0.0,
        "tool_sequence_exact": (
            1.0 if target_valid and predicted_valid and expected_tools == predicted_tools else 0.0
        ),
        "tool_recall": tool_recall,
        "argument_key_recall": key_recall,
        "plan_step_count_match": (
            1.0 if len(expected_plan) == len(predicted_plan) else 0.0
        ),
    }


def score_record(expected: str, predicted: str) -> dict[str, Any]:
    expected_json = parse_json_object(expected)
    predicted_json = parse_json_object(predicted)
    if expected_json is None:
        return {
            "json_parse": None,
            "key_recall": None,
            "scalar_match": None,
            "token_f1": token_f1(expected, predicted),
            **native_plan_metrics(None, None),
        }
    if predicted_json is None:
        return {
            "json_parse": 0.0,
            "key_recall": 0.0,
            "scalar_match": 0.0,
            "token_f1": token_f1(expected, predicted),
            **native_plan_metrics(expected_json, None),
        }

    expected_scalars = flatten_scalars(expected_json)
    predicted_scalars = flatten_scalars(predicted_json)
    expected_keys = set(expected_scalars)
    predicted_keys = set(predicted_scalars)
    key_recall = len(expected_keys & predicted_keys) / max(1, len(expected_keys))
    comparable = 0
    matches = 0
    for key, value in expected_scalars.items():
        if key not in predicted_scalars:
            continue
        if isinstance(value, (str, int, float, bool)):
            comparable += 1
            candidate = predicted_scalars[key]
            if candidate == value or str(candidate).strip().lower() == str(value).strip().lower():
                matches += 1
    scalar_match = matches / max(1, len(expected_scalars))
    return {
        "json_parse": 1.0,
        "key_recall": key_recall,
        "scalar_match": scalar_match,
        "token_f1": token_f1(expected, predicted),
        **native_plan_metrics(expected_json, predicted_json),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def fingerprint_records(rows: list[dict[str, Any]]) -> str:
    """Hash canonical record content in order so evaluation runs can prove split identity."""
    digest = hashlib.sha256()
    for row in rows:
        canonical = json.dumps(
            row, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\\n")
    return digest.hexdigest()


def prompt_for(row: dict[str, Any]) -> tuple[str, str, list[str], str]:
    system = str(row.get("system") or "")
    prompt = str(row.get("prompt") or "")
    expected = str(row.get("completion") or "")
    if isinstance(row.get("messages"), list):
        for message in row["messages"]:
            role = message.get("role")
            content = message.get("content")
            if role == "system":
                system = content if isinstance(content, str) else system
            elif role == "user":
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    prompt_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            prompt_parts.append(str(part.get("text") or ""))
                    prompt = "\n".join(prompt_parts)
            elif role == "assistant":
                if isinstance(content, str):
                    expected = content
                elif isinstance(content, list):
                    expected = "\n".join(
                        str(part.get("text") or "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    )
    images = [str(path) for path in (row.get("images") or []) if path]
    return system, prompt, images, expected


def chat_template_kwargs_for(row: dict[str, Any]) -> dict[str, Any]:
    """Return the same tool/template context used during SFT for held-out generation."""
    raw_kwargs = row.get("chat_template_kwargs") or {}
    if not isinstance(raw_kwargs, dict):
        raise ValueError("chat_template_kwargs must be a JSON object.")
    kwargs = dict(raw_kwargs)
    tools = row.get("tools")
    if tools is not None:
        if not isinstance(tools, list) or not tools:
            raise ValueError("The tools field must be a non-empty function-schema list.")
        if "tools" in kwargs and kwargs["tools"] != tools:
            raise ValueError("Top-level tools and chat_template_kwargs.tools disagree.")
        kwargs["tools"] = tools
    if "add_generation_prompt" in kwargs:
        raise ValueError("add_generation_prompt is controlled by the evaluator.")
    return kwargs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Base Hugging Face model or local LoRA/model directory")
    parser.add_argument("--test-jsonl", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()

    if args.max_records < 0:
        parser.error("--max-records cannot be negative.")
    source_rows = load_jsonl(args.test_jsonl)
    if not source_rows:
        raise RuntimeError("The held-out test file is empty.")
    source_test_split_records = len(source_rows)
    source_test_split_sha256 = fingerprint_records(source_rows)
    rows = source_rows[:args.max_records] if args.max_records else source_rows
    evaluated_records_sha256 = fingerprint_records(rows)
    evaluation_is_partial = len(rows) < source_test_split_records

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required for multimodal student evaluation.")

    from PIL import Image
    from unsloth import FastVisionModel

    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=args.model,
        load_in_4bit=False,
        use_gradient_checkpointing=False,
    )
    FastVisionModel.for_inference(model)
    device = "cuda"
    records = []
    metrics_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, row in enumerate(rows):
        system, prompt, image_paths, expected = prompt_for(row)
        if not expected.strip():
            raise RuntimeError(
                f"Held-out record {row.get('record_id', index)!r} has no assistant reference output; "
                "refusing to report misleading evaluation metrics."
            )
        user_content = []
        images = []
        for image_path in image_paths:
            with Image.open(image_path) as source:
                images.append(source.convert("RGB").copy())
            user_content.append({"type": "image"})
        user_content.append({"type": "text", "text": prompt})
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content})
        template_kwargs = chat_template_kwargs_for(row)
        input_text = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            **template_kwargs,
        )
        if images:
            inputs = tokenizer(
                images,
                input_text,
                add_special_tokens=False,
                return_tensors="pt",
            ).to(device)
        else:
            inputs = tokenizer(
                input_text,
                add_special_tokens=False,
                return_tensors="pt",
            ).to(device)
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
        prompt_tokens = inputs["input_ids"].shape[-1]
        output_text = tokenizer.decode(
            generated[0][prompt_tokens:],
            skip_special_tokens=True,
        ).strip()
        scores = score_record(expected, output_text)
        domain = str(row.get("domain") or "unknown")
        metrics_by_domain[domain].append(scores)
        records.append({
            "record_id": row.get("record_id", f"record-{index}"),
            "domain": domain,
            "tool_schema_supplied": bool(template_kwargs.get("tools")),
            "predicted": output_text,
            "scores": scores,
        })
        if (index + 1) % 20 == 0:
            print(f"Evaluated {index + 1}/{len(rows)} held-out records")

    summary = {}
    for domain, items in metrics_by_domain.items():
        summary[domain] = {}
        for key in ("json_parse", "key_recall", "scalar_match", "token_f1", "plan_parse", "plan_shape_valid", "tool_sequence_exact", "tool_recall", "argument_key_recall", "plan_step_count_match"):
            values = [item[key] for item in items if item.get(key) is not None]
            if values:
                summary[domain][key] = sum(values) / len(values)
        summary[domain]["records"] = len(items)

    output = {
        "model": args.model,
        "test_records": len(records),
        "source_test_split_records": source_test_split_records,
        "source_test_split_sha256": source_test_split_sha256,
        "evaluated_records_sha256": evaluated_records_sha256,
        "evaluation_is_partial": evaluation_is_partial,
        "evaluation_limit": args.max_records,
        "test_split_used_for_training": False,
        "metrics_by_domain": summary,
        "records": records,
        "interpretation": (
            "JSON structure, native-plan sequence and argument-key diagnostics, and token overlap only. "
            "They are not engineering accuracy, schema-valid command execution, native success, "
            "geometry validity or statutory compliance. Verify native outputs in NextCAD, "
            "Next BIM and applicable schema/checking tools."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
