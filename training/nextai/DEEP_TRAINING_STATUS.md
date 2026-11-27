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


## Latest portable-multimodal-corpus improvement — 27 November 2026

- Newly prepared CAD image references are stored relative to the corpus root, not as machine-specific absolute filesystem paths. A complete corpus can be moved to another machine/runtime without rewriting JSONL records.
- The exact Qwen-tokenizer audit resolves relative images from the corpus directory and refuses to report PASS when any referenced asset is missing. A diagnostic-only `--allow-missing-images` override emits `OVERRIDE_MISSING_IMAGES`, never PASS.
- The trainer's split-integrity preflight and image loader now resolve relative references against the JSONL corpus root, aligning audit and training path semantics.
- Regression tests cover relative asset references, trainer-side resolution, and fail-closed missing-image handling.

This improves corpus portability and catches multimodal asset failures before baseline evaluation or GPU preparation. It does not establish that the full corpus exists, that 400 million tokens have been measured, or that model training has occurred.


## Live NextCAD capability-census integration — 27 November 2026

- The full-scale corpus builder now accepts `--nextcad-runtime-report` from the read-only `discover_nextcad_runtime.FCMacro` capture. It forwards the report to the pinned capability census, which adds the live GUI command registry and public Python API members discovered in loaded modules to the capability inventory and L0 learning lessons.
- `--require-nextcad-runtime` now makes the full build fail closed when a live capture is missing. The builder's plan records source modules, captured GUI commands, loaded API modules/members, BIMCraft registered commands, capability counts and the enumeration scope. It explicitly labels skill obligations as not being training examples and does not claim mastery.
- This closes a connection gap between the live-runtime census already supported by `capability_census.py` and the large-scale build entry point. The macro still has to be run inside the pinned NextCAD GUI to create the JSON report; code integration does not mean that capture has already occurred. Its enumeration is limited to visible registered commands and loaded public Python members, not every C++ symbol or optional API.


## Native execution-evidence ingestion — 27 November 2026

- The full-scale builder now accepts separate prepared native SFT files for NextCAD and Next BIM across train, validation and held-out test splits, and forwards each to the existing native-trace ingestion path in `prepare_public_corpora.py`.
- Before corpus construction it validates each JSONL file's application identity, declared split, conversation shape, stable record IDs and JSON integrity; it records per-file SHA-256 fingerprints and row counts in the large-scale plan.
- `--require-native-traces` is a strict mode that refuses to build the execution-training corpus unless all six app/split files are present and non-empty. This prevents the project from confusing capability descriptions or synthetic plans with examples of successful native operations.
- These are input gates and plumbing, not a claim that a set of L3/L4/L5 native traces has already been collected. The validated native trace preparation route remains `prepare_native_sft.py`; records must prove native validation, recompute and save/reopen, have reviewed provenance/privacy, and pass the training-record schema.


## Preservation of validated native traces — 27 November 2026

- Native NextCAD and Next BIM operation traces are now assembled separately from the capped public/synthetic sample. All accepted native training traces are appended after public-data sampling; all native validation and test traces are appended after the public validation/test caps.
- Six application/split sidecar files are emitted (`nextcad_native_{train,validation,test}.jsonl` and `nextbim_native_{train,validation,test}.jsonl`) and their exact per-split counts are recorded in the manifest.
- This prevents high-evidence native operation examples from being lost to random down-sampling and protects native held-out evidence from public-data limits. The test split remains held out and is not added to training.


## Pre-training native-evidence gate and provenance — 27 November 2026

- The GPU runner now accepts `--require-native-traces`. Before loading the tokenizer or model, it checks the corpus manifest for non-empty NextCAD and Next BIM train, validation and test splits and verifies the traces were retained outside the public-data caps.
- The runner writes `native_trace_coverage.json` into its evidence bundle, including counts, missing splits and the explicit field `native_execution_mastery_claimed: false`.
- Corpus manifests now identify each application’s native execution trace source separately and state that source licences are recorded per record.
- This is a fail-closed training-entry requirement for a full native-execution run. It still depends on a real set of native traces having been captured and approved; no trace collection or GPU training has happened in this session.


