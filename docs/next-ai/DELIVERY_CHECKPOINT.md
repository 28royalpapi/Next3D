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
- Trainer, corpus builders, split-integrity checks, evaluator and multimodal export code are committed.
- No prepared corpus, fine-tuning run, trained checkpoint or evaluated student is evidenced yet.
- The available local session has no NVIDIA GPU.
- Connected Hugging Face identity reports `@Justin75685`, not confirmed as the Next3D GitHub owner. No GPU job was launched and no files were uploaded to that account. Confirm account ownership and any GPU-job billing before using it, or attach the intended Colab runtime.

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
