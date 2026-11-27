# NextAI deep-training readiness — 27 November 2026

This report describes the actual implementation state of branch `nextai-deep-training`. It is not a claim that a Qwen model has already been fine-tuned.

## Latest verified checkpoint — 27 November 2026, 07:24 UTC

The implementation received two additional fail-closed protections:

- run_large_scale_training.py now refuses to start GPU fine-tuning when the exact Qwen-tokenizer audit is below the configured target (400,000,000 by default). A below-target run is possible only with the explicit --allow-below-token-target pilot flag, and its result is labelled PILOT_OVERRIDE rather than target-met.
- When publishing is enabled, the runner checks for HF_TOKEN and calls the Hugging Face create-or-verify endpoint against the private model repository before GPU training. A present but read-only token therefore fails before compute is consumed.
- Four tests cover exact target success, under-target refusal, exact shortfall reporting and explicit pilot labelling.
- GitHub Actions runs [45957925863](https://github.com/28royalpapi/Next3D/actions/runs/45957925863) and [45958097893](https://github.com/28royalpapi/Next3D/actions/runs/45958097893) completed successfully. The test, Python compilation and CLI-help steps all passed on the latest code commit.

The latest connected Hugging Face inspection still shows zero active Jobs. The private model and dataset repositories currently contain only .gitattributes; no corpus, checkpoints, adapters or trained weights are present. The connected OAuth credential exposes jobs and read-repos, not repository-write scope. A separate Hugging Face write token must therefore be provided securely as HF_TOKEN; the runner now verifies that permission before GPU use. No GPU job has been submitted: the 400M corpus has not yet been built/audited, and a maximum compute spend has not been authorised.

This checkpoint is evidence of stronger training controls and passing code checks, not evidence of corpus completion or model training.

## Latest corpus-integrity improvement — 27 November 2026, 07:30 UTC

- The exact-token audit now rejects exact normalized prompt/conversation duplicates within the same split, not only duplicates crossing train/validation/test. This prevents repeated examples from silently inflating the corpus and its apparent training exposure.
- Regression test added for two distinct record IDs carrying the same normalized training text.
- Validation run [45958743631](https://github.com/28royalpapi/Next3D/actions/runs/45958743631) passed: 36 unit tests, Python compilation and CLI-help checks. The duplicate-content regression passed.
- The broader selector/native acceptance workflow [45958743694](https://github.com/28royalpapi/Next3D/actions/runs/45958743694) was still running at this checkpoint; its platform jobs must be checked before claiming a full matrix pass.

This is a corpus-integrity improvement only. It does not mean the full public corpus has been materialized, that 400 million tokens have been measured, or that the model has been trained. Hugging Face still reports no active Jobs and the private corpus/model repositories still contain only .gitattributes. No paid compute has been launched.

## Implemented in the repository

- Full-source corpus builder for the published Zero-to-CAD, IFC/BIM Alpaca and IFC/BIM QA splits.
- BuildEng V8 ingestion: 145,117 published civil/structural/building-engineering chat records under Apache-2.0. Since the source publishes one train split, Next3D assigns deterministic internal partitions by category and normalized user brief.
- Original analytic engineering generator: 17 families, 10,000 parameterised cases per family (170,000 target generated records), with governing equations, inputs, units, assumptions, expected values and limitations.
- Five-stage progressive curriculum: foundations, CAD/BIM fluency, engineering disciplines, operator methods and integrated projects.
- 10% spaced rehearsal from earlier stages after each 32 new examples; sequential training sampler preserves the schedule.
- Indexed JSONL data access and disk-backed SQLite split-integrity checks.
- Actual image-asset attachment for multimodal messages.
- Exact Qwen tokenizer corpus audit, including train/validation/test tokens, source/domain counts, schema tokens and image inventory.
- Resumable checkpoints with a fail-closed comparison of data fingerprints, ordered schedule hash, model and training settings.
- Separate validation evaluation and post-training base-versus-candidate evaluation on the untouched held-out test set.
- Candidate compact export gate for Q4_K_M language weights plus a separately checked Q8_0 vision projector, followed by a package-size report.

## Configured corpus scale

The full-source builder currently targets a mixed train cap of 700,000 records, validation capacity of 60,000 records and held-out test capacity of 50,000 records. The source limits include the full published source splits and the 170,000 analytic-case target.

The programme uses 400 million measured Qwen text tokens as a planning target. It is not an achieved count. The final measured number must come from `corpus_audit.json`; image patches and runtime chat-template overhead are counted separately. If the permitted corpus falls short, the report must state the shortfall and add further licence-cleared sources rather than duplicate records to inflate the token count.

## Code validation

GitHub Actions run [45955110376](https://github.com/28royalpapi/Next3D/actions/runs/45955110376) passed the deep-training validation. The run reported 31 unit tests passing, Python compilation for the large-scale pipeline and CLI checks. These tests validate the data/training code contracts; they are not evidence of a completed GPU run, a trained checkpoint, a native CAD/BIM acceptance test or professional engineering competence.

## What remains uncompleted

- Build the full corpus in a runtime, inspect `manifest.json`, and produce the actual `corpus_audit.json` with Qwen tokenizer counts.
- Record the untouched base model on validation and on the held-out tests after the training protocol is fixed.
- Run BF16 LoRA on an authorised CUDA GPU with resumable checkpoints and full logs.
- Save the adapter, merged checkpoint, Q4_K_M model, Q8_0 vision projector and checksums.
- Compare base and candidate by engineering domain; keep every failed case visible.
- Execute representative plans inside real NextCAD and Next BIM; save, close, reopen and verify actual geometry, object identity and IFC relationships.
- Measure the installed offline model package against the 1.2 GB model budget.

## Compute and Hub state

The connected Hugging Face identity is `Justin75685`. The connected Jobs listing currently contains no active jobs. The private model and dataset repositories exist but currently contain only repository metadata, not training artifacts.

No GPU job has been started. Hugging Face GPU Jobs are billable. A first run must not be submitted until an explicit maximum spend is authorised. The runner itself refuses CPU fallback and does not rent compute.

## Release rule

Do not report “trained”, “400M tokens”, “mastered”, “native validated” or “offline packaged” until the corresponding corpus audit, training logs/checkpoints, held-out evaluation, native acceptance evidence and package measurements exist.