## Verified work-session checkpoint — 27 November 2026, 08:03 WAT

Latest branch commit at this checkpoint: `41a2450424dc2078fb355bbbd6fe8740a7234fd9`.

### Landed implementation changes

1. Multimodal corpus paths are relocatable; image audit and trainer both resolve relative paths against the corpus root. Missing image assets block an audit PASS unless the explicit diagnostic-only override is used.
2. The full-scale builder can consume a live NextCAD runtime census and optionally requires one. The plan records live command/API counts and clearly states the API enumeration scope.
3. The full-scale builder accepts six prepared native SFT input files (NextCAD and Next BIM, each train/validation/test), validates their JSONL/application/split/IDs, fingerprints them and forwards them into corpus assembly.
4. Validated native execution traces are retained outside the public/synthetic sampler and public validation/test caps. Six application-specific sidecar JSONL files are emitted and exact per-split counts are written to the manifest.
5. The GPU runner offers `--require-native-traces`; it blocks before tokenizer/model download and GPU use unless all six app/split trace counts are non-zero and the manifest confirms trace retention. It writes a native-trace coverage evidence report without claiming mastery.

### Verification

- Latest deep-training validation run `45962660663`: **52 unit tests passed**, training-pipeline compilation passed, and CLI help checks passed.
- Latest selector visual smoke matrix run `45962660619`: Windows and macOS Intel passed; Linux was still running when this checkpoint was written.
- Previous complete three-platform matrix on commit `2a88d990ace17bbcea627052437c1c01dc4aa9b9` passed on Windows, macOS Intel and Linux.

### Not yet completed

- No live NextCAD GUI runtime census was captured in this session.
- No actual native trace dataset was supplied or collected; the new six-file gates are tested with fixtures only.
- The 400M tokenizer-measured training target has not been achieved or verified.
- Hugging Face reports no running jobs. The private model and dataset repositories still contain only `.gitattributes`; no adapter, checkpoint, merged weights or quantized model exists there.
- No paid compute was launched and no model weights were changed.

This checkpoint is a substantial improvement to data correctness and the path for learning/validating native operations. It is not a trained-model improvement claim.


## Native-trace evidence carried into SFT — 27 November 2026

- `prepare_native_sft.py` now embeds a compact proof envelope in every accepted SFT row: validation result, recompute and save/reopen pass flags, verified native after-state SHA-256, operation counts and a canonical operation-trace SHA-256.
- Both `prepare_public_corpora.read_native` and the full-scale builder reject native SFT inputs without that passing validation proof envelope. This closes the gap where a conversation-shaped row with source metadata could be mistaken for a verified native execution trace.
- The proof metadata is derived from the original schema-validated native record. It is evidence of the recorded source checks, not a cryptographic attestation by the native application and not a claim of general model mastery.


## Split-disjoint native NextCAD collection harness — 27 November 2026

- The native GUI acceptance runner now accepts explicit `--split`, `--scenario-id` and `--scenario-scale` values. The actual Part/PartDesign geometry, operation arguments, boolean-volume assertion and recorded millimetre parameters scale together so the three runs are not identical copies.
- New `scripts/collect_nextcad_native_splits.py` launches three separate native GUI acceptance processes: compact train (0.8×), standard validation (1.0×), and expanded held-out test (1.25×). Each produces two staged traces. The collector rejects missing/failed operations, duplicate IDs, wrong split labels and reused project lineage across train/validation/test.
- It combines the six raw schema records, runs `prepare_native_sft.py`, emits split-specific raw files plus SFT train/validation/test sidecars, and writes a manifest with file hashes, counts and explicit L3/L4-only evidence classification.
- The native build workflow now collects and uploads this corpus from its Linux GUI acceptance environment. The build remains manually dispatched; routine branch pushes do not initiate the expensive native build.
- This will produce six controlled native acceptance examples when the workflow runs successfully. It does not provide broad CAD task coverage, Next BIM traces or independent engineering validation.


