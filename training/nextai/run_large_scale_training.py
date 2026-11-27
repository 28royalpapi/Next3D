#!/usr/bin/env python3
"""Run a reproducible NextAI GPU fine-tune, evaluations and optional Hub publication."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRAINING = Path(__file__).resolve().parent


def execute(command: list[str], log_path: Path, env: dict[str, str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = " ".join(command)
    print(f"\n$ {rendered}", flush=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n$ {rendered}\n")
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        code = process.wait()
        if code:
            raise subprocess.CalledProcessError(code, command)


def runtime_manifest(output_dir: Path, token_audit: dict[str, Any]) -> dict[str, Any]:
    import torch
    import transformers
    import trl

    try:
        import unsloth
        unsloth_version = getattr(unsloth, "__version__", "unknown")
    except Exception:
        unsloth_version = "import-failed"

    cuda = torch.cuda.is_available()
    gpu = None
    vram = None
    bf16 = False
    if cuda:
        props = torch.cuda.get_device_properties(0)
        gpu = torch.cuda.get_device_name(0)
        vram = round(props.total_memory / 1024**3, 2)
        bf16 = bool(torch.cuda.is_bf16_supported())

    result = {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "transformers": transformers.__version__,
        "trl": trl.__version__,
        "unsloth": unsloth_version,
        "cuda_available": cuda,
        "gpu_name": gpu,
        "gpu_vram_gib": vram,
        "bf16_supported": bf16,
        "token_audit": {
            "train_text_tokens": token_audit.get("train_text_tokens"),
            "validation_text_tokens": token_audit.get("validation_text_tokens"),
            "held_out_test_text_tokens": token_audit.get("held_out_test_text_tokens"),
            "image_files_total": token_audit.get("image_files_total"),
            "image_bytes_total": token_audit.get("image_bytes_total"),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "compute_manifest.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def publish_artifacts(output_dir: Path, repo_id: str, token: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="model", private=True, exist_ok=True)

    upload_map = [
        (output_dir / "adapter", "candidate/adapter"),
        (output_dir / "gguf_q4_k_m", "candidate/gguf_q4_k_m"),
    ]
    for folder, path_in_repo in upload_map:
        if folder.is_dir():
            api.upload_folder(
                folder_path=str(folder),
                repo_id=repo_id,
                repo_type="model",
                path_in_repo=path_in_repo,
                commit_message=f"Publish NextAI student artifacts: {path_in_repo}",
            )

    for filename in (
        "training_config.json",
        "training_result.json",
        "compute_manifest.json",
        "corpus_audit.json",
    ):
        path = output_dir / filename
        if path.is_file():
            api.upload_file(
                path_or_fileobj=str(path),
                path_in_repo=f"candidate/{filename}",
                repo_id=repo_id,
                repo_type="model",
                commit_message=f"Publish NextAI training evidence: {filename}",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-model", default="Qwen/Qwen3.5-0.8B")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--target-text-tokens", type=int, default=400_000_000)
    parser.add_argument("--resume-from-checkpoint", type=Path)
    parser.add_argument("--skip-baseline-evaluation", action="store_true")
    parser.add_argument("--skip-candidate-evaluation", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--model-repo", default="Justin75685/nextai-qwen35-engineering-student")
    parser.add_argument("--evaluation-max-records", type=int, default=0)
    args = parser.parse_args()

    if args.epochs <= 0 or args.max_seq_length < 256 or args.batch_size < 1:
        parser.error("epochs, sequence length and batch size are outside supported ranges.")
    if args.gradient_accumulation < 1 or args.lora_rank < 1 or args.target_text_tokens < 1:
        parser.error("gradient accumulation, LoRA rank and token target must be positive.")

    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not (data_dir / "train.jsonl").is_file():
        raise FileNotFoundError(f"Training corpus not found at {data_dir / 'train.jsonl'}")
    if not (data_dir / "validation.jsonl").is_file() or not (data_dir / "test.jsonl").is_file():
        raise FileNotFoundError("Training, validation and held-out test files are all required.")

    from transformers import AutoTokenizer
    from audit_nextai_corpus import audit_corpus

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    audit = audit_corpus(data_dir, tokenizer, require_test=True)
    audit_path = data_dir / "corpus_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "corpus_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    train_tokens = int(audit["train_text_tokens"])
    if train_tokens <= 0:
        raise ValueError("The measured training text-token count is zero.")
    token_target_met = train_tokens >= args.target_text_tokens
    print(
        f"Measured train text tokens: {train_tokens:,} / target {args.target_text_tokens:,}. "
        f"Target met: {token_target_met}.",
        flush=True,
    )
    print(
        "Image patch tokens and runtime chat-template overhead are not included in this "
        "text-token count. No data is repeated automatically to inflate the budget.",
        flush=True,
    )

    compute = runtime_manifest(output_dir, audit)
    if not compute["cuda_available"]:
        raise RuntimeError("A CUDA GPU is required. Refusing to fall back to CPU training.")

    env = os.environ.copy()
    log_path = output_dir / "training.log"
    test_file = data_dir / "test.jsonl"

    if not args.skip_baseline_evaluation:
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", args.base_model,
                "--test-jsonl", str(test_file),
                "--output", str(output_dir / "base_heldout_evaluation.json"),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path,
            env,
        )

    training_command = [
        sys.executable, str(TRAINING / "train_nextai.py"),
        "--data-dir", str(data_dir),
        "--output-dir", str(output_dir),
        "--base-model", args.base_model,
        "--max-steps", "-1",
        "--num-train-epochs", str(args.epochs),
        "--max-seq-length", str(args.max_seq_length),
        "--batch-size", str(args.batch_size),
        "--gradient-accumulation", str(args.gradient_accumulation),
        "--learning-rate", str(args.learning_rate),
        "--lora-rank", str(args.lora_rank),
        "--save-merged-model",
    ]
    if args.resume_from_checkpoint:
        training_command += ["--resume-from-checkpoint", str(args.resume_from_checkpoint.resolve())]
    execute(training_command, log_path, env)

    training_result_path = output_dir / "training_result.json"
    if not training_result_path.is_file():
        raise RuntimeError("Trainer exited without writing training_result.json.")
    training_result = json.loads(training_result_path.read_text(encoding="utf-8"))
    merged_model = training_result.get("merged_16bit_checkpoint")
    if not merged_model or not (Path(merged_model) / "config.json").is_file():
        raise RuntimeError("Merged student checkpoint was not produced or is incomplete.")

    if not args.skip_candidate_evaluation:
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", str(merged_model),
                "--test-jsonl", str(test_file),
                "--output", str(output_dir / "candidate_heldout_evaluation.json"),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path,
            env,
        )

    run_report = {
        "status": "TRAINED_AND_EVALUATED" if not args.skip_candidate_evaluation else "TRAINED_EVALUATION_PENDING",
        "base_model": args.base_model,
        "training_epochs": args.epochs,
        "max_sequence_length": args.max_seq_length,
        "target_train_text_tokens": args.target_text_tokens,
        "measured_train_text_tokens": train_tokens,
        "token_target_met": token_target_met,
        "compute_manifest": str(output_dir / "compute_manifest.json"),
        "corpus_audit": str(output_dir / "corpus_audit.json"),
        "training_result": str(training_result_path),
        "base_evaluation": None if args.skip_baseline_evaluation else str(output_dir / "base_heldout_evaluation.json"),
        "candidate_evaluation": None if args.skip_candidate_evaluation else str(output_dir / "candidate_heldout_evaluation.json"),
        "native_application_acceptance": "PENDING",
        "package_size_acceptance": "PENDING",
        "note": "Fine-tuning and held-out model evaluation do not prove native CAD/BIM operations or professional engineering approval.",
    }
    report_path = output_dir / "large_scale_run_report.json"
    report_path.write_text(json.dumps(run_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not args.skip_upload:
        token = env.get("HF_TOKEN", "").strip()
        if not token:
            raise RuntimeError("HF_TOKEN is required to publish the adapter, GGUF and evidence to the private model repository.")
        publish_artifacts(output_dir, args.model_repo, token)
        run_report["hub_upload"] = "completed"
    else:
        run_report["hub_upload"] = "skipped"
    report_path.write_text(json.dumps(run_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run_report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
