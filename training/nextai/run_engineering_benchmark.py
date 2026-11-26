#!/usr/bin/env python3
"""Run Qwen NextAI against the independent, train-excluded engineering benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from engineering_benchmark_v1 import (
    BENCHMARK_VERSION,
    SYSTEM_PROMPT,
    aggregate_scores,
    benchmark_records,
    score_prediction,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Base Hugging Face model or local trained model directory")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--max-cases", type=int, default=0, help="Zero evaluates every independent case")
    args = parser.parse_args()
    if args.max_new_tokens < 32 or args.max_cases < 0:
        parser.error("--max-new-tokens must be >=32 and --max-cases cannot be negative")

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError(
            "A CUDA GPU is required for Qwen inference. This script does not start or rent compute."
        )
    from unsloth import FastVisionModel

    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=args.model,
        load_in_4bit=False,
        use_gradient_checkpointing=False,
    )
    FastVisionModel.for_inference(model)
    cases = benchmark_records()
    if args.max_cases:
        cases = cases[:args.max_cases]
    scored = []
    outputs = []
    for index, case in enumerate(cases, 1):
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": case["prompt"]}],
            },
        ]
        input_text = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
        )
        inputs = tokenizer(
            input_text,
            add_special_tokens=False,
            return_tensors="pt",
        ).to("cuda")
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
        prompt_tokens = inputs["input_ids"].shape[-1]
        prediction = tokenizer.decode(
            generated[0][prompt_tokens:],
            skip_special_tokens=True,
        ).strip()
        score = score_prediction(case, prediction)
        scored.append(score)
        outputs.append({
            "case_id": case["case_id"],
            "domain": case["domain"],
            "prompt": case["prompt"],
            "prediction": prediction,
            "score": score,
        })
        print(
            f"[{index}/{len(cases)}] {case['case_id']} "
            f"{'PASS' if score['passed'] else 'FAIL'}"
        )

    summary = aggregate_scores(scored)
    result: dict[str, Any] = {
        "model": args.model,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_train_excluded": True,
        "summary": {key: value for key, value in summary.items() if key != "results"},
        "cases": outputs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