## Native Next BIM/BIMCraft command-trace collector — 27 November 2026

- Added a native CLI acceptance runner for the pinned BIMCraft executable. It loads the sample project, applies two actual `wall` commands with explicit millimetre coordinates, saves after each command, reopens through `bimcraft-cli info`, and requires the wall count to increase by exactly one each time.
- Each recorded trace retains exact command ID and arguments, CLI output, before/after project hashes, native project summaries, command schema catalogue revision, save/reopen checks and source lineage. The SFT converter keeps Next BIM's distinct `steps` response contract.
- Added a three-run collector (0.8× compact train, 1.0× standard validation, 1.25× expanded test) with split-disjoint source lineage and SFT conversion. The native build workflow's Linux Next BIM job now uploads its output as a 30-day artifact.
- The trace evidence confirms that the BIMCraft CLI accepted the command and reopened the saved project with the expected wall count. It does not claim independent geometry or engineering approval.


## Native trace collection milestone — verified checkpoint 27 November 2026, 09:42 WAT

### Collection implementation now present

- NextCAD GUI acceptance runner supports train/validation/test labels and three scaled scenario families (0.8x, 1.0x, 1.25x). It executes the existing typed Part/PartDesign workflow in three separate GUI processes and checks the emitted stage records' split and scenario lineage.
- `collect_nextcad_native_splits.py` validates two stage records per split, operation success, schema, save/reopen/recompute evidence, distinct source lineages and record IDs; converts the six records with `prepare_native_sft.py`; and writes raw, split-specific and SFT sidecars plus a hashed manifest.
- Next BIM now has a native BIMCraft CLI runner that applies actual `wall` commands to a sampled project, saves and reopens after each command, and requires the reported wall count to increase by exactly one. It records two stage records per run with exact arguments, before/after BIMC hashes and count-based persistence evidence.
- `collect_nextbim_native_splits.py` runs the 0.8x/1.0x/1.25x scenarios, validates app/split/schema/evidence/operation scope and split-disjoint project lineages, converts six records to SFT and writes split sidecars plus a manifest.
- The manually dispatched native application build workflow now runs both collectors on Linux and uploads separate 30-day artifacts for NextCAD and Next BIM. The workflow was deliberately not dispatched during this work session to avoid starting long-running native builds / compute without an explicit request to incur those costs.
- Next BIM's split validator now requires each source lineage to identify the expected split scenario and only admits the native `wall` operation used by this acceptance harness.

### Latest validation evidence

Latest active branch head at this checkpoint: `531eb2c419e85804c7e97ad8166bd75f53392d95`.

- Deep-training CI run `45967629751`: **55 core tests, 9 native SFT tests and 6 Next BIM split-validation tests passed** (70 tests total across the groups). Python compilation and CLI help checks passed.
- Run URL: https://github.com/28royalpapi/Next3D/actions/runs/45967629751
- Selector visual smoke run `45967630002` was triggered for this branch; its final result should be checked independently.

### What remains unclaimed

- The native application workflow has not yet been run on the new collection path, so the planned six NextCAD and six Next BIM native examples do not yet exist as collected artifacts.
- These controlled scenarios are software acceptance fixtures for specific typed operations/CLI commands, not broad user design coverage, not 100k/10k capability mastery, and not independent L5 engineering validation.
- No training corpus reaching 400M measured Qwen text tokens has been built or audited. No Hugging Face GPU job has been launched; no adapter/checkpoint/quantized student weights have been produced. Paid compute remains unstarted.
## Native collection manifest → full-corpus handoff — verified checkpoint 27 November 2026, 10:15 WAT

### Implementation committed

