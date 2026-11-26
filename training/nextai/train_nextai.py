#!/usr/bin/env python3
"""BF16 LoRA SFT trainer for the single Qwen3.5-0.8B NextAI student."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def validate_training_splits(
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fail closed on empty references, duplicate IDs and cross-split leakage."""
    splits = {
        "train": train_rows,
        "validation": validation_rows,
        "test": test_rows,
    }
    identities: dict[str, dict[str, str]] = {}
    summaries = {}
    for split_name, rows in splits.items():
        seen_ids = set()
        source_groups = set()
        split_groups = set()
        image_count = 0
        domains = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"{split_name}[{index}] is not a JSON object.")
            record_id = str(row.get("record_id") or "").strip()
            if record_id:
                if record_id in seen_ids:
                    raise ValueError(f"Duplicate record_id {record_id!r} within {split_name}.")
                seen_ids.add(record_id)
                identities.setdefault("record_id:" + record_id, {})[split_name] = record_id

            for key, registry in (
                ("split_group", split_groups),
                ("source_group_sha256", source_groups),
            ):
                value = str(row.get(key) or "").strip()
                if value:
                    registry.add(value)
                    identities.setdefault(key + ":" + value, {})[split_name] = value

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
                        isinstance(part, dict) and part.get("type") in {"text", "tool_call"}
                        and (part.get("text") or part.get("tool_call"))
                        for part in assistant_content
                    )
                ) or bool((last_assistant or {}).get("tool_calls"))
                if not has_text:
                    raise ValueError(f"{split_name} record {record_id or index!r} has no assistant target.")
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
        summaries[split_name] = {
            "records": len(rows),
            "unique_record_ids": len(seen_ids),
            "split_groups": len(split_groups),
            "source_groups": len(source_groups),
            "image_files": image_count,
            "domains": sorted(domains),
        }

    conflicts = []
    for identity, appearances in identities.items():
        if len(appearances) > 1:
            conflicts.append({"identity": identity, "splits": sorted(appearances)})
    if conflicts:
        sample = conflicts[:8]
        raise ValueError(
            "Data leakage detected: record IDs or source/split groups occur in more than one split: "
            + json.dumps(sample, ensure_ascii=False)
        )
    return {
        "status": "PASS",
        "cross_split_identity_conflicts": 0,
        "splits": summaries,
        "test_used_for_gradient_updates": False,
    }


def conversation_row_for_collator(row: dict[str, Any]) -> dict[str, Any]:
    """Preserve Qwen tool-call messages and pass per-example tool schemas to its chat template."""
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
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument("--save-merged-model", action="store_true",
                        help="Save a temporary merged 16-bit checkpoint for vision-projector Q8 export.")
    args = parser.parse_args()

    if args.max_steps == 0 or args.max_steps < -1 or args.num_train_epochs <= 0:
        parser.error("max-steps must be -1 or positive, and epochs must be positive")
    if args.batch_size < 1 or args.gradient_accumulation < 1:
        parser.error("batch size and gradient accumulation must be positive")

    train_rows = read_jsonl(args.data_dir / "train.jsonl")
    validation_rows = read_jsonl(args.data_dir / "validation.jsonl")
    test_path = args.data_dir / "test.jsonl"
    test_rows = read_jsonl(test_path) if test_path.is_file() else []
    if not train_rows or not validation_rows:
        raise RuntimeError("Training and validation JSONL must both be non-empty.")
    integrity = validate_training_splits(train_rows, validation_rows, test_rows)
    print("NEXTAI DATA INTEGRITY PASS: " + json.dumps(integrity, ensure_ascii=False))

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
        def __init__(self, rows):
            self.rows = rows

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            row = self.rows[index]
            if isinstance(row.get("messages"), list):
                return conversation_row_for_collator(row)
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

    for row in train_rows + validation_rows:
        for image_path in row.get("images") or []:
            if not Path(image_path).is_file():
                raise FileNotFoundError(f"Training image is missing: {image_path}")

    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=args.base_model,
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
        random_state=3407,
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
        "batch_size": args.batch_size,
        "gradient_accumulation": args.gradient_accumulation,
        "effective_batch_size": args.batch_size * args.gradient_accumulation,
        "learning_rate": args.learning_rate,
        "lora_rank": args.lora_rank,
        "precision": "bf16" if use_bf16 else "fp16",
        "seed": 3407,
        "data_integrity": integrity,
        "training_record_count": len(train_rows),
        "validation_record_count": len(validation_rows),
        "held_out_test_record_count": len(test_rows),
        "test_set_used_for_training": False,
    }
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
        seed=3407,
        report_to="none",
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
        train_dataset=ConversationDataset(train_rows),
        eval_dataset=ConversationDataset(validation_rows),
        args=config,
    )
    train_metrics = trainer.train()
    eval_metrics = trainer.evaluate()

    def evaluate_by_domain(rows, prefix):
        grouped = {}
        domains = sorted({str(row.get("domain") or "unknown") for row in rows})
        for domain in domains:
            subset = [row for row in rows if str(row.get("domain") or "unknown") == domain]
            if not subset:
                continue
            metrics = trainer.evaluate(
                eval_dataset=ConversationDataset(subset),
                metric_key_prefix=f"{prefix}_{domain}",
            )
            grouped[domain] = metrics
        return grouped

    validation_by_domain = evaluate_by_domain(validation_rows, "validation")
    test_by_domain = evaluate_by_domain(test_rows, "test") if test_rows else {}

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
