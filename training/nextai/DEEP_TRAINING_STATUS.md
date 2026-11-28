# NextAI deep-training readiness — 28 November 2026

**Current decision: NOT READY to begin fine-tuning.** The data volume is substantial, but the complete merged corpus has not yet passed its exact-tokenizer and leakage gates, and native NextCAD/Next BIM acceptance evidence remains incomplete.

The authoritative, measurable pre-training gate is maintained in [NATIVE_OPERATION_FINISH_LINE_GATE.md](NATIVE_OPERATION_FINISH_LINE_GATE.md). This status file supersedes earlier dated checkpoints below; historical 400-million-token targets and old 620-row inventory figures are not current requirements.

## Current curriculum inventory

| Layer | Current count | Evidence |
|---|---:|---|
| Practical NextCAD collection | 20,000 | L0 authored scenarios |
| Practical Next BIM collection | 20,000 | L0 authored scenarios |
| Engineering disciplines | 20,000 | L0 authored scenarios |
| Complex engineering projects | 20,000 | L0 authored scenarios |
| Native operator/tool selection/recovery | 20,000 | L0 authored scenarios |
| Analytical engineering | 25 families × 10,000 = 250,000 | Deterministic formula-backed educational calculations |
| BIMCraft capability metadata | 215 commands × 10 dimensions = 2,150 | L0 capability lessons |
| NextCAD source-module metadata | 32 modules × 6 dimensions = 192 | L0 source lessons; not live runtime command coverage |
| Local project skills | 75 lessons across 16 skill packs | L0 local knowledge |

The practical curriculum is split 80,000/10,000/10,000. Its standalone Qwen/Qwen3.5-0.8B tokenizer audit passed with 95,207,123 text tokens across the three splits. This does not certify the complete merged corpus.

The analytical curriculum contains 25 registered families. Examples include structural beam and column calculations, torsion, geotechnical effective stress/consolidation/bearing/slope stability, hydraulics, pump power, surveying, earthworks and construction quantities. Each family is generated at 10,000 records per build. These are educational analytical cases, not professional design approvals or native CAD/BIM traces.

## Current blockers and active evidence

### 1. Full merged-corpus integrity

- [Run 46128394535](https://github.com/28royalpapi/Next3D/actions/runs/46128394535) built the merged corpus but failed the exact Qwen tokenizer audit because identical normalized conversations appeared across train and validation.
- The audit was not weakened. A read-only diagnostic was added to identify duplicate records, source/domain lineage, split groups and image fingerprints.
- The diagnostic's first CI command had a YAML shell formatting error; it was corrected in [commit b0d7d7d](https://github.com/28royalpapi/Next3D/commit/b0d7d7ddb2565b0978613097e23f3e175ce05454).
- Corrected corpus build [run 46130402327](https://github.com/28royalpapi/Next3D/actions/runs/46130402327) passed the loader/split regression tests and was still preparing the full corpus at the latest checked status. The diagnostic artifact and fresh Qwen audit are pending.
- No duplicate records will be silently discarded and no split leakage will be waived. Inspect the diagnostic first, then repair the source split/deduplication logic and rerun the audit.

### 2. Native application evidence

- BIMCraft's pinned source catalogue contains 215 command registrations. Ten L0 metadata dimensions per command do not prove the commands execute successfully.
- NextCAD's pinned source index contains 32 modules. A live GUI command/API census has not yet been captured; module count is not a command count.
- Next BIM's earlier six L3/L4 records covered only the wall command. The acceptance runner has been expanded to wall and floor in each split, but a new native artifact must prove both commands and save/reopen behaviour.
- The corrected NextCAD Boolean-volume acceptance macro still needs a successful real native GUI run.
- Native build workflow [run 46127286250](https://github.com/28royalpapi/Next3D/actions/runs/46127286250) was still in progress on its Linux build and native test jobs at the latest check. No successful new native training artifact is claimed.

### 3. Training and evaluation

- Fine-tuning has **not** started. No adapter, checkpoint or updated model weights exist.
- No paid Hugging Face GPU/CPU job has been started.
- `--target-text-tokens` is optional and defaults to no project-wide minimum. No arbitrary 400-million-token minimum is imposed by the current training runner.
- A bounded first fine-tuning pilot should begin only after the full merged-corpus integrity audit, native evidence gates and held-out evaluation preparation pass.
- The 18-task practical exam and independent engineering benchmark remain evaluation-only; held-out records must not enter optimizer updates.

## Required next actions

1. Retrieve the corrected workflow's leakage diagnostic artifact and identify exact duplicate records and their source lineages.
2. Repair global split assignment/deduplication at the source or source-group level, retaining provenance and held-out integrity.
3. Rebuild the complete corpus and pass the exact Qwen/Qwen3.5-0.8B tokenizer audit on final train/validation/test files.
4. Complete the NextCAD runtime census and native acceptance; complete Next BIM wall/floor acceptance in all splits.
5. Run independent base-model evaluation on held-out engineering and operator tasks.
6. Only then declare readiness for a bounded zero-cost fine-tuning pilot.

**Do not mark the project fine-tuning-ready solely because record counts or unit tests pass.**