- Both native collectors now emit portable artifact inventories for raw traces, per-split raw files, SFT train/validation/test files, quarantine output and SFT summary. Each inventory entry records relative path, byte size and SHA-256; JSONL entries also record their non-empty row count.
- The collectors refuse to write a successful collection manifest when SFT conversion quarantines records or detects source-group split leakage.
- prepare_large_scale_corpus.py now accepts --nextcad-native-manifest and --nextbim-native-manifest. It verifies manifest schema, application, pinned upstream source revision, all artifact paths, sizes, hashes and line counts before accepting the SFT files.
- --require-native-manifests requires both application manifests and all six non-empty train/validation/test SFT splits. The builder rejects mixing a manifest with explicit split paths for the same application.
- The builder parses the raw trace and each split sidecar, verifies application/split identity, checks project lineage separation across all three splits, and requires the converted SFT record-ID sets to match the raw accepted record-ID sets exactly. The hashed SFT summary must agree with the manifest summary, and quarantine/leakage must be zero.
- This is file integrity and provenance validation, not a signed or cryptographic attestation of the native application. It does not upgrade the underlying acceptance fixture's engineering validation level.

### Latest validation

- Validated code commit: f349e9b9c8ad28e17226d73dc694d31afed54afc.
- Deep-training CI run 45972091495: 61 corpus/training tests, 9 native SFT tests, 13 Next BIM split/evidence tests and 8 NextCAD split/artifact tests passed (91 total). Python compilation and CLI help checks passed.
- Run: https://github.com/28royalpapi/Next3D/actions/runs/45972091495
- Selector visual smoke run 45972091502: macOS Intel and Windows steps passed; Linux was still running at the time this checkpoint was written. Check the final run result separately.

### Work not yet performed

- The native GUI/CLI collection workflow was not dispatched. No actual NextCAD or Next BIM trace corpus artifacts have been collected from the pinned native builds; current coverage is collector and pipeline fixtures/tests only.
- No live NextCAD runtime census was captured.
- The 400M measured Qwen text-token target has not been achieved or audited, and no model fine-tune/checkpoint/weights have been produced.
- No paid GPU or other paid compute was started.

## Manifest/raw/SFT lineage cross-check — verified 27 November 2026, 10:17 WAT

- The full-scale corpus builder now cross-checks each collector manifest's train/validation/test report against the actual raw trace rows: declared record counts, exact record-ID sets and source project lineage must agree.
- It also verifies that the raw split sidecars match their corresponding raw-trace subsets, that train/validation/test project lineages do not overlap, and that SFT conversion preserves the exact accepted raw record IDs.
- Manifest semantics are fail-closed: the pinned app/schema revision, collector evidence level, controlled synthetic acceptance-fixture label, split-disjoint lineage declaration and explicit 'independent engineering validation not claimed' statement are all checked.
- Latest validated code commit: cc101cb57faef4922eb8885034a941cf70bd4688.
- Deep-training CI run 45972391784 passed: 64 corpus/training tests, 9 native SFT tests, 13 Next BIM split/evidence tests and 8 NextCAD split/artifact tests (94 total), plus script compilation and CLI-help checks.
- Run: https://github.com/28royalpapi/Next3D/actions/runs/45972391784
- No native build/collection job was dispatched. The native execution examples remain planned collector fixtures; no actual native trace dataset, 400M-token corpus or trained model weights were created in this milestone.

## Native split scenario identity enforcement — verified 27 November 2026, 10:19 WAT

- The full-corpus builder additionally enforces the declared controlled scenarios: train = train-compact (0.8x), validation = validation-standard (1.0x), and held-out test = test-expanded (1.25x), for both applications.
- Scenario IDs and scales are compared with the collector's split report before the records can be accepted.
- Validated code commit: fb f515228ee7c54193ed6b90cabd5453321c7c18 (full SHA: fbf515228ee7c54193ed6b90cabd5453321c7c18).
- Deep-training CI run 45972631867 passed: 65 corpus/training tests, 9 native SFT tests, 13 Next BIM split/evidence tests and 8 NextCAD split/artifact tests (95 total); compilation and CLI-help checks passed.
- Run: https://github.com/28royalpapi/Next3D/actions/runs/45972631867
- Selector smoke run 45972631858 was still completing its cross-platform jobs at this checkpoint.
- Hugging Face recheck: zero active jobs; the model and dataset repositories still contain only .gitattributes. No weights or corpus artifacts have been published, and no paid compute has been started.
