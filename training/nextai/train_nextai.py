#!/usr/bin/env python3
"""BF16 LoRA SFT trainer for the single Qwen3.5-0.8B NextAI student."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sqlite3
import tempfile
from array import array
from pathlib import Path
from typing import Any, Iterable


class IndexedJSONL:
    """Random-access JSONL dataset backed by a compact byte-offset index.

    Records are parsed on demand. The full corpus is never materialized as a
    Python list, which keeps memory use predictable for million-record training.
    Each worker process lazily owns its own file handle.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        self.offsets = array("Q")
        with self.path.open("rb") as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                if line.strip():
                    self.offsets.append(offset)
        self._handle = None
        self._pid = None

    def __len__(self) -> int:
        return len(self.offsets)

    def __getitem__(self, index: int) -> dict[str, Any]:
        if index < 0:
            index += len(self.offsets)
        if index < 0 or index >= len(self.offsets):
            raise IndexError(index)
        pid = os.getpid()
        if self._handle is None or self._pid != pid:
            self.close()
            self._handle = self.path.open("rb")
            self._pid = pid
        self._handle.seek(self.offsets[index])
        line = self._handle.readline()
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{self.path} record {index} is not a JSON object.")
        return row

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
        self._handle = None
        self._pid = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_handle"] = None
        state["_pid"] = None
        return state

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def validate_training_splits(
    train_rows: Iterable[dict[str, Any]],
    validation_rows: Iterable[dict[str, Any]],
    test_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Fail closed on invalid records, duplicate IDs and cross-split leakage.

    Identity indexes are held in a temporary SQLite file, not large Python sets.
    This keeps validation memory bounded when the corpus grows to hundreds of
    thousands or millions of records.
    """
    splits = {
        "train": train_rows,
        "validation": validation_rows,
        "test": test_rows,
    }
    summaries = {}
    with tempfile.TemporaryDirectory(prefix="nextai-integrity-") as temp_dir:
        db_path = Path(temp_dir) / "identities.sqlite3"
        connection = sqlite3.connect(str(db_path))
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute("PRAGMA temp_store=FILE")
            connection.execute("PRAGMA cache_size=-16384")
            connection.execute(
                "CREATE TABLE identities ("
                "identity TEXT NOT NULL, split TEXT NOT NULL, "
                "PRIMARY KEY (identity, split)) WITHOUT ROWID"
            )
            connection.execute(
                "CREATE TABLE record_ids ("
                "record_id TEXT NOT NULL, split TEXT NOT NULL, "
                "PRIMARY KEY (record_id, split)) WITHOUT ROWID"
            )
            connection.execute(
                "CREATE TABLE group_ids ("
                "group_type TEXT NOT NULL, group_id TEXT NOT NULL, split TEXT NOT NULL, "
                "PRIMARY KEY (group_type, group_id, split)) WITHOUT ROWID"
            )

            for split_name, rows in splits.items():
                record_count = 0
                image_count = 0
                domains: set[str] = set()

                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        raise ValueError(f"{split_name}[{index}] is not a JSON object.")
                    record_count += 1
                    record_id = str(row.get("record_id") or "").strip()
                    if record_id:
                        cursor = connection.execute(
                            "INSERT OR IGNORE INTO record_ids(record_id, split) VALUES (?, ?)",
                            (record_id, split_name),
                        )
                        if cursor.rowcount == 0:
                            raise ValueError(
                                f"Duplicate record_id {record_id!r} within {split_name}."
                            )
                        connection.execute(
                            "INSERT OR IGNORE INTO identities(identity, split) VALUES (?, ?)",
                            ("record_id:" + record_id, split_name),
                        )

                    for key, group_type in (
                        ("split_group", "split_group"),
                        ("source_group_sha256", "source_group_sha256"),
                    ):
                        value = str(row.get(key) or "").strip()
                        if value:
                            connection.execute(
                                "INSERT OR IGNORE INTO group_ids(group_type, group_id, split) "
                                "VALUES (?, ?, ?)",
                                (group_type, value, split_name),
                            )
                            connection.execute(
                                "INSERT OR IGNORE INTO identities(identity, split) VALUES (?, ?)",
                                (key + ":" + value, split_name),
                            )

                    domains.add(str(row.get("domain") or "unknown"))
                    messages = row.get("messages")
                    if isinstance(messages, list):
                        roles = {
                            message.get("role")
                            for message in messages
                            if isinstance(message, dict)
                        }
                        if "user" not in roles or "assistant" not in roles:
                            raise ValueError(
                                f"{split_name} record {record_id or index!r} must contain user and assistant messages."
                            )
                        last_assistant = next(
                            (
                                message for message in reversed(messages)
                                if isinstance(message, dict) and message.get("role") == "assistant"
                            ),
                            None,
                        )
                        assistant_content = (last_assistant or {}).get("content")
                        has_text = (
                            isinstance(assistant_content, str) and bool(assistant_content.strip())
                        ) or (
                            isinstance(assistant_content, list)
                            and any(
                                isinstance(part, dict)
                                and part.get("type") in {"text", "tool_call"}
                                and (part.get("text") or part.get("tool_call"))
                                for part in assistant_content
                            )
                        ) or bool((last_assistant or {}).get("tool_calls"))
                        if not has_text:
                            raise ValueError(
                                f"{split_name} record {record_id or index!r} has no assistant target."
                            )
                        conversation_row_for_collator(row)
                    else:
                        prompt = str(row.get("prompt") or "").strip()
                        completion = str(row.get("completion") or "").strip()
                        if not prompt or not completion:
                            raise ValueError(
                                f"{split_name} record {record_id or index!r} needs non-empty prompt and completion."
                            )

                    for image_path in row.get("images") or []:
                        if not Path(image_path).is_file():
                            raise FileNotFoundError(
                                f"{split_name} record {record_id or index!r} references missing image: {image_path}"
                            )
                        image_count += 1

                connection.commit()
                unique_record_ids = connection.execute(
                    "SELECT COUNT(*) FROM record_ids WHERE split = ?",
                    (split_name,),
                ).fetchone()[0]
                split_group_count = connection.execute(
                    "SELECT COUNT(*) FROM group_ids WHERE split = ? AND group_type = 'split_group'",
                    (split_name,),
                ).fetchone()[0]
                source_group_count = connection.execute(
                    "SELECT COUNT(*) FROM group_ids WHERE split = ? AND group_type = 'source_group_sha256'",
                    (split_name,),
                ).fetchone()[0]
                summaries[split_name] = {
                    "records": record_count,
                    "unique_record_ids": unique_record_ids,
                    "split_groups": split_group_count,
                    "source_groups": source_group_count,
                    "image_files": image_count,
                    "domains": sorted(domains),
                }

            conflicts = connection.execute(
                "SELECT identity, GROUP_CONCAT(split) AS splits "
                "FROM identities GROUP BY identity HAVING COUNT(*) > 1 LIMIT 8"
            ).fetchall()
            if conflicts:
                sample = [
                    {"identity": identity, "splits": sorted(str(splits_value).split(","))}
                    for identity, splits_value in conflicts
                ]
                raise ValueError(
                    "Data leakage detected: record IDs or source/split groups occur in more than one split: "
                    + json.dumps(sample, ensure_ascii=False)
                )
        finally:
            connection.close()

    return {
        "status": "PASS",
        "cross_split_identity_conflicts": 0,
        "identity_index_storage": "temporary_disk_backed_sqlite",
        "splits": summaries,
        "test_used_for_gradient_updates": False,
    }



CURRICULUM_STAGE_ORDER = (
    "foundations",
    "cad_bim_fluency",
    "engineering_disciplines",
    "operator_methods",
    "integrated_projects",
)


def curriculum_stage_for_record(row: dict[str, Any]) -> str:
    """Map a record to the progressive engineering learning stage."""
    explicit = str(row.get("curriculum_stage") or "").strip()
    if explicit in CURRICULUM_STAGE_ORDER:
        return explicit

    domain = str(row.get("domain") or "unknown").strip().lower()
    foundation_prefixes = (
        "engineering_statics_",
        "engineering_structural_axial_",
        "engineering_mechanical_torsion",
        "engineering_hydraulics_",
        "engineering_geotechnical_",
        "engineering_mechanical_gear_ratio",
        "engineering_electrical_",
        "engineering_surveying_",
        "engineering_structural_section_",
        "engineering_beam_reactions_",
        "engineering_fem_axial_",
        "engineering_pipe_continuity_",
        "civil_earthwork_",
        "construction_concrete_quantity",
        "construction_reinforcement_mass",
    )
    if domain.startswith(foundation_prefixes):
        return "foundations"

    if domain.startswith(("cad_", "bim_", "ifc_")) or domain in {
        "swiss_dwellings_floorplan",
        "ifc_model_summary",
        "ifc_element_inventory",
    }:
        return "cad_bim_fluency"

    if domain in {"nextcad_native", "nextbim_native"}:
        return "integrated_projects"
    if domain.startswith(("design_execution_", "bim_execution_")):
        return "integrated_projects"

    if domain in {"nextcad_capability_knowledge", "nextbim_capability_knowledge"}:
        return "operator_methods"
    if domain == "engineering_skill_knowledge" or domain.startswith("design_intake_"):
        return "operator_methods"

    if domain.startswith(("engineering_", "civil_", "construction_")):
        return "engineering_disciplines"

    return "engineering_disciplines"


def build_progressive_curriculum_order(
    rows: Iterable[dict[str, Any]],
    *,
    seed: int = 3407,
    replay_fraction: float = 0.10,
    replay_chunk_size: int = 32,
) -> tuple[list[int], dict[str, Any]]:
    """Order one epoch as a progressive course with spaced rehearsal.

    Every unique record is used once in its assigned stage. At each later stage,
    a small random sample of earlier stages is inserted after each new-data chunk.
    This introduces spaced rehearsal without materializing record contents.
    """
    if not 0.0 <= replay_fraction <= 0.5:
        raise ValueError("replay_fraction must be between 0 and 0.5.")
    if replay_chunk_size < 1:
        raise ValueError("replay_chunk_size must be positive.")

    stage_indices: dict[str, list[int]] = {
        stage: [] for stage in CURRICULUM_STAGE_ORDER
    }
    domain_counts: dict[str, dict[str, int]] = {
        stage: {} for stage in CURRICULUM_STAGE_ORDER
    }
    record_fingerprint = hashlib.sha256()
    for index, row in enumerate(rows):
        stage = curriculum_stage_for_record(row)
        stage_indices[stage].append(index)
        domain = str(row.get("domain") or "unknown")
        domain_counts[stage][domain] = domain_counts[stage].get(domain, 0) + 1
        # Hash the full canonical JSON record so a resumed checkpoint cannot
        # silently attach to a changed corpus with the same number of rows.
        canonical_record = json.dumps(
            row, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        record_fingerprint.update(canonical_record.encode("utf-8"))
        record_fingerprint.update(b"\n")

    rng = random.Random(seed)
    for stage_index, stage in enumerate(CURRICULUM_STAGE_ORDER):
        random.Random(seed + 1009 * (stage_index + 1)).shuffle(stage_indices[stage])

    ordered_indices: list[int] = []
    prior_indices: list[int] = []
    unique_row_count = len(rows)  # IndexedJSONL exposes an inexpensive constant-time length.
    stage_reports: dict[str, Any] = {}
    replay_total = 0

    for stage in CURRICULUM_STAGE_ORDER:
        current = stage_indices[stage]
        stage_start = len(ordered_indices)
        replay_count = 0

        for offset in range(0, len(current), replay_chunk_size):
            chunk = current[offset:offset + replay_chunk_size]
            ordered_indices.extend(chunk)
            if prior_indices and replay_fraction > 0 and chunk:
                replay_size = max(1, int(round(len(chunk) * replay_fraction)))
                replay = [rng.choice(prior_indices) for _ in range(replay_size)]
                ordered_indices.extend(replay)
                replay_count += len(replay)

        replay_total += replay_count
        stage_reports[stage] = {
            "unique_records": len(current),
            "replay_records_inserted_after_stage_chunks": replay_count,
            "ordered_positions_added": len(ordered_indices) - stage_start,
            "domain_counts": dict(sorted(domain_counts[stage].items())),
        }
        prior_indices.extend(current)

    assigned_record_count = sum(len(stage_indices[stage]) for stage in CURRICULUM_STAGE_ORDER)
    if assigned_record_count != unique_row_count:
        raise RuntimeError(
            f"Progressive curriculum assigned {assigned_record_count} of {unique_row_count} records."
        )
    if len(ordered_indices) < unique_row_count:
        raise RuntimeError("Progressive curriculum ordering dropped one or more training records.")

    order_digest = hashlib.sha256()
    for index in ordered_indices:
        order_digest.update(str(index).encode("ascii"))
        order_digest.update(b",")

    manifest = {
        "schedule_version": 1,
        "stage_order": list(CURRICULUM_STAGE_ORDER),
        "stages": stage_reports,
        "unique_training_records": len(rows),
        "training_records_sha256": record_fingerprint.hexdigest(),
        "ordered_training_exposures": len(ordered_indices),
        "spaced_replay_exposures": replay_total,
        "replay_fraction_per_chunk": replay_fraction,
        "replay_chunk_size": replay_chunk_size,
        "sampler": "sequential",
        "seed": seed,
        "ordered_index_sha256": order_digest.hexdigest(),
        "method": "Progressive stage blocks with deterministic spaced rehearsal of prior stages",
    }
    return ordered_indices, manifest

def conversation_row_for_collator(
    row: dict[str, Any],
    image_loader=None,
) -> dict[str, Any]:
    """Preserve tool schemas and attach real image assets when a message record has them."""
    messages = row.get("messages")
    if not isinstance(messages, list):
        raise ValueError("A conversational training record must contain a messages list.")
    normalized = []
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            raise ValueError("Each conversational message needs a role.")
        item = dict(message)
        if isinstance(item.get("content"), str):
            item["content"] = [{"type": "text", "text": item["content"]}]
        normalized.append(item)

    image_paths = [str(path) for path in (row.get("images") or [])]
    if image_paths and image_loader is not None:
        user_index = next(
            (index for index, message in enumerate(normalized) if message["role"] == "user"),
            None,
        )
        if user_index is None:
            raise ValueError("A multimodal conversational record must contain a user message.")
        user_message = normalized[user_index]
        content = user_message.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if not isinstance(content, list):
            raise ValueError("A multimodal user message must have string or list content.")

        loaded_images = [
            {"type": "image", "image": image_loader(path)}
            for path in image_paths
        ]
        rebuilt = []
        image_index = 0
        placeholder_count = 0
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image":
                placeholder_count += 1
                if image_index >= len(loaded_images):
                    raise ValueError("The message contains more image placeholders than image assets.")
                rebuilt.append(loaded_images[image_index])
                image_index += 1
            else:
                rebuilt.append(part)
        if placeholder_count == 0:
            rebuilt = loaded_images + rebuilt
        elif image_index < len(loaded_images):
            rebuilt = loaded_images[image_index:] + rebuilt
        user_message["content"] = rebuilt

    result = {"messages": normalized}
    template_kwargs = dict(row.get("chat_template_kwargs") or {})
    tools = row.get("tools")
    if tools is not None:
        if not isinstance(tools, list) or not tools:
            raise ValueError("The tools field must be a non-empty function-schema list.")
        template_kwargs["tools"] = tools
    if template_kwargs:
        result["chat_template_kwargs"] = template_kwargs
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-model", default="Qwen/Qwen3.5-0.8B")
    parser.add_argument("--max-steps", type=int, default=-1,
                        help="Set -1 to train for complete epochs; a positive value runs a bounded smoke/debug pass.")
    parser.add_argument("--num-train-epochs", type=float, default=1.0)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--curriculum-replay-fraction", type=float, default=0.10)
    parser.add_argument("--curriculum-replay-chunk-size", type=int, default=32)
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument(
        "--resume-from-checkpoint", type=Path,
        help="Resume the same training run from a Trainer checkpoint directory.",
    )
    parser.add_argument("--save-merged-model", action="store_true",
                        help="Save a temporary merged 16-bit checkpoint for vision-projector Q8 export.")
    args = parser.parse_args()

    if args.max_steps == 0 or args.max_steps < -1 or args.num_train_epochs <= 0:
        parser.error("max-steps must be -1 or positive, and epochs must be positive")
    if args.batch_size < 1 or args.gradient_accumulation < 1:
        parser.error("batch size and gradient accumulation must be positive")

    train_rows = IndexedJSONL(args.data_dir / "train.jsonl")
    validation_rows = IndexedJSONL(args.data_dir / "validation.jsonl")
    test_path = args.data_dir / "test.jsonl"
    test_rows = IndexedJSONL(test_path) if test_path.is_file() else []
    if not train_rows or not validation_rows:
        raise RuntimeError("Training and validation JSONL must both be non-empty.")
    integrity = validate_training_splits(train_rows, validation_rows, test_rows)
    print("NEXTAI DATA INTEGRITY PASS: " + json.dumps(integrity, ensure_ascii=False))
    training_indices, curriculum_manifest = build_progressive_curriculum_order(
        train_rows,
        seed=args.seed,
        replay_fraction=args.curriculum_replay_fraction,
        replay_chunk_size=args.curriculum_replay_chunk_size,
    )
    print("NEXTAI PROGRESSIVE CURRICULUM: " + json.dumps(curriculum_manifest, ensure_ascii=False))

    # Fail before downloading the model if no CUDA device is available.
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU not available. BF16 LoRA must run in an authorised GPU "
            "environment; no CPU fallback or QLoRA substitution is attempted."
        )

    from PIL import Image
    from unsloth import FastVisionModel
    from unsloth.trainer import UnslothVisionDataCollator
    from trl import SFTConfig, SFTTrainer
    from torch.utils.data import Dataset

    class ConversationDataset(Dataset):
        def __init__(self, rows, indices=None):
            self.rows = rows
            self.indices = indices

        def __len__(self):
            return len(self.indices) if self.indices is not None else len(self.rows)

        def __getitem__(self, index):
            row_index = self.indices[index] if self.indices is not None else index
            row = self.rows[row_index]
            if isinstance(row.get("messages"), list):
                def load_image(path):
                    with Image.open(path) as image:
                        return image.convert("RGB").copy()
                return conversation_row_for_collator(
                    row,
                    image_loader=load_image if row.get("images") else None,
                )
            content = []
            for image_path in row.get("images") or []:
                with Image.open(image_path) as image:
                    content.append({"type": "image", "image": image.convert("RGB").copy()})
            prompt = str(row.get("prompt") or "")
            completion = str(row.get("completion") or "")
            if content:
                content.append({"type": "text", "text": prompt})
                user_content = content
            else:
                user_content = prompt
            messages = []
            system = str(row.get("system") or "")
            if system:
                messages.append({"role": "system", "content": system})
            messages.extend([
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": [{"type": "text", "text": completion}]},
            ])
            return {"messages": messages}

    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=False,
        use_gradient_checkpointing="unsloth",
    )
    model = FastVisionModel.get_peft_model(
        model,
        # CAD is visual as well as parametric. Adapt the vision pathway with
        # LoRA too, while preserving the frozen base weights and compact export.
        finetune_vision_layers=True,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=args.lora_rank,
        lora_alpha=args.lora_rank,
        lora_dropout=0,
        bias="none",
        random_state=args.seed,
        use_rslora=False,
    )
    FastVisionModel.for_training(model)

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    use_bf16 = bool(torch.cuda.is_bf16_supported())
    run_config = {
        "base_model": args.base_model,
        "method": "BF16 LoRA supervised fine-tuning",
        "max_steps": args.max_steps,
        "num_train_epochs": args.num_train_epochs,
        "max_seq_length": args.max_seq_length,
        "resume_from_checkpoint": str(args.resume_from_checkpoint) if args.resume_from_checkpoint else None,
        "batch_size": args.batch_size,
        "gradient_accumulation": args.gradient_accumulation,
        "effective_batch_size": args.batch_size * args.gradient_accumulation,
        "learning_rate": args.learning_rate,
        "lora_rank": args.lora_rank,
        "precision": "bf16" if use_bf16 else "fp16",
        "seed": args.seed,
        "curriculum_schedule": curriculum_manifest,
        "unique_training_records": len(train_rows),
        "ordered_training_exposures": len(training_indices),
        "spaced_replay_exposures": curriculum_manifest["spaced_replay_exposures"],
        "train_sampling_strategy": "sequential",
        "data_integrity": integrity,
        "data_loading_strategy": "Indexed JSONL byte offsets with on-demand record parsing",
        "training_record_count": len(train_rows),
        "validation_record_count": len(validation_rows),
        "held_out_test_record_count": len(test_rows),
        "test_set_used_for_training": False,
    }
    (output / "curriculum_schedule.json").write_text(
        json.dumps(curriculum_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "training_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    config = SFTConfig(
        output_dir=str(output / "checkpoints"),
        max_length=args.max_seq_length,
        max_steps=args.max_steps,
        num_train_epochs=args.num_train_epochs,
        bf16=use_bf16,
        fp16=not use_bf16,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        warmup_steps=20,
        logging_steps=10,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=args.seed,
        train_sampling_strategy="sequential",
        shuffle_dataset=False,
        report_to="none",
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
        train_dataset=ConversationDataset(train_rows, indices=training_indices),
        eval_dataset=ConversationDataset(validation_rows),
        args=config,
    )
    if args.resume_from_checkpoint is not None and not args.resume_from_checkpoint.is_dir():
        raise FileNotFoundError(
            f"Resume checkpoint directory does not exist: {args.resume_from_checkpoint}"
        )
    train_metrics = trainer.train(
        resume_from_checkpoint=(
            str(args.resume_from_checkpoint) if args.resume_from_checkpoint else None
        )
    )
    eval_metrics = trainer.evaluate()

    # Domain-level generative evaluation runs once after training, in the
    # orchestration stage. Do not run a second full validation pass for every
    # domain from inside the trainer.
    validation_by_domain = {
        "status": "PENDING_POST_TRAINING_EVALUATION",
        "domains": integrity["splits"]["validation"]["domains"],
    }
    # Do not inspect held-out test outputs during fine-tuning. The independent
    # base-versus-candidate test comparison is run only after the candidate is
    # fully trained, using the separate post-training evaluation orchestrator.
    test_by_domain = {
        "status": "PENDING_POST_TRAINING",
        "records": len(test_rows),
        "evaluated_during_training": False,
    }

    adapter_dir = output / "adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    merged_dir = None
    if args.save_merged_model:
        merged_dir = output / "merged_16bit"
        model.save_pretrained_merged(
            str(merged_dir), tokenizer, save_method="merged_16bit"
        )

    result = {
        "base_model": args.base_model,
        "method": "BF16 LoRA SFT",
        "vision_encoder_weights_frozen": False,
        "vision_encoder_lora_adapted": True,
        "language_layers_trainable": True,
        "train_records": len(train_rows),
        "training_exposures": len(training_indices),
        "spaced_replay_exposures": curriculum_manifest["spaced_replay_exposures"],
        "curriculum_schedule": str(output / "curriculum_schedule.json"),
        "validation_records": len(validation_rows),
        "held_out_test_records": len(test_rows),
        "data_integrity": integrity,
        "training_config": str(output / "training_config.json"),
        "max_steps": args.max_steps,
        "num_train_epochs": args.num_train_epochs,
        "precision": "bf16" if use_bf16 else "fp16",
        "max_seq_length": args.max_seq_length,
        "lora_rank": args.lora_rank,
        "training_metrics": train_metrics.metrics,
        "evaluation_metrics": eval_metrics,
        "validation_metrics_by_domain": validation_by_domain,
        "held_out_test_metrics_by_domain": test_by_domain,
        "test_set_used_for_training": False,
        "adapter": str(adapter_dir),
        "merged_16bit_checkpoint": str(merged_dir) if merged_dir else None,
        "gguf_export": "pending",
        "native_engine_benchmark": "pending",
        "package_size_validation": "pending",
    }
    (output / "training_result.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
    )
    if not args.skip_gguf:
        gguf_dir = output / "gguf_q4_k_m"
        model.save_pretrained_gguf(
            str(gguf_dir), tokenizer, quantization_method="q4_k_m"
        )
        result["gguf_export"] = str(gguf_dir)
        gguf_files = []
        for file_path in sorted(gguf_dir.rglob("*.gguf")):
            digest = hashlib.sha256()
            with file_path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            gguf_files.append({
                "file": str(file_path.relative_to(gguf_dir)),
                "size_bytes": file_path.stat().st_size,
                "sha256": digest.hexdigest(),
            })
        result["gguf_files"] = gguf_files
        result["gguf_total_bytes"] = sum(item["size_bytes"] for item in gguf_files)
        (output / "training_result.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
