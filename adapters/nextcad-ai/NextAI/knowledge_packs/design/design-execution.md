# From approved design brief to editable native model

## Core rule

A design request has two distinct phases: understand and agree the brief, then create the design in the native application. A plan is not a model, a rendered picture is not an editable design, and a successful tool call is not proof that the overall design is complete.

Use the live application's command catalogue and typed tools. Do not invent commands, parameters or geometry. Preserve project state, feature history, component identity and user-approved decisions.

## The operating sequence

1. Inspect the active document/project and discover the current native capabilities.
2. Retrieve the relevant CAD/BIM workflow guidance and identify the appropriate workbenches or native command families.
3. Confirm the design brief, units, envelope, components, constraints, deliverable and open assumptions.
4. Break multi-step tasks into short, visible stages. Give each object a meaningful label and stable native identity.
5. Build using native editable geometry, BIM elements or parametric feature history. Avoid replacing a parametric object with a static mesh when the user expects future editing.
6. Recompute/update the native viewport after each successful operation. Show the progress of the actual operation; do not animate a pretend drawing or show a mock image as if it were native geometry.
7. Inspect the resulting document after each major stage. Verify geometry, dimensions, relationships, constraints, quantities or element counts relevant to the task.
8. Keep a clear list of incomplete work, unresolved information, warnings and checks that were not performed.
9. When the user asks for a change, identify the exact existing native object and modify it in place. Do not create a duplicate merely because the original object is difficult to locate. If multiple candidates match, ask which one.
10. After edits, re-inspect the document and report before/after values and the resulting model state.

For a long operation, use the native application's progress/checklist mechanism. Preserve the application's normal undo transaction. If an operation fails validation, stop or roll back according to the native tool's transaction behaviour; never report success for a failed operation.

## Residential floor-plan creation

After the user confirms the room programme and agrees a layout envelope, build the plan from measurable native elements:

- Establish a coordinate origin, units, overall envelope and drawing orientation.
- Create room boundary or wall geometry using the native drafting/architectural tools available in the live installation.
- Use named rooms/spaces where the native application supports them, rather than only drawing unlabeled rectangles.
- Place doors and windows only where the agreed circulation, privacy, daylight, access and ventilation intent has been confirmed.
- Dimension the overall envelope and important room dimensions. Label each bedroom, master bedroom, ensuite, shared bathroom, sitting room, store, kitchen/dining and circulation space.
- Check that room zones fit inside the envelope, do not unintentionally overlap, have clear access relationships and match the agreed room counts.
- If the current toolset can only create 2D outlines and annotations, clearly describe the result as a 2D zoning/drafting concept. Do not call it a complete architectural wall/opening model.
- Keep the design editable: retain individual room/wall objects, meaningful names, dimensions and feature/model relationships.

A room schedule should record at least: room mark, room name, level, proposed width, proposed length, area, occupancy/use notes and whether the values are user-confirmed or proposed. Do not silently change a user's room count.

## Watchtower / guard tower creation

A phrase such as "wash tower" may mean watchtower or guard tower. Confirm the intended structure before modelling. Establish:

- structure type and material intent: steel, reinforced concrete, timber or another system;
- number of occupants and use of the cabin;
- observation-platform height and total height;
- support footprint and cabin dimensions;
- access by stair or ladder;
- roof, doors, windows, guardrails, lighting and power;
- site survey, ground/geotechnical information and wind exposure;
- whether the user wants a visual concept or an engineered construction design.

For an approved visual concept, create separate native components with meaningful labels: columns (C01, C02…), beams (B01, B02…), deck/platform (D01), cabin walls (W01…), roof (R01), access/stair, guardrails and openings when the geometry and toolset support them. Add dimensions and a member/component schedule so the user can identify each object.

A visual member envelope must be explicitly labelled as a placeholder, for example: "B01 — beam envelope 250×400 mm — concept placeholder, not engineered." The envelope is not a selected steel section, a reinforced-concrete design or proof of capacity. Do not assign a material if the available native tools cannot set and verify it. Do not claim wind resistance, stability, connection adequacy, foundation capacity or construction readiness without the required design basis and checks.

## Choosing native CAD primitives

Choose the native feature by the geometry the component actually needs:

- A box is suitable for prismatic envelopes, plates, blocks and packaging placeholders.
- A cylinder is suitable for shafts, pins, rollers, cylindrical bosses, wheel envelopes and round columns. Set its axis explicitly when it is not aligned with the default Z direction.
- A sphere is suitable for balls, spherical knobs and rounded concept components.
- A cone/frustum is suitable for tapered nozzles, transitions and conical components.
- A sketch plus Pad/Pocket is preferable when the user needs a constrained, editable mechanical feature history rather than a single primitive.

Keep separate components as separate named native objects. Use labels/marks to identify each component and native dimensions for its envelope. Never confuse a geometric primitive with a selected material, a manufacturing-ready component, a jointed assembly or an engineered member.

For a vehicle package concept, separate chassis, body and wheel envelopes; use cylinders for wheel geometry and record the scope exclusions. Do not claim suspension kinematics, steering, brakes, drivetrain, crashworthiness, material selection, tolerances or road approval unless those systems have been modelled and checked with the required data.

