# NextAI native-operation finish-line gate

This record tracks native evidence separately from authored curriculum volume.

## Curriculum finish-line snapshot — 28 November 2026

### Authored curriculum volume (not native mastery)

| Curriculum layer | Current materialized target | Evidence boundary |
|---|---:|---|
| Practical NextCAD collection | 20,000 | L0 scenario-authored; not all native commands executed |
| Practical Next BIM collection | 20,000 | L0 scenario-authored; not all BIMCraft commands executed |
| Engineering disciplines | 20,000 | L0 scenarios; analytical solvers audited separately |
| Complex engineering projects | 20,000 | L0 scenario-authored |
| Native operator/tool selection/recovery | 20,000 | L0 scenario-authored; not native traces |
| Analytical engineering | 25 families × 10,000 = 250,000 | Deterministic formula-backed educational calculations |
| Pinned BIMCraft command lessons | 215 commands × 10 dimensions = 2,150 | L0 metadata obligations |
| NextCAD source-module lessons | 32 modules × 6 dimensions = 192 | L0 source knowledge only; not a live runtime census |
| Local skill lessons | 75 across 16 skill packs | L0 local project knowledge |

The 100,000 practical curriculum has an independently completed exact Qwen/Qwen3.5-0.8B tokenizer audit (95,207,123 text tokens across train/validation/test). The 250,000 analytical source has a previous tokenizer measurement. Neither result substitutes for the fresh audit of the complete merged corpus.

### Latest merged-corpus gate

- The merged-corpus builder reached the exact-tokenizer audit but failed because identical normalized model-facing conversations were found across training and validation.
- The failure is a real hold: no split leakage may be waived to force a PASS.
- A read-only diagnostic has been added to report exact duplicate records, sources, domains, record IDs, image fingerprints and split-group lineage. It must run before the next repair; records must not be silently discarded or moved.
- The diagnostic's first workflow invocation exposed a malformed shell command; that command was corrected in commit b0d7d7ddb2565b0978613097e23f3e175ce05454. The corrected workflow run is still in progress at the time of this snapshot.

### Native application evidence

- NextCAD: the prior acceptance macro passed create/edit/save/reopen but failed its final Boolean-volume assertion. The assertion was corrected to compare the final recomputed pre-save and post-reopen volume. A real native Linux GUI acceptance run and a live command/API census are still required.
- Next BIM: the earlier six native records covered only the wall command. The runner now exercises wall and floor in each split; the new native Linux acceptance artifact must prove both commands in train, validation and test before those records are admitted.
- Source-module counts, metadata lessons, compile checks and unit tests must never be presented as proof of GUI execution.

### Definition of the finish line before the first fine-tuning pilot

1. Every included dataset source has documented provenance/licence, record counts and explicit split lineage.
2. The full merged corpus builds from the intended sources; duplicate IDs, duplicate conversations and source-group leakage are zero. The exact Qwen tokenizer audit passes on the final merged train/validation/test files.
3. The 25 analytical families each retain 10,000 records, and all solver, unit, invalid-input and split tests pass.
4. The 100,000 practical curriculum remains balanced at 20,000 per collection with 80/10/10 split allocation.
5. BIMCraft's 215 registered commands and NextCAD's live runtime command/API census are represented accurately; unsupported or unverified operations remain explicit coverage gaps.
6. Native acceptance artifacts prove the supported NextCAD and Next BIM operations execute and survive save/reopen, with disjoint train/validation/test lineages.
7. Independent held-out exams and engineering benchmarks remain excluded from training. Base-model evaluation is recorded so the tuned candidate can be compared against it.

Passing this gate authorizes a **bounded, zero-cost first fine-tuning pilot**, not a claim that NextAI has mastered every professional engineering task. Promotion to a broader operator model requires the candidate to improve held-out results without increasing invalid or unsafe native operations.

## Current source inventories

