#!/usr/bin/env python3
"""Validate, fingerprint and split the public BuildEng V8 chat corpus.

The upstream dataset publishes one train split. This module creates deterministic
internal train/validation/test partitions, grouping identical normalized user
briefs so repeated variants cannot straddle splits. The resulting examples stay
labelled as authored L0 material, not native CAD/BIM execution traces.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SOURCE_REPO = "Irfanuruchi/buildeng"
SOURCE_URL = "https://huggingface.co/datasets/Irfanuruchi/buildeng"
SOURCE_LICENSE = "Apache-2.0"
DOMAIN = "engineering_buildeng_reasoning"


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s.+/%-]", "", value)
    return value.strip()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_buildeng_record(row: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert one source row to NextAI's multimodal SFT record contract."""
    raw_messages = row.get("messages")
    if not isinstance(raw_messages, list) or len(raw_messages) < 3:
        raise ValueError("BuildEng record must contain at least three chat messages.")

    messages: list[dict[str, str]] = []
    for message in raw_messages:
        if not isinstance(message, dict):
            raise ValueError("BuildEng chat message is not an object.")
        role = str(message.get("role") or "").strip().lower()
        content = message.get("content")
        if role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unsupported BuildEng message role: {role!r}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"BuildEng {role} message has empty/non-text content.")
        messages.append({"role": role, "content": content.strip()})

    roles = [message["role"] for message in messages]
    if "user" not in roles or "assistant" not in roles or roles[-1] != "assistant":
        raise ValueError("BuildEng conversation must contain a user turn and end with an assistant turn.")

    user_text = "\n".join(
        message["content"] for message in messages if message["role"] == "user"
    )
    assistant_text = "\n".join(
        message["content"] for message in messages if message["role"] == "assistant"
    )
    if len(normalize_text(assistant_text)) < 16:
        raise ValueError("BuildEng assistant response is too short to admit.")

    category = str(row.get("category") or "uncategorized").strip()
    tags = row.get("tags") or []
    if not isinstance(tags, list):
        raise ValueError("BuildEng tags must be a list.")
    tags = sorted({str(tag).strip() for tag in tags if str(tag).strip()})
    normalized_user = normalize_text(user_text)
    if not normalized_user:
        raise ValueError("BuildEng user request is empty after normalization.")

    # Identical requests in the same source category always stay in one split.
    group_sha = _digest(f"{category.lower()}|{normalized_user}")
    bucket = int(group_sha[:8], 16) % 100
    split = "test" if bucket < 5 else "validation" if bucket < 10 else "train"

    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record_sha = _digest(canonical)
    return {
        "record_id": f"buildeng-{record_sha[:24]}",
        "domain": DOMAIN,
        "messages": messages,
        "images": [],
        "source": SOURCE_REPO,
        "source_url": SOURCE_URL,
        "license": SOURCE_LICENSE,
        "source_validation_claim": "publisher_described_validated",
        "source_split": "train",
        "split": split,
        "source_category": category,
        "source_tags": tags,
        "source_group_sha256": group_sha,
        "split_group": group_sha,
        "source_record_index": int(index),
        "evidence_level": "L0",
        "native_execution_verified": False,
        "training_use_note": (
            "Publisher-described civil/structural reasoning and safety-behaviour example. "
            "Not an independently verified NextCAD/Next BIM command trace or design approval."
        ),
    }
