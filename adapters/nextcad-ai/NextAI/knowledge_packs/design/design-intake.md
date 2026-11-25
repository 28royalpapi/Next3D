# Guided design intake for CAD and BIM

## Purpose

A request such as "make a three-bedroom floor plan", "design a car" or "create a BIM model" expresses the goal, not a complete design specification. Do not rush into geometry. Conduct a short design conversation, preserve what the user has confirmed, ask only for missing information that changes the next design step, and then prepare an explicit brief.

This document is workflow guidance. It is not a source of dimensions, local planning rules, structural design values or proof that a native operation is supported.

## The conversation method

1. Acknowledge the requested object and intended deliverable.
2. Ask a small, relevant group of high-value questions. Avoid presenting a long questionnaire of details that are not yet needed.
3. Track every requirement as confirmed, not supplied, proposed for review, or conflicting.
4. In later turns, use the conversation history. Never ask again for a value the user has already supplied. Ask only about the missing or conflicting items that block the next step.
5. Separate essential inputs from optional preferences. The user may authorise editable placeholders or preliminary proposals, but those must remain clearly labelled and must never be represented as verified design values.
6. Summarise the confirmed design brief before creating a substantial native model. Keep the native plan empty while essential requirements are still being clarified.
7. Use only commands exposed by the current native application. After a plan is approved and executed, inspect the actual model, recompute, validate, and report what succeeded or failed. Do not claim a model exists merely because a plan was proposed.

## Residential floor plans

For a request such as "generate a three-bedroom floor plan", ask about:

- Building form: bungalow or storey house; if storey, how many levels?
- Bedrooms: confirm the requested bedroom count and ask how many are master bedrooms.
- Toilets and bathrooms: ask for the total number of toilet/bathroom rooms and how they are distributed between master ensuites, shared bathrooms and guest WC. Do not assume one toilet per bedroom or confuse the number of bedrooms with the number of bathrooms.
- Living spaces: one sitting/living room, or a formal sitting room plus a separate family lounge?
- Additional rooms: ask which are wanted, for example store, pantry, dining area, laundry, study, guest room, prayer room, maid's room or carport. Do not insert every optional room by default.
- Site and drawing level: ask for plot width and depth, which side faces the road/access, units, and whether the user wants an unscaled schematic or a dimensioned/site-fitted concept.

A practical first response should group those questions naturally. Do not make every minor preference a blocker. If plot dimensions are absent, offer an unscaled relationship/adjacency concept and state that it is not site-fitted or to scale. Do not claim a scaled plan without a known scale and site dimensions.

After the user replies, restate the confirmed room programme, for example: three bedrooms; one master with ensuite; two toilet/bathroom rooms total, one ensuite and one shared; one sitting room; store and dining area; bungalow. Ask only for plot dimensions/road orientation if needed. Room sizes and wall thicknesses may be proposed for review only when the user permits preliminary proposals. Record setbacks, orientation, accessibility, ventilation, wall build-ups and local planning requirements as open checks where they have not been supplied.

A final brief should distinguish confirmed room counts and relationships; proposed room sizes/layout choices; missing site or regulatory information; the next native drawing/model action; and the checks still required.

## Vehicle and product CAD

For "design a car in CAD", establish:

- vehicle class and intended use (for example sedan, SUV, pickup, sports car, van or minibus);
- number of occupants and door/body arrangement;
- target overall length, width, height and wheelbase, or permission to use labelled concept parameters;
- wheel/tyre envelope, ground clearance and key package limits when known;
- powertrain type and layout (electric, hybrid, petrol/diesel; front, rear or all-wheel drive) when relevant;
- desired scope: exterior styling concept, interior package, packaging model, editable assembly, detailed part design or manufacturing drawings.

Use the user's supplied values. If a value is not known, ask whether to leave an editable placeholder or defer that feature. Organise a vehicle model into meaningful components rather than one opaque solid where the requested scope supports it.

A visual vehicle concept is not a roadworthy design. Do not claim crashworthiness, restraint-system adequacy, braking/steering performance, chassis strength, electrical safety or regulatory compliance without verified engineering inputs, qualified review and applicable testing.

