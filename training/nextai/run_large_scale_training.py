#!/usr/bin/env python3
"""Run a reproducible NextAI GPU fine-tune, multimodal export and examinations.

This runner never rents compute. It must be invoked inside an already authorised
GPU runtime (for example, a Hugging Face Job). It refuses CPU fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRAINING = Path(__file__).resolve().parent


def execute(command: list[str], log_path: Path, env: dict[str, str]) -> None:
    """Stream a subprocess into the console and a persistent run log."""
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


def prepare_llama_cpp(llama_cpp_dir: Path, log_path: Path, env: dict[str, str]) -> str:
    """Fetch and record the converter revision used by the multimodal export."""
    llama_cpp_dir = llama_cpp_dir.resolve()
    if not (llama_cpp_dir / "convert_hf_to_gguf.py").is_file():
        if llama_cpp_dir.exists() and any(llama_cpp_dir.iterdir()):
            raise FileExistsError(
                f"llama.cpp directory exists but is not a usable checkout: {llama_cpp_dir}"
            )
        llama_cpp_dir.parent.mkdir(parents=True, exist_ok=True)
        execute(
            [
                "git", "clone", "--depth", "1",
                "https://github.com/ggml-org/llama.cpp.git",
                str(llama_cpp_dir),
            ],
            log_path,
            env,
        )
    revision = subprocess.check_output(
        ["git", "-C", str(llama_cpp_dir), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if not revision:
        raise RuntimeError("Unable to record the llama.cpp conversion revision.")
    return revision


def compact_multimodal_export(
    output_dir: Path,
    merged_model_dir: Path,
    llama_cpp_dir: Path,
    log_path: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    """Verify and compact the Qwen language GGUF plus its separate vision projector."""
    gguf_dir = output_dir / "gguf_q4_k_m"
    if not gguf_dir.is_dir():
        raise FileNotFoundError(
            "The trainer did not create gguf_q4_k_m; refusing to publish a language-only model."
        )
    revision = prepare_llama_cpp(llama_cpp_dir, log_path, env)
    execute(
        [
            sys.executable,
            str(TRAINING / "compact_multimodal_export.py"),
            "--merged-model-dir", str(merged_model_dir),
            "--llama-cpp-dir", str(llama_cpp_dir.resolve()),
            "--gguf-dir", str(gguf_dir.resolve()),
        ],
        log_path,
        env,
    )
    manifest_path = gguf_dir / "compact-export-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("The multimodal exporter did not write compact-export-manifest.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not any(item.get("kind") == "language_model" for item in manifest.get("files", [])):
        raise RuntimeError("The final compact export has no language-model GGUF.")
    if not any(item.get("kind") == "vision_projector" for item in manifest.get("files", [])):
        raise RuntimeError("The final compact export has no Q8_0 vision projector.")
    manifest["llama_cpp_revision"] = revision
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "llama_cpp_revision.txt").write_text(revision + "\n", encoding="utf-8")
    return manifest


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required evidence file is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def require_token_target(
    train_tokens: int,
    target_tokens: int,
    *,
    allow_below_target: bool = False,
) -> dict[str, Any]:
    """Fail closed before GPU use when the measured corpus misses its target."""
    if train_tokens < 0 or target_tokens < 1:
        raise ValueError("Measured train tokens must be non-negative and target tokens must be positive.")
    shortfall = max(0, target_tokens - train_tokens)
    result = {
        "measured_train_text_tokens": train_tokens,
        "target_train_text_tokens": target_tokens,
        "shortfall_tokens": shortfall,
        "target_met": shortfall == 0,
        "pilot_override_used": bool(shortfall and allow_below_target),
        "decision": (
            "PASS"
            if shortfall == 0
            else "PILOT_OVERRIDE"
            if allow_below_target
            else "BLOCKED"
        ),
    }
    if shortfall and not allow_below_target:
        raise RuntimeError(
            "Refusing GPU fine-tuning: the measured corpus contains "
            f"{train_tokens:,} train text tokens, below the required "
            f"{target_tokens:,} by {shortfall:,}. Add licence-cleared, non-duplicated "
            "material and rerun the exact tokenizer audit. For a deliberately bounded "
            "pilot only, pass --allow-below-token-target and label the run as a pilot."
        )
    return result


def compare_engineering_benchmarks(
    base_path: Path,
    candidate_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    base = load_json(base_path)
    candidate = load_json(candidate_path)
    base_summary = base.get("summary") or {}
    candidate_summary = candidate.get("summary") or {}
    base_domains = base_summary.get("domains") or {}
    candidate_domains = candidate_summary.get("domains") or {}
    domain_comparison = {}
    for domain in sorted(set(base_domains) | set(candidate_domains)):
        before = base_domains.get(domain, {})
        after = candidate_domains.get(domain, {})
        before_rate = before.get("pass_rate")
        after_rate = after.get("pass_rate")
        domain_comparison[domain] = {
            "base_pass_rate": before_rate,
            "candidate_pass_rate": after_rate,
            "delta": (
                float(after_rate) - float(before_rate)
                if before_rate is not None and after_rate is not None
                else None
            ),
            "base_cases": before.get("case_count", 0),
            "candidate_cases": after.get("case_count", 0),
        }
    base_overall = base_summary.get("overall_pass_rate")
    candidate_overall = candidate_summary.get("overall_pass_rate")
    comparison = {
        "benchmark_version": candidate.get("benchmark_version"),
        "base_model": base.get("model"),
        "candidate_model": candidate.get("model"),
        "base_overall_pass_rate": base_overall,
        "candidate_overall_pass_rate": candidate_overall,
        "overall_delta": (
            float(candidate_overall) - float(base_overall)
            if base_overall is not None and candidate_overall is not None
            else None
        ),
        "domains": domain_comparison,
        "promotion_rule": (
            "Do not promote solely on overall pass rate. Review every domain, failures, "
            "engineering limitations and native application acceptance."
        ),
    }
    output_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return comparison



def compare_heldout_evaluations(
    base_path: Path,
    candidate_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Compare the untouched base and trained candidate on one post-training test split."""
    base = load_json(base_path)
    candidate = load_json(candidate_path)
    base_domains = base.get("metrics_by_domain") or {}
    candidate_domains = candidate.get("metrics_by_domain") or {}
    if int(base.get("test_records", -1)) != int(candidate.get("test_records", -2)):
        raise ValueError("Base and candidate held-out evaluations did not use the same record count.")

    metric_names = (
        "json_parse", "key_recall", "scalar_match", "token_f1",
        "plan_shape_valid", "tool_sequence_exact", "tool_recall",
        "argument_key_recall", "plan_step_count_match",
    )
    domains = {}
    for domain in sorted(set(base_domains) | set(candidate_domains)):
        before = base_domains.get(domain, {})
        after = candidate_domains.get(domain, {})
        domains[domain] = {
            metric: {
                "base": before.get(metric),
                "candidate": after.get(metric),
                "delta": (
                    float(after[metric]) - float(before[metric])
                    if before.get(metric) is not None and after.get(metric) is not None
                    else None
                ),
            }
            for metric in metric_names
            if before.get(metric) is not None or after.get(metric) is not None
        }

    comparison = {
        "benchmark_kind": "held_out_sft_corpus",
        "same_held_out_test_split": True,
        "base_model": base.get("model"),
        "candidate_model": candidate.get("model"),
        "test_records": base.get("test_records"),
        "test_split_used_for_training": False,
        "test_evaluated_only_after_candidate_training": True,
        "metrics_by_domain": domains,
        "interpretation_limit": (
            "These are structural, plan-shape and token-overlap diagnostics. "
            "They do not establish native CAD/BIM execution, dimensional engineering accuracy "
            "or statutory compliance; review the independent engineering benchmark and native gates too."
        ),
    }
    output_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return comparison


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

    evidence_files = (
        "training_config.json",
        "training_result.json",
        "curriculum_schedule.json",
        "compute_manifest.json",
        "corpus_audit.json",
        "base_validation_evaluation.json",
        "candidate_validation_evaluation.json",
        "base_heldout_evaluation.json",
        "candidate_heldout_evaluation.json",
        "heldout_evaluation_comparison.json",
        "base_engineering_benchmark.json",
        "candidate_engineering_benchmark.json",
        "engineering_benchmark_comparison.json",
        "large_scale_run_report.json",
        "llama_cpp_revision.txt",
    )
    for filename in evidence_files:
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
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--curriculum-replay-fraction", type=float, default=0.10)
    parser.add_argument("--curriculum-replay-chunk-size", type=int, default=32)
    parser.add_argument("--target-text-tokens", type=int, default=400_000_000)
    parser.add_argument(
        "--allow-below-token-target",
        action="store_true",
        help="Explicitly allow a bounded pilot below the measured corpus target; never represents the 400M programme.",
    )
    parser.add_argument("--resume-from-checkpoint", type=Path)
    parser.add_argument("--llama-cpp-dir", type=Path)
    parser.add_argument("--skip-baseline-evaluation", action="store_true")
    parser.add_argument("--skip-candidate-evaluation", action="store_true")
    parser.add_argument("--skip-engineering-benchmark", action="store_true")
    parser.add_argument("--skip-compact-export", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--model-repo", default="Justin75685/nextai-qwen35-engineering-student")
    parser.add_argument("--evaluation-max-records", type=int, default=0)
    parser.add_argument("--engineering-max-cases", type=int, default=0)
    parser.add_argument("--model-budget-bytes", type=int, default=1_200_000_000)
    args = parser.parse_args()

    if args.epochs <= 0 or args.max_seq_length < 256 or args.batch_size < 1:
        parser.error("epochs, sequence length and batch size are outside supported ranges.")
    if args.gradient_accumulation < 1 or args.lora_rank < 1 or args.target_text_tokens < 1:
        parser.error("gradient accumulation, LoRA rank and token target must be positive.")
    if args.model_budget_bytes < 1 or args.evaluation_max_records < 0 or args.engineering_max_cases < 0:
        parser.error("Model budget must be positive and evaluation limits cannot be negative.")
    if not args.skip_upload and not os.environ.get("HF_TOKEN", "").strip():
        parser.error(
            "HF_TOKEN is required before GPU training so completed weights and evidence can be published. "
            "Use --skip-upload only for an explicitly temporary/local-only run."
        )
    if not args.model_repo.strip():
        parser.error("Model repository cannot be empty.")
    if not args.skip_upload:
        # A present token is not necessarily a write token. Exercise the Hub's
        # create-or-verify endpoint before downloading the base model or using
        # GPU time. The target repository is private and already exists.
        from huggingface_hub import HfApi
        try:
            HfApi(token=os.environ["HF_TOKEN"]).create_repo(
                repo_id=args.model_repo,
                repo_type="model",
                private=True,
                exist_ok=True,
            )
        except Exception as exc:
            parser.error(
                "HF_TOKEN cannot create/verify the private model repository with write access. "
                "Use a Hugging Face write token in the HF_TOKEN secret before launching GPU training. "
                f"Hub preflight error: {type(exc).__name__}: {exc}"
            )
        print(
            f"NEXTAI HUB WRITE PREFLIGHT PASS: {args.model_repo}",
            flush=True,
        )
    if not 0.0 <= args.curriculum_replay_fraction <= 0.5 or args.curriculum_replay_chunk_size < 1:
        parser.error("Curriculum replay fraction must be in [0, 0.5] and chunk size must be positive.")

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
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_text = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
    (data_dir / "corpus_audit.json").write_text(audit_text, encoding="utf-8")
    (output_dir / "corpus_audit.json").write_text(audit_text, encoding="utf-8")

    train_tokens = int(audit["train_text_tokens"])
    if train_tokens <= 0:
        raise ValueError("The measured training text-token count is zero.")
    planned_exposures = train_tokens * args.epochs
    token_target_met = train_tokens >= args.target_text_tokens
    token_gate = require_token_target(
        train_tokens,
        args.target_text_tokens,
        allow_below_target=args.allow_below_token_target,
    )
    print("NEXTAI TOKEN-TARGET GATE: " + json.dumps(token_gate, ensure_ascii=False), flush=True)
    print(
        f"Measured unique train text tokens: {train_tokens:,} / target {args.target_text_tokens:,}. "
        f"Target met: {token_target_met}.",
        flush=True,
    )
    print(
        f"Estimated text-token exposures for {args.epochs:g} epoch(s): {planned_exposures:,}. "
        "This estimate excludes runtime template overhead and image patch tokens.",
        flush=True,
    )
    print(
        "No samples are duplicated automatically to inflate the data/token count.",
        flush=True,
    )

    compute = runtime_manifest(output_dir, audit)
    if not compute["cuda_available"]:
        raise RuntimeError("A CUDA GPU is required. Refusing to fall back to CPU training.")

    env = os.environ.copy()
    log_path = output_dir / "training.log"
    validation_file = data_dir / "validation.jsonl"
    test_file = data_dir / "test.jsonl"
    baseline_validation_eval = output_dir / "base_validation_evaluation.json"
    candidate_validation_eval = output_dir / "candidate_validation_evaluation.json"
    base_heldout_eval = output_dir / "base_heldout_evaluation.json"
    candidate_heldout_eval = output_dir / "candidate_heldout_evaluation.json"
    heldout_comparison_path = output_dir / "heldout_evaluation_comparison.json"
    baseline_benchmark = output_dir / "base_engineering_benchmark.json"

    # Validation may be inspected before/during training. The held-out test
    # split is never evaluated until the candidate has finished training.
    if not args.skip_baseline_evaluation:
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", args.base_model,
                "--test-jsonl", str(validation_file),
                "--output", str(baseline_validation_eval),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path, env,
        )
    if not args.skip_engineering_benchmark:
        execute(
            [
                sys.executable, str(TRAINING / "run_engineering_benchmark.py"),
                "--model", args.base_model,
                "--output", str(baseline_benchmark),
                "--max-cases", str(args.engineering_max_cases),
            ],
            log_path, env,
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
        "--seed", str(args.seed),
        "--curriculum-replay-fraction", str(args.curriculum_replay_fraction),
        "--curriculum-replay-chunk-size", str(args.curriculum_replay_chunk_size),
        "--save-merged-model",
    ]
    if args.resume_from_checkpoint:
        training_command += ["--resume-from-checkpoint", str(args.resume_from_checkpoint.resolve())]
    execute(training_command, log_path, env)

    training_result_path = output_dir / "training_result.json"
    training_result = load_json(training_result_path)
    merged_model = training_result.get("merged_16bit_checkpoint")
    if not merged_model or not (Path(merged_model) / "config.json").is_file():
        raise RuntimeError("Merged student checkpoint was not produced or is incomplete.")

    compact_manifest = None
    llama_cpp_revision = None
    if not args.skip_compact_export:
        llama_cpp_dir = args.llama_cpp_dir or (output_dir / "llama.cpp")
        compact_manifest = compact_multimodal_export(
            output_dir, Path(merged_model), llama_cpp_dir, log_path, env
        )
        llama_cpp_revision = compact_manifest["llama_cpp_revision"]
        training_result = load_json(training_result_path)
        training_result["vision_projector_quantization"] = "Q8_0"
        training_result["compact_export_manifest"] = str(
            output_dir / "gguf_q4_k_m" / "compact-export-manifest.json"
        )
        training_result_path.write_text(
            json.dumps(training_result, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    if not args.skip_candidate_evaluation:
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", str(merged_model),
                "--test-jsonl", str(validation_file),
                "--output", str(candidate_validation_eval),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path, env,
        )

    # Persist the same per-domain validation reports that were used to
    # compare pre-training and post-training behaviour. These reports are
    # development metrics; the independent test split remains untouched.
    training_result = load_json(training_result_path)
    if baseline_validation_eval.is_file():
        training_result["base_validation_metrics_by_domain"] = (
            load_json(baseline_validation_eval).get("metrics_by_domain", {})
        )
    if candidate_validation_eval.is_file():
        training_result["candidate_validation_metrics_by_domain"] = (
            load_json(candidate_validation_eval).get("metrics_by_domain", {})
        )
    training_result["validation_evaluation_status"] = (
        "COMPLETED" if candidate_validation_eval.is_file() else "PENDING"
    )
    training_result_path.write_text(
        json.dumps(training_result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    heldout_comparison = None
    if not args.skip_baseline_evaluation and not args.skip_candidate_evaluation:
        # Freeze the candidate first, then perform the one final base-versus-
        # candidate examination against the identical unseen test set.
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", args.base_model,
                "--test-jsonl", str(test_file),
                "--output", str(base_heldout_eval),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path, env,
        )
        execute(
            [
                sys.executable, str(TRAINING / "evaluate_nextai.py"),
                "--model", str(merged_model),
                "--test-jsonl", str(test_file),
                "--output", str(candidate_heldout_eval),
                "--max-records", str(args.evaluation_max_records),
            ],
            log_path, env,
        )
        heldout_comparison = compare_heldout_evaluations(
            base_heldout_eval,
            candidate_heldout_eval,
            heldout_comparison_path,
        )
        training_result = load_json(training_result_path)
        training_result["held_out_test_metrics_by_domain"] = (
            load_json(candidate_heldout_eval).get("metrics_by_domain", {})
        )
        training_result["base_held_out_test_metrics_by_domain"] = (
            load_json(base_heldout_eval).get("metrics_by_domain", {})
        )
        training_result["held_out_test_evaluation"] = (
            "COMPLETED_AFTER_TRAINING_ON_UNTOUCHED_SPLIT"
        )
        training_result_path.write_text(
            json.dumps(training_result, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    if not args.skip_engineering_benchmark:
        execute(
            [
                sys.executable, str(TRAINING / "run_engineering_benchmark.py"),
                "--model", str(merged_model),
                "--output", str(output_dir / "candidate_engineering_benchmark.json"),
                "--max-cases", str(args.engineering_max_cases),
            ],
            log_path, env,
        )
        if baseline_benchmark.is_file():
            compare_engineering_benchmarks(
                baseline_benchmark,
                output_dir / "candidate_engineering_benchmark.json",
                output_dir / "engineering_benchmark_comparison.json",
            )

    compact_bytes = None
    budget_passed = None
    if compact_manifest:
        compact_bytes = int(compact_manifest.get("total_gguf_bytes", 0))
        budget_passed = compact_bytes <= args.model_budget_bytes
        if not budget_passed:
            print(
                f"WARNING: compact model artifacts are {compact_bytes:,} bytes, "
                f"above the configured {args.model_budget_bytes:,}-byte model budget.",
                flush=True,
            )

    run_report = {
        "status": "TRAINED_AND_HELDOUT_COMPARED" if heldout_comparison else "TRAINED_EVALUATION_PENDING",
        "base_model": args.base_model,
        "training_epochs": args.epochs,
        "max_sequence_length": args.max_seq_length,
        "target_unique_train_text_tokens": args.target_text_tokens,
        "measured_unique_train_text_tokens": train_tokens,
        "estimated_text_token_exposures": planned_exposures,
        "token_target_met": token_target_met,
        "token_target_gate": token_gate,
        "pilot_run": bool(args.allow_below_token_target and not token_target_met),
        "compute_manifest": str(output_dir / "compute_manifest.json"),
        "corpus_audit": str(output_dir / "corpus_audit.json"),
        "training_result": str(training_result_path),
        "curriculum_schedule": str(output_dir / "curriculum_schedule.json"),
        "base_validation_evaluation": None if args.skip_baseline_evaluation else str(baseline_validation_eval),
        "candidate_validation_evaluation": None if args.skip_candidate_evaluation else str(candidate_validation_eval),
        "base_heldout_evaluation": str(base_heldout_eval) if heldout_comparison else None,
        "candidate_heldout_evaluation": str(candidate_heldout_eval) if heldout_comparison else None,
        "heldout_evaluation_comparison": str(heldout_comparison_path) if heldout_comparison else None,
        "base_engineering_benchmark": None if args.skip_engineering_benchmark else str(baseline_benchmark),
        "candidate_engineering_benchmark": None if args.skip_engineering_benchmark else str(output_dir / "candidate_engineering_benchmark.json"),
        "engineering_benchmark_comparison": None if args.skip_engineering_benchmark else str(output_dir / "engineering_benchmark_comparison.json"),
        "compact_export": str(output_dir / "gguf_q4_k_m") if compact_manifest else None,
        "compact_model_bytes": compact_bytes,
        "model_budget_bytes": args.model_budget_bytes,
        "model_budget_passed": budget_passed,
        "llama_cpp_revision": llama_cpp_revision,
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
