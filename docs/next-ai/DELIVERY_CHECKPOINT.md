# Next3D delivery checkpoint

Last updated: 2026-11-26
Repository: `28royalpapi/Next3D`
Branch: `nextai-operator-foundation`

## Operating rule

Continue from the current branch head and Actions runs. Do not recreate the project or repeat conversation history. Work one gate at a time, inspect only failed steps and relevant log excerpts, then make the smallest root-cause fix. Never weaken native acceptance to obtain a green CI result.

## Native delivery gate

Required evidence:
- Verify pinned upstream source commits and generated capability indexes.
- Build NextCAD and Next BIM against those pinned sources on supported platforms.
- Launch each desktop application.
- Execute real operations in the native engines, not just mocks.
- Save, close, reopen and verify project contents/geometry.
- Keep native test suites green. A compiled binary or source-level test is not full acceptance.

Known evidence and fixes:
- Source verification confirmed the BIMCraft catalogue has 215 registrations.
- The data-pipeline suite passed 153 tests in the source-gate run below.
- NextCAD macOS built and its upstream FreeCAD suite passed 2,216 tests in the earlier run. Native duplicate acceptance had a false assumption: the cutter starts at Y=5 mm, but the test expected Y=0. Commit `31eb5ef` snapshots the original placement and checks source immutability plus the exact +40 mm duplicate offset.
- Windows FreeCAD CTest previously had 11 missing-DLL failures (exit code `0xc0000135`). Commit `31eb5ef` adds installation into the pinned runtime environment before the test suite. This is awaiting a fresh Windows run, not yet a proven resolution.
- Linux NextCAD AI acceptance previously timed out when launched through the Pixi task wrapper. Commit `31eb5ef` changes macro/census launch to use the built executable directly. This needs a fresh GUI run.
- Next BIM pinned upstream UI tests expect the Assistant palette to stay closed until requested. Forcing Next AI open produced 89 UI failures. Commit `31eb5ef` removes forced-open/default-layout changes while preserving palette branding as `Next AI` and legacy saved-name mapping.
- The source verifier still required the removed forced-open layout. The follow-up patch aligns it with the pinned upstream default and keeps the established Settings label.

Key commits:
- Training-pipeline updates: `86dbf0dcee9889a2640a8004afa559a2eac6eee8`
- Native acceptance/workspace correction: `31eb5ef0a09b6271b29f39cafded5b6680f1af77`

Actions:
- Earlier native run (failed; diagnosed): https://github.com/28royalpapi/Next3D/actions/runs/45774693218
- Source-gate run (153 data tests passed; stale verifier failed; this checkpoint records the correction): https://github.com/28royalpapi/Next3D/actions/runs/45821205804

## Qwen student training gate

Target: `Qwen/Qwen3.5-0.8B`.

Required evidence:
- Prepare complete train/validation/test corpora with provenance, permission and privacy checks.
- Keep native-success traces separate from knowledge lessons and prevent project/source lineage leakage.
- Run real GPU BF16/FP16 LoRA; do not call a prepared notebook a trained model.
- Compare base and tuned model on the same held-out engineering tasks.
- Export and verify Q4 language GGUF and required Q8 vision projector, with checksums/config/reports.
- Promote only after actual native app acceptance.

Status:
- The CPU-only corpus preparation workflow has now completed successfully (Actions run `45831337789`, commit `afc7aa974ef4daafefa1656e4953414976362b90`). Its audit artifact records 25,780 training, 2,730 validation and 1,415 held-out test records across 83 labelled CAD/BIM/engineering domains; all three split-integrity checks passed with zero cross-split identity conflicts, and the held-out test set is excluded from gradient updates.
- The corpus is currently skewed toward IFC/BIM: 12,804 BIM IFC knowledge and 5,000 BIM IFC QA examples. It contains 2,500 CAD visual and 2,500 CAD feature-trace examples, plus 2,150 pinned capability-knowledge lessons across the train/validation/test sidecars.
- The latest capability census is deliberately incomplete for NextCAD: it found 32 source modules but captured no live runtime commands or Python API members. Its 215 Next BIM registrations and 2,150 learning obligations are metadata inventory/knowledge only, not proof of native execution or mastery.
- The separate train-excluded engineering benchmark contains 28 cases across 15 domains. It has passed its reference-rubric tests, but has not yet been run against a fine-tuned model and is not a native CAD/BIM execution benchmark.
- No fine-tuning run, trained checkpoint, base-vs-tuned model result or deployable model package has been produced.
- Hugging Face identity `@Justin75685` is confirmed by the user. The connected token currently exposes read-only Hub repository scopes and does not have `write-repos`; model/checkpoint upload and creation of a Space are therefore not available through this connection.
- No paid Hugging Face Job has been started. Hugging Face Jobs are billed by the minute. The free ZeroGPU quota is 5 GPU minutes per day for a free account, which is useful for a bounded smoke test but is not a realistic basis for promising completion of this 25,780-record multimodal fine-tune. Do not launch Jobs or upgrade Space hardware under this project without an explicitly approved, zero-cost grant/compute allocation.