For consumer products (furniture, appliances, tools, housings and similar objects), first clarify the product's function, user, size/envelope, important interfaces, moving parts, material preference, manufacturing method and desired deliverable. Do not choose a manufacturing process or tolerance silently.

## Mechanical parts and assemblies

For an individual component, ask what it does, what it attaches to, the measured mating interfaces, available space, loads or operating conditions, material if known, manufacturing method, critical tolerances and whether the result is a visual prototype or a functional/load-bearing part.

For an assembly, clarify the component list, existing versus new components, reference component, mating faces/axes, joint types, allowed degrees of freedom, movement range, fasteners and service access. Use fixed, revolute, prismatic or other constraints only when the intended motion is known. Report unresolved constraints rather than forcing the assembly to appear complete.

For sheet-metal parts and enclosures, clarify internal equipment, envelope, material/thickness if known, mounting points, access panels, bends/flanges, cable openings, ventilation/thermal conditions and fabrication process. Do not claim an IP rating, electrical clearance, grounding adequacy or thermal performance without the required data and checks.

## BIM project intake

A BIM request is not only a request for 3D geometry. Clarify:

- project type, intended use, location and governing jurisdiction;
- source information: survey, drawings, point cloud, existing model, or new-build brief;
- site coordinate reference, vertical datum, units and orientation;
- building levels/storeys, spaces and approximate areas;
- disciplines in scope (architecture, structure, civil/site, HVAC, electrical, plumbing, fire protection, interiors and specialist systems);
- required geometric detail and non-geometric information, using the project's agreed LOD/LOI or equivalent requirements;
- classification/property/asset information and any employer information requirements or IDS;
- schedules, quantities, issue coordination, phasing, handover and other deliverables;
- required IFC schema/version and exchange requirements.

Do not invent coordinates, levels, element classifications, property values or approval status. Distinguish the design model, coordination model, construction model and asset/as-built information model. A model that looks complete may still have missing properties or invalid relationships.

For a renovation, establish how reliable the existing information is. An old drawing or photograph is not automatically a verified as-built model. Ask for measured survey/scan evidence, its date and confidence, what must be retained or protected, and what may be removed or changed. Keep uncertain existing geometry flagged until verified.

## Civil and site design

For roads, drainage, water/sewer networks, bridges, grading and retaining structures, ask for the verified survey and datum, project location/authority, design classification or performance basis, relevant geometry/capacity inputs, ground/geotechnical data, utilities, environmental constraints and required deliverables. Never invent traffic/design speed, soil parameters, water levels, flows, rainfall values, outfall capacity, loads or code clauses. An early schematic model must be labelled schematic, not construction-ready.

## Technical drawings and CAM

For a manufacturing or fabrication drawing, confirm the model revision, units, sheet size/scale, projection method, required orthographic/section/detail views, datum scheme, material, finish, tolerances/GD&T, revision information and the governing drawing standard with jurisdiction and edition. Read dimensions from the verified native model where possible. Leave unspecified tolerances, material and standards as TBD; never invent them or mark a drawing approved for manufacture before review.

For CAM, obtain the actual stock material and dimensions, machine and axis configuration, controller/postprocessor, workholding, work coordinate system, tools and holders, operation requirements, tolerances and surface finish. Feeds, speeds, stepovers and cut depths must come from approved data for the real machine, tool and material. Without the verified setup, prepare only an operation checklist and setup-data template. Do not generate executable toolpaths or controller G-code, or claim collision-free machining, before native simulation and setup review.

## When to proceed

Proceed to a concept when the user's intent and the inputs needed for that concept are clear. If only a schematic is possible, say so and leave unknown dimensions or design properties unresolved. Proceed to dimensioned or detailed modelling only when the necessary dimensions, interfaces and design basis are available or the user explicitly approves clearly labelled provisional parameters.

Always end clarification with a concise next step. Do not turn every request into a long interview, but do not invent the facts needed to produce a reliable design.
