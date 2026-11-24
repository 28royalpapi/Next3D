#!/usr/bin/env python3
"""BF16 LoRA SFT trainer for the single Qwen3.5-0.8B NextAI student."""
from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-model", default="Qwen/Qwen3.5-0.8B")
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--skip-gguf", action="store_true")
    args = parser.parse_args()

    if args.max_steps < 1 or args.batch_size < 1 or args.gradient_accumulation < 1:
        parser.error("steps and batch sizes must be positive")

    train_rows = read_jsonl(args.data_dir / "train.jsonl")
    validation_rows = read_jsonl(args.data_dir / "validation.jsonl")
    test_path = args.data_dir / "test.jsonl"
    test_rows = read_jsonl(test_path) if test_path.is_file() else []
    if not train_rows or not validation_rows:
        raise RuntimeError("Training and validation JSONL must both be non-empty.")

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
                return {"messages": row["messages"]}
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
                {"role": "assistant", "content": completion},
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
        finetune_vision_layers=False,
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
    config = SFTConfig(
        output_dir=str(output / "checkpoints"),
        max_length=args.max_seq_length,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        max_steps=args.max_steps,
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

    result = {
        "base_model": args.base_model,
        "method": "BF16 LoRA SFT",
        "vision_encoder_weights_frozen": True,
        "language_layers_trainable": True,
        "train_records": len(train_rows),
        "validation_records": len(validation_rows),
        "max_steps": args.max_steps,
        "max_seq_length": args.max_seq_length,
        "lora_rank": args.lora_rank,
        "training_metrics": train_metrics.metrics,
        "evaluation_metrics": eval_metrics,
        "validation_metrics_by_domain": validation_by_domain,
        "held_out_test_metrics_by_domain": test_by_domain,
        "test_set_used_for_training": False,
        "adapter": str(adapter_dir),
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
        (output / "training_result.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
