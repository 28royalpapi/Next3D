# NextAI native-operation finish-line gate

This record tracks native evidence separately from authored curriculum volume.

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
