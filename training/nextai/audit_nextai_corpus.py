#!/usr/bin/env python3
"""Exact text-token and dataset-integrity audit for a NextAI JSONL corpus.

Image patches are reported separately: this audit deliberately does not pretend
that image placeholders or eight-view CAD examples are text tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPLITS = ("train", "validation", "test")


def _part_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or "")
            if kind == "text":
                parts.append(str(item.get("text") or ""))
            elif kind in {"tool_call", "function_call"}:
                payload = item.get("tool_call") or item.get("function_call") or item
                parts.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            elif kind == "image":
                parts.append("[IMAGE_ASSET]")
        return "\n".join(parts)
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def render_record_text(row: dict[str, Any]) -> tuple[str, str]:
    """Return model-facing text and a separately counted tool-schema string."""
    messages = row.get("messages")
    if isinstance(messages, list):
        chunks = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "unknown")
            chunks.append(f"<{role}>\n{_part_text(message.get('content'))}")
            if message.get("tool_calls"):
                chunks.append(json.dumps(message["tool_calls"], ensure_ascii=False, sort_keys=True))
        text = "\n".join(chunks)
    else:
        text = "\n".join(
            part for part in (
                str(row.get("system") or ""),
                str(row.get("prompt") or ""),
                str(row.get("completion") or ""),
            ) if part
        )

    tool_schemas = row.get("tools")
    if tool_schemas is None:
        tool_schemas = (row.get("chat_template_kwargs") or {}).get("tools")
    schema_text = json.dumps(tool_schemas, ensure_ascii=False, sort_keys=True) if tool_schemas else ""
    return text, schema_text


def _token_length(tokenizer: Any, text: str) -> int:
    if not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))


def _content_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return float(ordered[index])


def audit_corpus(
    data_dir: Path,
    tokenizer: Any,
    *,
    max_records: int = 0,
    require_test: bool = True,
) -> dict[str, Any]:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory does not exist: {data_dir}")

    split_summaries: dict[str, Any] = {}
    identity_locations: dict[str, set[str]] = defaultdict(set)
    exact_hash_locations: dict[str, set[str]] = defaultdict(set)
    duplicate_text_records: list[dict[str, str]] = []
    duplicate_ids: list[dict[str, str]] = []
    missing_images: list[dict[str, Any]] = []
    domain_tokens: dict[str, Counter] = defaultdict(Counter)
    source_tokens: dict[str, Counter] = defaultdict(Counter)
    license_counts: Counter = Counter()
    evidence_counts: Counter = Counter()
    global_record_ids: dict[str, str] = {}
    global_text_hashes: dict[str, str] = {}
    image_total = 0
    image_bytes_total = 0

    for split in SPLITS:
        path = data_dir / f"{split}.jsonl"
        if not path.is_file():
            if split == "test" and not require_test:
                split_summaries[split] = {"records": 0, "missing_file": True}
                continue
            raise FileNotFoundError(f"Required {split}.jsonl is missing: {path}")

        record_count = 0
        token_total = 0
        schema_token_total = 0
        split_image_count = 0
        split_image_bytes = 0
        split_domains: Counter = Counter()
        split_sources: Counter = Counter()
        split_licenses: Counter = Counter()
        split_ids: set[str] = set()
        token_lengths: list[int] = []
        source_groups: set[str] = set()
        split_groups: set[str] = set()

        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                if max_records and record_count >= max_records:
                    break
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{line_number} is not a JSON object")
                record_count += 1

                record_id = str(row.get("record_id") or "").strip()
                if record_id:
                    if record_id in split_ids:
                        duplicate_ids.append({"record_id": record_id, "split": split, "file": path.name})
                    split_ids.add(record_id)
                    previous = global_record_ids.get(record_id)
                    if previous and previous != split:
                        identity_locations["record_id:" + record_id].update({previous, split})
                    else:
                        global_record_ids[record_id] = split

                for key in ("source_group_sha256", "split_group"):
                    identity = str(row.get(key) or "").strip()
                    if identity:
                        identity_locations[key + ":" + identity].add(split)
                        (source_groups if key == "source_group_sha256" else split_groups).add(identity)

                text, schema = render_record_text(row)
                tokens = _token_length(tokenizer, text)
                schema_tokens = _token_length(tokenizer, schema)
                token_total += tokens
                schema_token_total += schema_tokens
                token_lengths.append(tokens)

                digest = _content_hash(text)
                previous_split = global_text_hashes.get(digest)
                if previous_split and previous_split != split:
                    exact_hash_locations[digest].update({previous_split, split})
                elif previous_split == split:
                    duplicate_text_records.append({
                        "sha256": digest,
                        "split": split,
                        "record_id": record_id or f"{split}:{line_number}",
                    })
                else:
                    global_text_hashes[digest] = split

                domain = str(row.get("domain") or "unknown")
                source = str(row.get("source") or "unspecified")
                license_name = str(row.get("license") or "unspecified")
                evidence = str(row.get("evidence_level") or row.get("evidence") or "unspecified")
                split_domains[domain] += 1
                split_sources[source] += 1
                split_licenses[license_name] += 1
                domain_tokens[domain][split] += tokens
                source_tokens[source][split] += tokens
                license_counts[license_name] += 1
                evidence_counts[evidence] += 1

                for image_path in row.get("images") or []:
                    split_image_count += 1
                    image_total += 1
                    candidate = Path(str(image_path))
                    if not candidate.is_file():
                        missing_images.append({
                            "split": split,
                            "record_id": record_id or f"{split}:{line_number}",
                            "image": str(image_path),
                        })
                    else:
                        size = candidate.stat().st_size
                        split_image_bytes += size
                        image_bytes_total += size

        split_summaries[split] = {
            "records": record_count,
            "text_tokens": token_total,
            "tool_schema_tokens": schema_token_total,
            "mean_text_tokens_per_record": round(statistics.mean(token_lengths), 2) if token_lengths else 0,
            "p50_text_tokens_per_record": round(statistics.median(token_lengths), 2) if token_lengths else 0,
            "p90_text_tokens_per_record": round(_percentile(token_lengths, 0.90), 2) if token_lengths else 0,
            "max_text_tokens_per_record": max(token_lengths, default=0),
            "image_files": split_image_count,
            "image_bytes": split_image_bytes,
            "unique_source_groups": len(source_groups),
            "unique_split_groups": len(split_groups),
            "domains": dict(sorted(split_domains.items())),
            "sources": dict(sorted(split_sources.items())),
            "licenses": dict(sorted(split_licenses.items())),
        }

    if split_summaries.get("train", {}).get("records", 0) == 0:
        raise ValueError("Training split is empty.")
    if split_summaries.get("validation", {}).get("records", 0) == 0:
        raise ValueError("Validation split is empty.")
    if require_test and split_summaries.get("test", {}).get("records", 0) == 0:
        raise ValueError("Held-out test split is empty.")

    leakage = [
        {"identity": identity, "splits": sorted(splits)}
        for identity, splits in identity_locations.items()
        if len(splits) > 1
    ]
    content_leakage = [
        {"sha256": digest, "splits": sorted(splits)}
        for digest, splits in exact_hash_locations.items()
        if len(splits) > 1
    ]
    if leakage:
        raise ValueError("Cross-split source identity leakage detected: " + json.dumps(leakage[:12], ensure_ascii=False))
    if content_leakage:
        raise ValueError("Exact normalized text duplicates cross splits: " + json.dumps(content_leakage[:12], ensure_ascii=False))
    if duplicate_text_records:
        raise ValueError(
            "Exact normalized text duplicates within a split would inflate training exposure: "
            + json.dumps(duplicate_text_records[:12], ensure_ascii=False)
        )
    if duplicate_ids:
        raise ValueError("Duplicate record IDs found: " + json.dumps(duplicate_ids[:12]))

    return {
        "schema_version": 1,
        "status": "PASS",
        "tokenizer": getattr(tokenizer, "name_or_path", "provided-tokenizer"),
        "token_scope": "Text tokens only; image patch/vision tokens and runtime chat-template overhead are not included.",
        "train_text_tokens": split_summaries["train"]["text_tokens"],
        "validation_text_tokens": split_summaries["validation"]["text_tokens"],
        "held_out_test_text_tokens": split_summaries.get("test", {}).get("text_tokens", 0),
        "all_split_text_tokens": sum(x.get("text_tokens", 0) for x in split_summaries.values()),
        "tool_schema_tokens_total": sum(x.get("tool_schema_tokens", 0) for x in split_summaries.values()),
        "image_files_total": image_total,
        "image_bytes_total": image_bytes_total,
        "missing_image_files": missing_images,
        "cross_split_identity_leakage": 0,
        "cross_split_exact_text_leakage": 0,
        "duplicate_text_records_within_split": 0,
        "duplicate_record_ids": 0,
        "license_record_counts": dict(sorted(license_counts.items())),
        "evidence_level_record_counts": dict(sorted(evidence_counts.items())),
        "domains": {domain: dict(sorted(counts.items())) for domain, counts in sorted(domain_tokens.items())},
        "sources": {source: dict(sorted(counts.items())) for source, counts in sorted(source_tokens.items())},
        "splits": split_summaries,
        "limitations": [
            "Text-token counts exclude image patch embeddings and runtime-added chat-template overhead.",
            "Source dataset validation labels are provenance claims, not independent NextCAD/Next BIM validation.",
            "Record and token counts are not counts of mastered skills or verified native operations.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--tokenizer", default="Qwen/Qwen3.5-0.8B")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--allow-empty-test", action="store_true")
    args = parser.parse_args()
    if args.max_records < 0:
        parser.error("--max-records cannot be negative")
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install Transformers v5 to count tokens with the actual student tokenizer.") from exc
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)
    report = audit_corpus(
        args.data_dir, tokenizer, max_records=args.max_records,
        require_test=not args.allow_empty_test,
    )
    output = args.output or (args.data_dir / "corpus_audit.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
