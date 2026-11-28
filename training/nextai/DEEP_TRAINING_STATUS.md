# NextAI deep-training readiness — 28 November 2026

**Decision: NOT READY to start fine-tuning.** The curriculum breadth is now substantial and independently audited in its standalone form, but the final merged corpus has not passed its exact Qwen tokenizer/leakage gate and the latest native NextCAD/Next BIM acceptance workflow has not completed.

The authoritative finish criteria are in [NATIVE_OPERATION_FINISH_LINE_GATE.md](NATIVE_OPERATION_FINISH_LINE_GATE.md). Earlier dated reports and historical 400-million-token targets are superseded. The current training runner has no project-wide token minimum by default.

## Verified curriculum inventory

| Curriculum layer | Records | Current evidence level |
|---|---:|---|
| NextCAD practical collection | 20,000 | L0 authored scenarios |
| Next BIM practical collection | 20,000 | L0 authored scenarios |
| Engineering disciplines | 20,000 | L0 authored scenarios |
| Complex engineering projects | 20,000 | L0 authored scenarios |
| Native operator/tool selection/recovery | 20,000 | L0 authored scenarios |
| Analytical engineering | 25 families × 10,000 = 250,000 | L0 formula-backed educational calculations |
| BIMCraft capability lessons | 2,150 (215 commands × 10 dimensions) | L0 pinned metadata knowledge |
| NextCAD module lessons | 192 (32 modules × 6 dimensions) | L0 pinned source knowledge |
| Local project skill lessons | 75 across 16 skill packs | L0 authored knowledge |

The practical collections have 80,000 train, 10,000 validation and 10,000 held-out test records. All eight scenario axes are present in every collection: project context, objective, operation, starting state, constraint, input quality, deliverable and affected input. The 45–96 affected-input options per collection each have at least 166 examples; other axes have at least 1,980 examples per option. The original subject allocations are also tested.

### Standalone exact-tokenizer evidence

Deep-training validation [run 46130904424](https://github.com/28royalpapi/Next3D/actions/runs/46130904424) completed successfully with **175 unit tests**. The 100,000 practical curriculum passed exact Qwen/Qwen3.5-0.8B tokenization:

- Train: 76,157,082 text tokens
- Validation: 9,521,610
- Held-out test: 9,528,431
- Total: 95,207,123
- Zero missing images, cross-split identity leakage, cross-split exact-text leakage, within-split duplicate text or duplicate IDs.

The same run audited the capability and skill sidecars: 2,342 metadata lessons plus 75 skill lessons, with 2,505,999 text tokens and zero duplicate IDs/text or cross-split leakage. These sidecars are L0; the audit does not claim native execution.

The 250,000 analytical records previously measured 129,430,330 training text tokens. A subsequent builder correction now keeps all 25 families outside the capped public/mixed sampler and verifies their per-family counts in the final JSONL splits. The new unit tests for that preservation passed in the current corpus-loader regression run.

## Remaining hard blockers

### 1. Complete merged-corpus build and leakage audit

- Previous full-corpus run [46128394535](https://github.com/28royalpapi/Next3D/actions/runs/46128394535) reached the tokenizer gate but failed on exact normalized conversations crossing train and validation.
- A read-only leakage diagnostic now reports record IDs, source/domain, split-group lineage and image fingerprints; the audit is not weakened and duplicates are not silently discarded.
- The merged-corpus adapter now preserves scenario-axis metadata, and regression tests verify the metadata survives conversion.
- Latest full-corpus run [46131656244](https://github.com/28royalpapi/Next3D/actions/runs/46131656244) passed its loader/split regression tests and capability census, and was still preparing the merged curriculum at the latest check. The final merged tokenizer audit and diagnostic report have not yet completed.

### 2. Native NextCAD and Next BIM execution

- The pinned source census currently finds 32 NextCAD source modules, **zero live NextCAD runtime commands/API members**, and 215 BIMCraft registered commands. The live NextCAD census is incomplete.
- BIMCraft's 2,150 lessons and NextCAD's 192 source-module lessons are knowledge obligations, not proof that the commands execute.
- NextCAD still needs a successful GUI acceptance run proving create/edit/save/reopen and the corrected Boolean-volume assertion.
- Next BIM still needs native wall and floor operations with save/reopen evidence across train, validation and test.
- Native application workflow [run 46131141810](https://github.com/28royalpapi/Next3D/actions/runs/46131141810) was still running the NextCAD Linux build and Next BIM native test suite at the latest check. No successful new native training artifact is claimed.

### 3. Fine-tuning access and evaluation

- Fine-tuning has **not** started. No adapter, checkpoint or trained weights exist.
- Hugging Face account `Justin75685` has zero running jobs. The private dataset and model repositories contain only `.gitattributes`.
- The connected Hugging Face OAuth credential is read-only (`read-repos`, no write scope). A separate write-enabled `HF_TOKEN` is needed to publish weights to the private model repository.
- No paid compute has been used or launched.
- The 18-task practical exam and independent engineering benchmark remain held-out evaluation material, not training data.

## Finish-line sequence

1. Complete the latest full merged-corpus build and inspect its read-only leakage diagnostic.
2. Repair any source-level duplicate/split lineage issues; rebuild until the final Qwen tokenizer audit passes with zero leakage and duplicates.
3. Complete the live NextCAD runtime census and native NextCAD/Next BIM acceptance evidence; rebuild the corpus using the completed native workflow artifact.
4. Run held-out base-model evaluations and verify the exam remains excluded from training.
5. Obtain the write-enabled Hugging Face secret if publishing the resulting adapter is required.
6. Only then declare readiness for a bounded, zero-cost first fine-tuning pilot.

**Do not start fine-tuning based only on example counts or a successful standalone curriculum audit.**
