#!/usr/bin/env python3
"""Run held-out multimodal SFT evaluation and report scores by domain.

This is an early model-quality diagnostic. It does not replace native FreeCAD,
BIMCraft, IFC schema, geometry or engineering validation.
"""
from __future__ import annotations

import argparse
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


def score_record(expected: str, predicted: str) -> dict[str, Any]:
    expected_json = parse_json_object(expected)
    predicted_json = parse_json_object(predicted)
    if expected_json is None:
        return {
            "json_parse": None,
            "key_recall": None,
            "scalar_match": None,
            "token_f1": token_f1(expected, predicted),
        }
    if predicted_json is None:
        return {"json_parse": 0.0, "key_recall": 0.0, "scalar_match": 0.0, "token_f1": token_f1(expected, predicted)}

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


def prompt_for(row: dict[str, Any]) -> tuple[str, str, list[str]]:
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
    images = [str(path) for path in row.get("images", []) if path]
    return system, prompt, images


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Base Hugging Face model or local LoRA/model directory")
    parser.add_argument("--test-jsonl", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()

    rows = load_jsonl(args.test_jsonl)
    if args.max_records:
        rows = rows[:args.max_records]
    if not rows:
        raise RuntimeError("The held-out test file is empty.")

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
        system, prompt, image_paths = prompt_for(row)
        expected = str(row.get("completion") or "")
        if isinstance(row.get("messages"), list):
            _, _, _ = prompt_for(row)
            if not expected:
                expected = str(row.get("messages", [{}])[-1].get("content") or "")
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
        input_text = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
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
            "predicted": output_text,
            "scores": scores,
        })
        if (index + 1) % 20 == 0:
            print(f"Evaluated {index + 1}/{len(rows)} held-out records")

    summary = {}
    for domain, items in metrics_by_domain.items():
        summary[domain] = {}
        for key in ("json_parse", "key_recall", "scalar_match", "token_f1"):
            values = [item[key] for item in items if item.get(key) is not None]
            if values:
                summary[domain][key] = sum(values) / len(values)
        summary[domain]["records"] = len(items)

    output = {
        "model": args.model,
        "test_records": len(records),
        "test_split_used_for_training": False,
        "metrics_by_domain": summary,
        "records": records,
        "interpretation": (
            "JSON structure and token-overlap diagnostics only. They are not "
            "engineering accuracy, native command success, geometry validity "
            "or statutory compliance. Verify native outputs in NextCAD, "
            "Next BIM and applicable schema/checking tools."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