- BIMCraft is pinned to \`a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b\` and its checked-in catalogue contains 215 command registrations.
- NextCAD is pinned to \`00cb280454069966a2fb0a8e7dc184c46e7b38b3\`; the current source index contains 32 workbench/module entries. These are not a live GUI command/API census.
- The capability curriculum contains 2,150 BIM command metadata lessons (10 per command) and 192 NextCAD source-module lessons (6 per module), plus 75 local-skill lessons across 16 skill packs. This artifact contains L0 material only; it does not claim native mastery.

## Native evidence status before the explicit Linux build

### Next BIM / BIMCraft

The earlier native artifact contained 6 valid L3/L4 acceptance records (2 train, 2 validation, 2 test), all exercising the \`wall\` command. It therefore proved one real command path only.

The current acceptance runner has been extended to exercise two distinct commands in each split:
1. \`wall\`: draw one wall segment and verify one additional wall after save/reopen.
2. \`floor\`: create a simple floor from a four-point boundary and verify one additional floor after save/reopen.

The collector now refuses a split unless it contains one wall and one floor record, both with matching native pre/post state hashes and count checks. Schema and collector unit tests pass. No claim of actual execution of the new floor path is made until the native Linux build/acceptance workflow produces the new artifact.

### NextCAD

The prior native acceptance run passed create/edit/save/reopen checks but failed its final Boolean-volume assertion. The old assertion compared the reopened result against the original Boolean creation volume, even though the acceptance sequence subsequently revised operand geometry.

The macro now captures the final recomputed Boolean volume immediately before save, reopens and recomputes the project, verifies one valid solid, and compares the actual pre-save and post-reopen volumes with a scale-aware tolerance. It records both measurements. Static tests pass; the corrected macro still requires an actual native GUI acceptance run.

The 32 source modules must not be reported as 32 live workbenches, and no NextCAD GUI command/API count is claimed until a version-matched runtime census artifact is captured.

## Curriculum expansion update — 28 November 2026

The master authored curriculum is now version 3: **98 subjects, 980 L0 examples**,
split into 784 train, 98 validation and 98 held-out test records. It supersedes the
earlier 62-subject/620-record master-curriculum snapshot above. The complete collection
breakdown and detailed lesson objectives are in [training/nextai/README.md](README.md)
and [COMPREHENSIVE_CAPABILITY_CURRICULUM.md](COMPREHENSIVE_CAPABILITY_CURRICULUM.md).

The expansion explicitly fills the electrical/mechanical specialist gap and deepens the
engineering operator and complete-project curriculum. It does not change the acceptance
standard: all 980 rows are L0 authored lessons. The native-operation finish gate, exact
merged-corpus tokenizer/leakage audit and held-out evaluation remain independent blockers.

## Required evidence before full operator fine-tuning

1. NextCAD Linux build and corrected create/edit/save/reopen acceptance pass, plus a valid three-way native training artifact.
2. NextCAD version-pinned GUI command/API census, with registered commands and typed adapter coverage distinguished from source module names.
3. Next BIM native wall and floor acceptance pass in all three splits; command IDs, parameters, native state hashes, and reopened element counts recorded.
4. Complete merged CAD/BIM/engineering corpus built from the intended source set; exact Qwen/Qwen3.5-0.8B tokenizer audit passes on its train/validation/test splits; no split leakage or duplicate IDs/text.
5. Native tool-planning tests on unseen command combinations and failure/recovery cases, plus independent engineering validation where design correctness or safety is claimed.
6. Untouched held-out exams remain excluded from optimizer updates.

## Non-claims

- L0 capability lessons are not L3 native execution traces.
- A passing compile, unit test or source inspection is not proof of GUI/runtime availability.
- A valid BIM object-count round trip is not proof of geometric correctness, code compliance or professional engineering adequacy.
- Fine-tuning has not started and no trained adapter/checkpoint is claimed by this gate document.

## Bounded finish-line review — 28 November 2026

- The 100,000-example practical curriculum is allocated at exactly 20,000 per collection and 80/10/10 train/validation/test.
- The scaled-curriculum builder now audits all eight scenario axes in every collection. It verifies that every option defined in that collection's profile appears at least once and reports per-option minimum/maximum example counts. Regression test: `test_every_profile_option_is_represented_in_each_collection`.
- The profile-option coverage regression passed in the deep-training validation workflow for commit `db8bc1912ea4161a9c2bcff17a3ce004492c4420`; the complete Qwen tokenizer and remaining validation steps were still running at this snapshot.
- Ordinary pushes to `nextai-deep-training` intentionally skip native builds. This commit explicitly requests the Linux native acceptance jobs with the required `[run-native-build]` marker. Do not infer any native PASS until the resulting NextCAD and Next BIM artifacts are inspected.
- The merged-corpus exact-tokenizer audit remains a separate gate. A prior attempt was cancelled during audit; the retried CPU-only corpus build must complete and produce its final result. Its read-only leakage diagnostic must be run against the actual generated train/validation/test files before any split repair.
- Fine-tuning remains blocked. No GPU/CPU fine-tuning job, adapter, or trained checkpoint has been started or produced.
