#!/usr/bin/env python3
"""Collect split-disjoint native Next BIM/BIMCraft CLI traces and prepare SFT sidecars."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_nextbim_ai_acceptance.py"
SCENARIOS = {"train": ("train-compact", 0.8), "validation": ("validation-standard", 1.0), "test": ("test-expanded", 1.25)}


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def collect_trace_files(trace_files: dict[str, Path], output_dir: Path) -> dict[str, Any]:
    if set(trace_files) != set(SCENARIOS):
        raise ValueError("Exactly Next BIM train, validation and test files are required")
    rows_all, reports, ids, lineages = [], {}, set(), set()
    for split in ("train","validation","test"):
        path=Path(trace_files[split]).resolve()
        if not path.is_file(): raise FileNotFoundError(f"Missing Next BIM {split} trace: {path}")
        rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows)!=2: raise ValueError(f"Next BIM {split} must contain two native operation records")
        source_ids={row.get("source",{}).get("source_id") for row in rows}
        if len(source_ids)!=1 or not next(iter(source_ids)): raise ValueError(f"Next BIM {split} records must share one source lineage")
        source_id=next(iter(source_ids))
        if source_id in lineages: raise ValueError("A native BIM project lineage was assigned to more than one split")
        lineages.add(source_id)
        for row in rows:
            if row.get("application")!="nextbim" or row.get("split")!=split: raise ValueError(f"Wrong application or split in Next BIM {split} trace")
            if row.get("record_id") in ids: raise ValueError("Duplicate Next BIM record ID")
            ids.add(row.get("record_id"))
            validation=row.get("validation",{})
            if validation.get("overall") not in {"passed","passed_with_warnings"} or validation.get("round_trip_passed") is not True or validation.get("recompute_passed") is not True:
                raise ValueError(f"Next BIM {split} record lacks passing native evidence")
            if not row.get("operations") or any(op.get("status")!="applied" for op in row["operations"]):
                raise ValueError(f"Next BIM {split} record contains missing or failed commands")
        reports[split]={"records":len(rows),"source_id":source_id,"sha256":sha256_file(path),"scenario_id":SCENARIOS[split][0],"scenario_scale":SCENARIOS[split][1]}
        rows_all.extend(rows)
    output_dir.mkdir(parents=True,exist_ok=True)
    raw=output_dir/"native-records.jsonl"
    raw.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows_all),encoding="utf-8")
    for split in ("train","validation","test"):
        (output_dir/f"nextbim-native-{split}.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows_all if row["split"]==split),encoding="utf-8")
    sys.path.insert(0,str(ROOT))
    from training.nextai.prepare_native_sft import prepare
    summary=prepare(raw,output_dir/"sft")
    expected={"train":2,"validation":2,"test":2}
    actual={split:summary.get(split,0) for split in expected}
    if actual!=expected: raise RuntimeError(f"Next BIM SFT did not preserve six records: {actual}")
    manifest={"schema_version":"nextbim.native-trace-corpus.v1","application":"nextbim","source_revision":"a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b","evidence_level":"L3 native CLI execution + L4 project save/reopen","independent_engineering_validation":"not_claimed","synthetic_acceptance_fixtures":True,"split_record_counts":actual,"splits":reports,"raw_trace_file":raw.name,"raw_trace_sha256":sha256_file(raw),"sft_output_dir":"sft","sft_summary":summary,"source_lineages_disjoint":True,"note":"Native BIMCraft wall-command acceptance examples. They test command execution and project persistence; independent geometric and engineering validation is not claimed."}
    (output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return manifest


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    cli=args.cli.resolve()
    if not cli.is_file(): raise SystemExit(f"Next BIM CLI executable not found: {cli}")
    out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    files={}
    for split,(scenario,scale) in SCENARIOS.items():
        run_dir=out/"runs"/split; run_dir.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,str(RUNNER),"--cli",str(cli),"--output-dir",str(run_dir),"--split",split,"--scenario-id",scenario,"--scenario-scale",str(scale)]
        print("+"," ".join(cmd),flush=True); subprocess.run(cmd,cwd=Path.cwd(),check=True)
        files[split]=run_dir/"nextbim-ai-native-acceptance-trace.jsonl"
    print(json.dumps(collect_trace_files(files,out),indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