## Crash-resistant collaboration

Keep prompts short; do not paste the long history repeatedly. Use the branch head and this file as the durable source of truth. Work one bounded phase per turn:
1. Native CI: inspect the current run, report only failing job/step and concise error context, patch root cause and rerun.
2. Training: validate/download bounded corpus, report counts/provenance/split checks, then use authorised GPU compute.
3. Evaluation/export: compare on the same held-out test set and retain reports/hashes.

Platform jobs now call the source patch script with `--only nextcad` or `--only nextbim`; the shared source-preparation gate still applies/verifies both sources and runs all contract tests. This avoids downloading FreeCAD's recursive dependency tree in Next BIM-only jobs and avoids fetching BIMCraft in NextCAD-only jobs.

Never print entire CI logs. Report current SHA, Actions URL, pass/fail delta and next blocker. Keep user updates concise.

## Latest work session — 2026-11-26

- The earlier native run `45774693218` checked out `86dbf0d`, before the native acceptance correction. Its macOS duplicate check incorrectly expected the cutter's original Y coordinate to be zero even though the cutter was created at Y=5 mm. Commit `31eb5ef0a09b6271b29f39cafded5b6680f1af77` now snapshots the source placement and checks both source immutability and the requested +40 mm copy offset.
- That same correction installs NextCAD into the pinned Pixi runtime before the Windows test suite and launches the Linux native acceptance macro with the built FreeCAD executable instead of the Pixi task wrapper. These changes still need a fresh native run.
- Source-gate run `45821205804` checked out `31eb5ef`. All 153 data-pipeline tests passed, but the final source verifier still required Next AI to be open beside the Project Browser by default. It stopped before the three-platform native matrix. The current branch verifier has since been aligned with the upstream default layout: Properties and Project Browser remain visible, while Next AI stays on-demand. Commit `e60bd80ee6e127d23656325d8738399b8fb093d7` adds a regression test for this rule. A new CI result is still required.
- The training branch now includes a separate 28-case, train-excluded engineering benchmark covering at least eight domains. It scores numerical answers, units and refusal to invent missing design inputs. The benchmark has not yet been run against a trained student.
- Hugging Face authentication succeeds, but a `t4-small` Jobs preflight was rejected with HTTP `402 Payment Required`. No GPU job was created and no training began. The account needs usable Jobs billing/credits or another explicitly authorised GPU runtime.
- The ChatGPT Android crash has no captured app stack trace, so its exact cause is not established. Keep collaboration prompts and log excerpts short; use this checkpoint rather than pasting the entire project history again.


## Latest verified results — 2026-11-26

- Curriculum build and audit: [Actions run 45831337789](https://github.com/28royalpapi/Next3D/actions/runs/45831337789), completed successfully on `afc7aa974ef4daafefa1656e4953414976362b90`. The audit artifact is `nextai-curriculum-profile` (artifact ID `15122248653`; GitHub retention is time-limited). It contains the profile, corpus manifest and capability census, not the full raw corpus.
- Corpus split counts: 25,780 train / 2,730 validation / 1,415 held-out test. Main, local-skill and capability-knowledge splits all report PASS with zero cross-split conflicts. The audit reports zero quarantined rows.
- Native build: [Actions run 45838757169](https://github.com/28royalpapi/Next3D/actions/runs/45838757169) is the current native run on commit `e60bd80ee6e127d23656325d8738399b8fb093d7`. Its source-preparation job passed, including source patch verification, pinned capability-index verification and data-pipeline tests. The Linux/Windows/macOS native matrix is still running/queued; do not claim native acceptance until every required job and native save/reopen/launch check has passed.
- The previous native run `45831334712` was cancelled when later commits arrived. Its partial matrix results are not a final acceptance result.
- No HF Jobs or paid Space hardware have been started. A free ZeroGPU Space is limited to five GPU minutes per day; a Community GPU Grant is a possible no-charge route for a public Space, but approval is discretionary and must be obtained before any paid hardware is enabled.

