#!/usr/bin/env python3
"""Build the full available public CAD/BIM corpus for NextAI, not notebook smoke samples."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = Path(__file__).resolve().parent


def run(command: list[str], *, cwd: Path = REPO_ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--cad-train", type=int, default=85000)
    parser.add_argument("--cad-validation", type=int, default=10000)
    parser.add_argument("--cad-test", type=int, default=10000)
    parser.add_argument("--bim-train", type=int, default=115000)
    parser.add_argument("--bim-validation", type=int, default=13000)
    parser.add_argument("--ifcqa-train", type=int, default=10000)
    parser.add_argument("--ifcqa-test", type=int, default=4000)
    parser.add_argument("--buildeng-records", type=int, default=145117)
    parser.add_argument("--analytic-cases-per-domain", type=int, default=10000)
    parser.add_argument("--mixed-train-cap", type=int, default=700000)
    parser.add_argument("--validation-cap", type=int, default=60000)
    parser.add_argument("--test-cap", type=int, default=50000)
    parser.add_argument("--swiss-dwellings-dir", type=Path)
    parser.add_argument("--ifc-model-corpus-dir", type=Path)
    parser.add_argument("--skip-capability-census", action="store_true")
    parser.add_argument("--skip-token-audit", action="store_true")
    parser.add_argument("--tokenizer", default="Qwen/Qwen3.5-0.8B")
    args = parser.parse_args()

    limits = (
        args.cad_train, args.cad_validation, args.cad_test,
        args.bim_train, args.bim_validation, args.ifcqa_train, args.ifcqa_test,
        args.buildeng_records, args.analytic_cases_per_domain,
        args.mixed_train_cap, args.validation_cap, args.test_cap,
    )
    if any(value < 0 for value in limits):
        parser.error("All source and split limits must be non-negative.")
    if args.mixed_train_cap == 0 or args.validation_cap == 0 or args.test_cap == 0:
        parser.error("Mixed train, validation and test caps must be positive.")

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    census_path = out / "capability-census.json"

    if not args.skip_capability_census:
        census_command = [
            sys.executable, str(TRAINING_DIR / "capability_census.py"),
            "--bim-catalog", str(REPO_ROOT / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json"),
            "--nextcad-source-index", str(REPO_ROOT / "docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json"),
            "--expected-nextcad-commit", "00cb280454069966a2fb0a8e7dc184c46e7b38b3",
            "--expected-nextbim-commit", "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b",
            "--output-dir", str(out / "capability-census"),
        ]
        run(census_command)
        census_path = out / "capability-census" / "capability-census.json"
    else:
        candidates = [
            out / "capability-census" / "capability-census.json",
            out / "capability-census.json",
        ]
        census_path = next((path for path in candidates if path.is_file()), None)
        if census_path is None:
            raise FileNotFoundError("--skip-capability-census requires an existing capability-census.json")

    command = [
        sys.executable, str(TRAINING_DIR / "prepare_public_corpora.py"),
        "--output-dir", str(out / "corpus"),
        "--max-cad-train", str(args.cad_train),
        "--max-cad-validation", str(args.cad_validation),
        "--max-cad-test", str(args.cad_test),
        "--max-bim-train", str(args.bim_train),
        "--max-bim-validation", str(args.bim_validation),
        "--max-ifcqa-train", str(args.ifcqa_train),
        "--max-ifcqa-test", str(args.ifcqa_test),
        "--max-buildeng-records", str(args.buildeng_records),
        "--analytic-cases-per-domain", str(args.analytic_cases_per_domain),
        "--max-mixed-train", str(args.mixed_train_cap),
        "--max-validation", str(args.validation_cap),
        "--max-test", str(args.test_cap),
        "--capability-census", str(census_path),
        "--seed", str(args.seed),
    ]
    if args.swiss_dwellings_dir:
        command += ["--swiss-dwellings-dir", str(args.swiss_dwellings_dir.resolve())]
    if args.ifc_model_corpus_dir:
        command += ["--ifc-model-corpus-dir", str(args.ifc_model_corpus_dir.resolve())]
    run(command)

    manifest_path = out / "corpus" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan = {
        "schema_version": 1,
        "profile": "full-public-source",
        "student": "Qwen/Qwen3.5-0.8B",
        "target_train_text_tokens": 400_000_000,
        "token_target_is_a_goal_not_a_claim": True,
        "source_limits": {
            "cad_train_source_rows": args.cad_train,
            "cad_validation_source_rows": args.cad_validation,
            "cad_test_source_rows": args.cad_test,
            "bim_train_source_rows": args.bim_train,
            "bim_validation_source_rows": args.bim_validation,
            "ifcqa_train_source_rows": args.ifcqa_train,
            "ifcqa_test_source_rows": args.ifcqa_test,
            "buildeng_source_rows": args.buildeng_records,
            "analytic_cases_per_domain": args.analytic_cases_per_domain,
            "analytic_engineering_total_target": args.analytic_cases_per_domain * 17,
            "mixed_train_cap": args.mixed_train_cap,
            "validation_cap": args.validation_cap,
            "test_cap": args.test_cap,
        },
        "source_counts": manifest.get("source_counts", {}),
        "records": {
            "train": manifest.get("train_records", 0),
            "validation": manifest.get("validation_records", 0),
            "test": manifest.get("test_records", 0),
            "quarantined": manifest.get("quarantined_rows", 0),
        },
        "training_domain_counts": manifest.get("training_domain_counts", {}),
        "analytic_engineering_split_counts": {
            "train": manifest.get("source_counts", {}).get("analytic_engineering_train", 0),
            "validation": manifest.get("source_counts", {}).get("analytic_engineering_validation", 0),
            "test": manifest.get("source_counts", {}).get("analytic_engineering_test", 0),
            "families": manifest.get("source_counts", {}).get("analytic_engineering_families", 0),
        },
        "capability_census": str(census_path),
        "corpus_dir": str(out / "corpus"),
        "requires_token_audit_before_gpu": True,
        "requires_native_trace_validation_before_claiming_native_mastery": True,
        "note": (
            "400M is a target, not an achieved number. Actual text tokens must be read "
            "from corpus_audit.json; image patch tokens and chat-template overhead are separate."
        ),
    }
    if not args.skip_token_audit:
        audit_command = [
            sys.executable, str(TRAINING_DIR / "audit_nextai_corpus.py"),
            "--data-dir", str(out / "corpus"),
            "--tokenizer", args.tokenizer,
            "--output", str(out / "corpus" / "corpus_audit.json"),
        ]
        run(audit_command)
        audit = json.loads((out / "corpus" / "corpus_audit.json").read_text(encoding="utf-8"))
        plan["token_audit"] = {
            "status": audit.get("status"),
            "train_text_tokens": audit.get("train_text_tokens"),
            "validation_text_tokens": audit.get("validation_text_tokens"),
            "held_out_test_text_tokens": audit.get("held_out_test_text_tokens"),
            "image_files_total": audit.get("image_files_total"),
            "image_bytes_total": audit.get("image_bytes_total"),
        }
        plan["target_met"] = int(audit.get("train_text_tokens", 0)) >= int(plan["target_train_text_tokens"])
    plan_path = out / "large_scale_training_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