## Native geometry selection and 3D building shells

Do not confuse a 2D room outline with a 3D architectural wall. Use separate `create_draft_wire` objects for a 2D zoning concept. Use `create_arch_wall` for actual editable native wall geometry when the confirmed path, height and thickness are known. Keep each wall separately named so it can be edited. Room labels and dimensions are annotations, not BIM space objects. Do not claim doors, windows or hosted openings unless a verified native command creates them.

For a wall-shell concept, model the exterior perimeter first, then internal partitions, then labels and dimensions. Recompute/refresh between each native operation. Inspect the resulting wall objects and report missing openings, joins, room boundaries and code checks.

For product and vehicle concepts, select native geometry by shape and role: Part boxes for rectangular packaging envelopes, cylinders for wheels/shafts, spheres for spherical components and cones for tapered components. Keep components separate, named and dimensioned. Primitive geometry is an editable envelope model, not a functional product design.

For a hollow pipe/tube, prefer a native PartDesign annular sketch with explicit outer and inner circles, then Pad the ring profile. Verify that the resulting body is one valid solid and inspect a section or bore dimension. Do not simulate a hollow object by simply placing an inner solid cylinder over an outer cylinder.

For sheet-metal cabinets and equipment housings, do not call a solid outer box a finished hollow enclosure. Either build the base, sides, lid and openings as explicit separate geometry or state that only the external package envelope was created. Electrical clearances, ventilation, earthing, IP protection, heat dissipation and safety testing remain separate design checks.

## Mechanical parts and assemblies

For an individual part:

- Build an editable native PartDesign body/feature tree where the task supports it.
- Create the sketch on the intended origin plane, apply exact supplied dimensions/constraints, then add Pad/Pocket or the appropriate native feature.
- Name features by purpose (BaseProfile, MountingHoleProfile, BasePad, MountingHoles), not generic labels alone.
- Inspect sketch degrees of freedom, body tip, valid solid count, shape validity, bounding dimensions and volume.
- Use parametric expressions when the user has approved named dimensions; preserve exact expression paths.
- Do not infer material, allowable stress, load capacity, safety factor, fits or tolerances from shape alone.

For assemblies:

- Identify the reference component and stable object identities.
- Distinguish existing source parts from newly created parts.
- Use actual interface faces/axes, fastener patterns, clearances and joints from supplied data.
- Report unresolved degrees of freedom and constraints; do not fake a fully constrained assembly.

For existing-design edits, prefer native in-place modification of the target object's approved property or feature. State the exact object and property being changed and report before/after values. If the chosen application has no typed safe edit operation for that property, inspect the native command catalogue and use only a verified command; otherwise explain the limitation and ask for an alternate path.

## Technical drawings and schedules

When drawings are required, use native dimensions, text, leaders, annotations, views, sections, title blocks and schedules where the live application supports them. Include:

- drawing title and revision;
- object/part/element marks;
- material only when supplied/confirmed;
- overall and functional dimensions;
- datum and projection convention where relevant;
- tolerances and GD&T only when specified by the design authority;
- explicit "TBD" items for missing material, finish, standards, tolerances or approval;
- a component/member schedule that links marks to native object identity and describes its role.

Do not label a drawing "approved for manufacture" or "construction issue" without the required review and approval process.

## BIM model execution

A BIM model is geometry plus structured project information. Build and check both:

1. Inspect the current project and native command catalogue.
2. Establish levels/storeys, grids, project units, coordinate reference and vertical datum from the agreed brief/survey.
3. Model the requested native elements: walls, slabs/floors, doors, windows, roofs, columns, beams, stairs, spaces/rooms, MEP systems, site/civil elements and equipment only where live commands support them.
4. Preserve semantic identity and host/containment/connectivity relationships. A drawing line is not automatically a BIM wall; an object visible in 3D is not necessarily a valid room, system or asset.
5. Use query_elements and inspect_model to confirm elements, levels, counts, warnings and properties.
6. Use modify with the exact existing element ID when changing a component. Do not silently delete/recreate an element and lose identity, schedules or relationships.
7. Verify room boundaries, door/window hosting, storey assignment, structural connectivity, MEP connectivity and discipline coordination as appropriate.
8. Use the agreed IFC schema and required property/information rules. Run native validation or the specified IDS/schema checks before claiming exchange conformance.
9. Record missing properties, unclassified elements, open clashes, unresolved survey data and unverified as-built elements as issues, not invented values.

For BIMCraft, use list_commands with a relevant filter to get exact live command identifiers and parameter schemas. For multi-stage tasks use todo_write; perform a coherent stage with execute, inspect/query the updated model, update the checklist and continue. Before editing an existing element, query it and use its returned element ID. The current native assistant may use the application's built-in undo step and project validation; preserve these behaviours.

## Reporting the finished work

The final report should say what native objects were created or edited, their labels/IDs, dimensions, levels or key parameters, and which validation checks actually ran. Separate:
- created and inspected;
- created but not fully verified;
- proposed placeholders;
- not modelled;
- engineering or regulatory review still required.

Never claim a model is editable, saved, reopened, structurally adequate, BIM-valid or construction-ready unless the corresponding native test or inspection has actually established it.
