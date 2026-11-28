#!/usr/bin/env python3
"""Authored NextAI project, CAD/BIM operator, and recovery curriculum.

These are L0 learning examples. They are not native execution traces,
engineering approvals, or evidence that the student has learned the tasks.
"""
from __future__ import annotations

import json
from typing import Any

VERSION = "nextai-master-curriculum-v2"
SYSTEM = """You are NextAI, a local engineering design-and-build operator for NextCAD and Next BIM.
Understand the confirmed request, identify blocking unknowns, choose an ordered and reversible
workflow, and state how the native result will be inspected. Use only exact tools and schemas
provided by the live application context; discover unfamiliar commands rather than guessing.
Preserve existing object identity and dependencies when revising a model. Never invent dimensions,
loads, soil parameters, material properties, standards, command names or successful execution.
Separate concept geometry from engineering verification. Ask concise questions for critical
missing inputs. Return a compact structured answer with workflow, checks, risks and limitations;
do not provide hidden chain-of-thought. An operation is not complete until the native application
reports success and its resulting state is inspected."""


# Each specification deliberately changes a real design decision, dependency,
# project stage, validation target, or recovery requirement.
SPECS: list[dict[str, Any]] = [
    # NextCAD / parametric CAD (12)
    {"id":"CAD-001","domain":"cad_parametric_design","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Create a parametric mounting plate: 160 × 100 × 12 mm, four Ø10 mm holes on a 120 × 60 mm rectangular pitch, 12 mm edge distance, and 2 mm external chamfer. The hole positions and plate dimensions must remain editable.",
     "inputs":["plate width=160 mm","plate height=100 mm","thickness=12 mm","hole diameter=10 mm","hole pitch=120 × 60 mm","edge distance=12 mm","chamfer=2 mm"],
     "workflow":["Create a single constrained base sketch from the confirmed datum and dimensions.","Constrain the four hole centres symmetrically and dimension the pitch.","Pad the plate to 12 mm and create through-holes from the sketch or a stable datum.","Apply the chamfer only to the specified external edges after identifying them.","Recompute and inspect the feature dependency tree."],
     "checks":["Sketch is fully constrained without redundant constraints.","One valid solid exists.","Four holes are through-all, correctly located and Ø10 mm.","The feature tree remains editable after save/reopen."],
     "failures":["Over-constrained sketch","Hole pattern references unstable generated edges","Chamfer fails after topology changes"],
     "limits":["Geometry acceptance does not establish fatigue capacity, bearing, bolt design or material suitability."]},
    {"id":"CAD-002","domain":"cad_surface_and_solid_modelling","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Model a hollow cylindrical instrument enclosure with 180 mm outside diameter, 240 mm overall height, 4 mm nominal wall, a removable top cover and six equally spaced mounting bosses. Keep body, cover and bosses as separately editable components.",
     "inputs":["outside diameter=180 mm","height=240 mm","wall=4 mm","six bosses","cover removable"],
     "workflow":["Confirm whether dimensions describe the clear internal envelope or external envelope; here outside diameter is confirmed.","Create the cylindrical shell with explicit wall thickness and base geometry.","Create a separate cover and define its interface and fastening locations.","Pattern six bosses around a stable axis and keep them separate or linked instances.","Inspect wall thickness, intersections, clearances and component identities."],
     "checks":["Body and cover are distinct editable objects.","Wall thickness is measured rather than inferred from appearance.","Bosses are evenly distributed and do not intersect the cover interface.","Assembly fits and survives recompute."],
     "failures":["Shell operation produces invalid faces","Boss pattern uses unstable edge references","Cover/body overlap"],
     "limits":["No ingress, pressure, impact, thermal or electrical protection rating is implied."]},
    {"id":"CAD-003","domain":"cad_revolved_components","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Create a rotationally symmetric storage vessel concept from a supplied half-section: straight cylindrical body, tapered shoulder, neck and base ring. Preserve the supplied section dimensions and keep the revolve axis explicit.",
     "inputs":["approved half-section drawing","datum axis","millimetre units","part is a concept model"],
     "workflow":["Inspect the supplied section and verify it is a closed, non-self-intersecting profile.","Identify the intended axis and coordinate reference.","Create a constrained sketch and revolve it through the specified angle.","Create the base ring and neck interface as separate features where appropriate.","Inspect section continuity, wall-thickness intent and the feature tree."],
     "checks":["Profile is closed and non-self-intersecting.","Revolve axis is explicit and aligned with the approved datum.","Result is a valid solid with no unintended zero-thickness regions.","Source dimensions remain traceable."],
     "failures":["Open profile","Axis mismatch","Self-intersection at shoulder transition"],
     "limits":["Do not infer pressure rating, mouldability, food-contact compliance or structural integrity."]},
    {"id":"CAD-004","domain":"cad_sweep_and_routing","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Create an editable routed pipe-centreline model between two supplied connection points with a specified nominal diameter, bend radius and route clearance envelope. The route must be editable without rebuilding the whole part.",
     "inputs":["source and destination connector frames","pipe outside diameter","minimum bend radius","clearance envelope","route datum"],
     "workflow":["Inspect endpoint frames, units and the obstacles in the current model.","Check that the proposed route satisfies the minimum bend radius and clearance envelope.","Create a stable centreline path with explicit tangent transitions.","Sweep the pipe profile along the centreline and retain the path as an editable dependency.","Inspect continuity, end alignment, self-intersection and clearance."],
     "checks":["Both endpoints coincide with the specified connector frames within tolerance.","Bend radii meet the supplied minimum.","Swept solid is valid and non-self-intersecting.","Route remains editable through its centreline."],
     "failures":["Discontinuous path","Sweep twist or self-intersection","Route collides with an obstacle"],
     "limits":["Do not size flow, pressure class, supports or thermal expansion without separate design inputs."]},
    {"id":"CAD-005","domain":"cad_mechanical_gears","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Prepare a parametric spur-gear pair concept with a specified module, tooth counts, pressure angle, face width and shaft centre distance. Include a ratio check and preserve separate editable gears.",
     "inputs":["module","driver and driven tooth counts","pressure angle","face width","shaft centre-distance requirement","shaft/bore interfaces"],
     "workflow":["Confirm units, tooth counts, module system and pressure angle.","Calculate the nominal ratio and pitch diameters from the supplied gear convention.","Compare the derived centre distance with the supplied requirement and flag any mismatch.","Build each gear as a separate editable component and position them on defined shaft axes.","Inspect tooth engagement envelope, bore interfaces and assembly clearances."],
     "checks":["Gear ratio matches the tooth-count ratio.","Derived pitch geometry is internally consistent.","Gear bodies remain separate and editable.","Centre-distance mismatch is reported rather than hidden."],
     "failures":["Incompatible module or pressure angle","Incorrect axis spacing","Interference between tooth envelopes"],
     "limits":["A visual tooth model is not proof of contact stress, wear life, lubrication or manufacturing accuracy."]},
    {"id":"CAD-006","domain":"cad_sheet_metal","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Design a folded sheet-metal electrical enclosure from a supplied flat pattern and bend schedule. Preserve material thickness, bend radius, bend directions, reliefs, mounting flanges and the developed blank.",
     "inputs":["flat-pattern geometry","material and thickness","inside bend radius","bend angle schedule","relief rules","manufacturing process"],
     "workflow":["Validate the supplied flat boundary and bend-line references.","Confirm material thickness, bend radii, K-factor or bend-table source and units.","Create base, flange and bend features in a stable feature sequence.","Generate the developed flat pattern from the native sheet-metal model.","Check collisions, bend reliefs, edge distances and agreement with the supplied blank."],
     "checks":["Folded and flat states are both available.","Bend angle/radius/thickness match the supplied schedule.","No self-intersection or impossible bend remains.","Manufacturing assumptions are explicitly reported."],
     "failures":["Bend radius below process limit","Overlapping flanges","Flat pattern differs from approved blank"],
     "limits":["Do not assert manufacturability without the actual material/process bend data."]},
    {"id":"CAD-007","domain":"cad_assembly_and_motion","application":"nextcad","stage":"cad_fluency","task_type":"create",
     "prompt":"Assemble a motor, coupling, shaft, two bearings and a driven pulley using supplied component files and interface dimensions. Preserve component identities and define only the intended degrees of freedom.",
     "inputs":["component files","shaft and bore dimensions","bearing seat positions","coupling interface","pulley alignment datum","intended motion"],
     "workflow":["Inspect each component's origin, coordinate system and mating interfaces.","Check shaft/bore compatibility and the bearing seat arrangement.","Insert components as instances and constrain the motor, bearings and pulley to their datums.","Constrain the coupling and shaft without over-constraining intended rotation.","Run fit/interference checks and document unresolved clearances."],
     "checks":["All components retain stable identities and source references.","Shaft, bearings, coupling and pulley are coaxial as specified.","Intended rotation remains free and other rigid-body motion is constrained.","Interference report is reviewed."],
     "failures":["Over-constrained assembly","Mismatched bore/shaft sizes","Lost component link"],
     "limits":["Assembly fit does not establish bearing life, shaft strength, balance or operating safety."]},
    {"id":"CAD-008","domain":"cad_technical_documentation","application":"nextcad","stage":"cad_fluency","task_type":"document",
     "prompt":"Produce a controlled engineering drawing for an approved machined bracket with front, top, side and isometric views, dimensions, hole callouts, material note, revision and title block.",
     "inputs":["approved native part","drawing template","projection convention","units","dimension/tolerance requirements","revision metadata"],
     "workflow":["Confirm the source model revision and drawing standard.","Create orthographic and isometric views linked to the native model.","Place functional dimensions and hole callouts without duplicate or ambiguous measurements.","Add material, general tolerance, revision and title-block metadata only from approved sources.","Recompute the drawing and check view updates against the model."],
     "checks":["Views reference the approved source model.","Dimensions reconcile with native geometry.","Projection convention and units are explicit.","Revision and title-block fields are complete or flagged missing."],
     "failures":["Stale view after model revision","Dimension attached to unstable geometry","Missing tolerance source"],
     "limits":["A drawing is not a release-for-manufacture document without approved tolerances and sign-off."]},
    {"id":"CAD-009","domain":"cad_fem_preprocessing","application":"nextcad","stage":"engineering_analysis","task_type":"analysis",
     "prompt":"Prepare an FEM model of a bracket using the supplied material data, load case, restraint locations and mesh criteria. Stop if a required material property or boundary condition is missing.",
     "inputs":["native solid","material elastic properties","load magnitudes/directions","restraint locations","contact assumptions","mesh size/convergence criterion"],
     "workflow":["Inspect solid validity, units, thin regions and intended load path.","Check material properties and boundary conditions for completeness and physical meaning.","Define a mesh strategy with local refinement at stress concentrations.","Create analysis constraints and loads only from the approved case.","Run mesh-quality and model-completeness checks before solving."],
     "checks":["Material and unit systems are consistent.","Loads and restraints are traceable to the supplied case.","Mesh-quality metrics meet the stated criteria.","Missing contact or nonlinear assumptions are disclosed."],
     "failures":["Rigid-body motion","Poor-quality elements","Unrealistic restraint or load application"],
     "limits":["Pre-processing is not a solved analysis; solver convergence and independent result review are separate gates."]},
    {"id":"CAD-010","domain":"cad_cam_preparation","application":"nextcad","stage":"manufacturing","task_type":"create",
     "prompt":"Prepare a CAM setup for a prismatic bracket using the supplied stock, machine envelope, cutter list, work offset, material and approved machining strategy. Do not generate controller-specific output without machine/post details.",
     "inputs":["part and stock geometry","machine/controller","tool library","work offset","material","strategy and tolerances","post-processor"],
     "workflow":["Verify the part revision, stock dimensions and machine envelope.","Validate the selected cutters against material, reach and holder clearance.","Define work coordinate system and setup orientation.","Create roughing, finishing and drilling operations with explicit allowances.","Simulate toolpaths and inspect collisions, remaining stock and post-processor compatibility."],
     "checks":["Stock encloses the intended workpiece.","Tool reach and holder clearance are valid.","Simulation reports no unreviewed collision.","Post-processor and controller match the target machine."],
     "failures":["Tool/holder collision","Incorrect work offset","Unsupported post-processor"],
     "limits":["A CAM simulation is not a guarantee of safe machine operation; verify setup and NC code on the actual machine."]},
    {"id":"CAD-011","domain":"cad_mesh_repair","application":"nextcad","stage":"geometry_validation","task_type":"edit",
     "prompt":"Inspect an imported triangulated mesh intended for conversion to a solid. Diagnose open boundaries, non-manifold edges, duplicate faces, inverted normals and scale before attempting repair.",
     "inputs":["source mesh","known unit/scale","target tolerance","intended downstream operation"],
     "workflow":["Preserve the source mesh and inspect its bounding box, units and topology.","Report boundary, non-manifold, duplicate and degenerate elements.","Repair only defects with a clear local interpretation; quarantine ambiguous geometry.","Recheck topology and compare volume/area/bounds before conversion.","Convert to a solid only when closure and tolerance requirements are met."],
     "checks":["Original source remains unchanged.","Topology defect counts are recorded before and after repair.","Scale and units are confirmed.","Converted solid passes validity and volume sanity checks."],
     "failures":["Non-manifold topology","Scale mismatch","Repair changes intended geometry"],
     "limits":["Automatic healing must not silently alter design-critical surfaces."]},
    {"id":"CAD-012","domain":"cad_parametric_revision","application":"nextcad","stage":"revision_and_recovery","task_type":"edit",
     "prompt":"Revise an existing bracket by changing the hole spacing and plate width while preserving the original document, body, feature names, downstream drawing links and unrelated components.",
     "inputs":["existing native document","requested new width and hole spacing","approved object identifiers","required unchanged properties"],
     "workflow":["Inspect the current feature tree and identify the driving parameters.","Confirm the target body and dependent features by stable identifiers.","Edit the driving sketch parameters in place rather than replacing the body.","Recompute and inspect downstream features and drawing links.","Save to a revision copy, reopen it and compare identities and geometry."],
     "checks":["Original file remains recoverable.","Target body identity is preserved.","Unrelated components are unchanged.","All dependent features recompute and drawing links update."],
     "failures":["Broken edge references","Failed recompute","Unexpected change to unrelated geometry"],
     "limits":["Do not claim a successful revision until save/reopen and identity comparison pass."]},

    # Next BIM / information modelling (12)
    {"id":"BIM-001","domain":"bim_levels_grids","application":"nextbim","stage":"bim_fluency","task_type":"create",
     "prompt":"Set up a four-storey building datum system from the approved survey origin: ground, first, second, roof levels and structural grid lines. Retain the source coordinates and level elevations.",
     "inputs":["survey origin and rotation","four approved elevations","grid spacing and labels","project units","coordinate reference system"],
     "workflow":["Inspect the current project datum and coordinate reference.","Create levels from approved elevations and name them consistently.","Create orthogonal grids using the supplied spacing and labels.","Verify grid intersections and level relationships before placing elements.","Record coordinate transformation and source survey metadata."],
     "checks":["Levels have exact supplied elevations.","Grid labels and spacing are unique and consistent.","Project origin and rotation match survey control.","No level or grid is silently shifted."],
     "failures":["Mixed units","Duplicate grid labels","Project north/true north confusion"],
     "limits":["A BIM datum setup is not a verified land survey or setting-out approval."]},
    {"id":"BIM-002","domain":"bim_residential_architecture","application":"nextbim","stage":"bim_fluency","task_type":"create",
     "prompt":"Develop a three-bedroom bungalow BIM model from an approved room schedule and site boundary, including external/internal walls, doors, windows, spaces, roof and room schedule.",
     "inputs":["approved floor plan and room schedule","site boundary/orientation","wall types and thicknesses","opening schedule","floor and roof levels","deliverable requirements"],
     "workflow":["Inspect project units, levels, grids and site boundary.","Place external and internal walls using approved types and dimensions.","Create hosted doors and windows against the correct wall identifiers.","Define spaces and verify room boundaries/areas.","Add floor and roof elements, then generate schedules and views."],
     "checks":["All required rooms exist and match the approved schedule.","Openings are hosted by intended walls.","Wall types and level assignments are correct.","Schedules reconcile to model elements."],
     "failures":["Unbounded room","Opening loses host","Overlapping or disconnected walls"],
     "limits":["Spatial modelling does not establish planning approval, accessibility compliance or structural adequacy."]},
    {"id":"BIM-003","domain":"bim_multistorey_residential","application":"nextbim","stage":"bim_fluency","task_type":"create",
     "prompt":"Create a four-storey apartment BIM model with a ground floor, three residential levels, stairs, lift core, risers and roof plant. Typical floors may repeat, but each level must remain individually editable.",
     "inputs":["floor plate and unit schedule","storey elevations","stair/lift core dimensions","structural grid","shaft/riser requirements","roof plant zones"],
     "workflow":["Establish project levels, grid and core datums.","Model a typical floor with spaces, partitions, openings and circulation.","Create controlled instances or equivalent level-aware copies for repeated floors.","Model unique ground, roof and plant-floor conditions separately.","Coordinate stair continuity, lift shaft, risers and structural framing."],
     "checks":["Each storey has correct elevation and distinct identity.","Stairs and lift core connect the intended levels.","Risers remain continuous where required.","Repeated floors are editable without unintentionally altering unique floors."],
     "failures":["Duplicate element identifiers","Disconnected stair run","Riser collision with structure"],
     "limits":["A coordinated concept model is not a code-compliant high-rise design."]},
    {"id":"BIM-004","domain":"bim_structural_model","application":"nextbim","stage":"bim_fluency","task_type":"create",
     "prompt":"Build a structural BIM framing model from a reviewed engineer's grid and member schedule: columns, beams, slabs, footings and bracing. Maintain analytical-to-physical correspondence where supported.",
     "inputs":["structural grid and levels","member schedule and section types","material grades","connection assumptions","load/analysis reference","foundation layout"],
     "workflow":["Inspect the approved structural grid and member schedule.","Place columns and footings with consistent alignment and level constraints.","Add beams, bracing and slabs while preserving member identifiers.","Check connectivity, offsets and framing continuity.","Record which analytical properties are populated and which remain unresolved."],
     "checks":["Members match the supplied schedule and material grades.","Beam/column connections are geometrically consistent.","Load paths and supports are inspectable.","Analytical assumptions are not invented."],
     "failures":["Disconnected framing","Incorrect member orientation","Analytical line offset mismatch"],
     "limits":["Physical BIM geometry is not structural analysis or code verification."]},
    {"id":"BIM-005","domain":"bim_healthcare_facility","application":"nextbim","stage":"integrated_bim","task_type":"create",
     "prompt":"Develop a small outpatient clinic BIM model from a room/data brief, including consultation rooms, waiting, treatment, accessible circulation, sanitary spaces, equipment zones and coordinated MEP.",
     "inputs":["room data sheets","occupancy and functional relationships","site/access brief","approved accessibility criteria","equipment envelopes","MEP design criteria"],
     "workflow":["Classify rooms by function, adjacency and required environmental services.","Establish circulation, access and controlled/clinical zones from approved criteria.","Create spaces, partitions, openings and equipment envelopes.","Coordinate ventilation, electrical, plumbing and medical-service zones with structure.","Generate room and equipment schedules and a coordination issue list."],
     "checks":["All required spaces and adjacency constraints are represented.","Equipment envelopes fit their intended rooms.","MEP service zones are coordinated with structure.","Unknown clinical and regulatory criteria are flagged."],
     "failures":["Missing room data","Service route crosses a restricted zone","Clash with structural member"],
     "limits":["The model is not healthcare licensing, infection-control or medical-gas certification."]},
    {"id":"BIM-006","domain":"bim_mep_systems","application":"nextbim","stage":"integrated_bim","task_type":"coordinate",
     "prompt":"Coordinate domestic water, drainage, ventilation and electrical systems through a multi-room building. Use the supplied loads, equipment schedules and connector data; do not invent pipe, cable or duct sizing.",
     "inputs":["approved equipment schedule","system design criteria","connector locations and types","loads/flows/air volumes","clearance rules","level and shaft layout"],
     "workflow":["Discover the current native command catalogue and relevant model objects.","Inspect connectors, equipment and served spaces.","Build system membership and routes from supplied connector compatibility.","Check levels, gradients, clearances and service-zone coordination.","Inspect unresolved connections and create a discipline-owned issue list."],
     "checks":["Systems have correct classification and membership.","Connections use compatible connector types.","Required gradients and clearances are checked against supplied values.","Open ends and unserved terminals are reported."],
     "failures":["Connector mismatch","Unintended open end","Duct/beam clash"],
     "limits":["BIM connectivity does not establish hydraulic, electrical or ventilation performance."]},
    {"id":"BIM-007","domain":"bim_clash_and_coordination","application":"nextbim","stage":"integrated_bim","task_type":"coordinate",
     "prompt":"Resolve a reported HVAC duct clash with a structural beam without silently moving either element. Record the issue, inspect both elements, propose alternatives and verify the approved resolution.",
     "inputs":["issue location/viewpoint","duct and beam identifiers","clearance/tolerance rules","discipline owners","approved design alternatives"],
     "workflow":["Inspect the issue and query exact duct/beam identifiers and geometry.","Confirm whether the intersection is a true clash or an intentional crossing under the stated tolerance.","Capture the current state and classify the responsible disciplines.","Present options such as route change or coordinated opening for authorised review.","Apply only the approved revision and rerun the clash check."],
     "checks":["Element identities are preserved unless a replacement is approved.","The approved clearance is achieved.","The issue retains before/after evidence and responsibility.","No structural change is made without engineering approval."],
     "failures":["False-positive clash","Edit affects wrong element","Unapproved structural modification"],
     "limits":["NextAI cannot approve structural openings or alter safety-critical systems autonomously."]},
    {"id":"BIM-008","domain":"bim_schedules_quantities","application":"nextbim","stage":"bim_delivery","task_type":"document",
     "prompt":"Produce schedules for doors, windows, walls, rooms and maintainable equipment from the native BIM model. Preserve stable identifiers and show unclassified items as exceptions.",
     "inputs":["approved schedule definitions","property/quantity measurement rules","element categories","units","required asset fields"],
     "workflow":["Inspect the model and approved schedule field definitions.","Query elements by type, level, phase and classification.","Read quantities from native geometry/properties with stated measurement rules.","Separate type-level information from instance values.","Reconcile totals and produce an exceptions register for missing fields."],
     "checks":["Every scheduled element has a stable identifier.","Units and measurement conventions are explicit.","Totals reconcile with selected model objects.","Unclassified or missing-property elements remain visible."],
     "failures":["Duplicate identifiers","Stale quantity after geometry change","Missing type/instance distinction"],
     "limits":["A quantity schedule is not a priced bill of quantities without rates, waste rules and commercial basis."]},
    {"id":"BIM-009","domain":"bim_ifc_interoperability","application":"nextbim","stage":"bim_delivery","task_type":"export",
     "prompt":"Prepare an IFC exchange model from the coordinated project using the agreed IFC schema, spatial hierarchy, element classifications, properties and coordinate reference. Validate the export by reopening it.",
     "inputs":["exchange requirement/IFC schema","project coordinate system","spatial hierarchy","classification mapping","required property sets","export scope"],
     "workflow":["Inspect the model's spatial containment and element typing.","Map each required native category to the agreed IFC entity/classification.","Check property sets, units, materials and stable global identifiers.","Export to the specified IFC schema and record exporter/version settings.","Reopen the IFC in an independent parser/viewer and compare counts, relationships and coordinates."],
     "checks":["IFC file parses successfully.","Spatial hierarchy and containment are preserved.","Required types/properties and coordinates survive round-trip.","Missing mappings and lossy fields are reported."],
     "failures":["Unsupported IFC entity","Missing property set","Coordinate transform mismatch"],
     "limits":["A successful export does not guarantee client information-requirement acceptance."]},
    {"id":"BIM-010","domain":"bim_existing_building_renovation","application":"nextbim","stage":"revision_and_recovery","task_type":"edit",
     "prompt":"Renovate an existing occupied building by changing selected partitions and replacing two doors while retaining the identity and host relationships of all unaffected elements.",
     "inputs":["existing model","survey/reality-capture confidence","approved demolition/new-work scope","target element identifiers","phasing rules"],
     "workflow":["Inspect the existing model's source, date and reliability by element.","Query the target partitions and hosted openings by stable identifiers.","Classify retain, demolish and new work using explicit phases.","Modify only approved targets in place and update affected hosts.","Compare before/after IDs, relationships, quantities and views."],
     "checks":["Unaffected elements retain identifiers and properties.","Door openings remain hosted by the intended walls.","Demolition/new work phases are correct.","Unverified existing conditions are labelled."],
     "failures":["Wrong target selected","Door host lost","Existing model accuracy overestimated"],
     "limits":["Modelled existing conditions are not field-verified as-built information."]},
    {"id":"BIM-011","domain":"bim_highrise_floor_variation","application":"nextbim","stage":"integrated_bim","task_type":"create",
     "prompt":"Model a ten-storey mixed-use building with a podium, typical residential floors, a transfer level, plant floor, roof and two basement levels. Do not copy one floor blindly across all levels.",
     "inputs":["approved floor-by-floor space programme","level elevations","grid and transfer structure","core/riser strategy","podium and basement layouts","plant requirements"],
     "workflow":["Establish levels, grids, basement extents and the principal core.","Model unique podium, transfer, plant, roof and basement conditions independently.","Create a typical residential floor and controlled copies only for genuinely repeated levels.","Track changes in grids, shafts, structure and service risers at the transfer level.","Inspect continuity and coordination at every unique transition."],
     "checks":["All twelve level conditions are represented as specified.","Unique floors have distinct editable identities.","Core, stairs and lifts connect correctly.","Transfer/plant levels are reviewed separately."],
     "failures":["Blind repetition over a unique transfer floor","Riser discontinuity","Level/elevation mismatch"],
     "limits":["The BIM model is not proof of high-rise structural, fire, vertical-transport or regulatory adequacy."]},
    {"id":"BIM-012","domain":"bim_site_and_georeferencing","application":"nextbim","stage":"bim_delivery","task_type":"coordinate",
     "prompt":"Coordinate a building model with surveyed site boundaries, levels, access road and utility corridors. Preserve the source coordinate system and record every transformation.",
     "inputs":["survey control points","coordinate reference system","site boundary and topography","utility records and confidence","building placement","north/orientation"],
     "workflow":["Inspect source survey units, datum and coordinate reference.","Validate control points and transformation parameters.","Place site/building geometry using an explicit transformation.","Overlay access, utilities and topography with source confidence metadata.","Check boundary offsets, elevations and coordinate round-trip."],
     "checks":["Control points match the supplied tolerance.","Transformation parameters are stored and reproducible.","Utility confidence and unknowns are visible.","Building orientation and site offsets reconcile."],
     "failures":["Local/global coordinate mix-up","Wrong elevation datum","Unverified utility interpreted as exact"],
     "limits":["Model coordination is not a legal cadastral survey or underground-service clearance."]},

    # Engineering disciplinary learning (16)
    {"id":"ENG-001","domain":"engineering_structural_concrete_beams","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Prepare a reinforced-concrete beam design workflow from a stated span, support condition, load schedule, concrete/steel grades, cover, exposure class and governing design standard. Show what must be checked before reinforcement is detailed.",
     "inputs":["span and support conditions","dead/live load schedule and combinations","concrete and reinforcement grades","section/depth constraints","cover/exposure/fire requirements","governing code edition"],
     "workflow":["Confirm load path, support idealisation and governing combinations.","Determine actions using a stated analysis method and verify equilibrium.","Check section classification and flexural resistance under the selected code.","Check shear, serviceability deflection/crack control, anchorage, curtailment and detailing rules.","Record all assumptions and obtain independent design review before detailing."],
     "checks":["Units and load combinations are consistent.","Flexure, shear and serviceability are all addressed.","Development/anchorage and cover are checked.","Code clauses and factors come from the named edition."],
     "failures":["Unsupported load combination","Incorrect effective depth","Shear/detailing omitted"],
     "limits":["No reinforcement quantity or adequacy can be certified without complete inputs and verified code implementation."]},
    {"id":"ENG-002","domain":"engineering_structural_slabs","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Assess a reinforced-concrete slab panel supported on four edges. Establish whether one-way or two-way action applies, identify the selected design method and gather panel dimensions, support continuity, loading, material grades and code basis.",
     "inputs":["effective panel dimensions and aspect ratio","edge support/continuity","load schedule","material grades","cover and fire/exposure","design code and edition"],
     "workflow":["Check support conditions and panel aspect ratio for the chosen code method.","Establish effective span, load combinations and load distribution assumptions.","Determine design moments using the appropriate coefficient or analysis method.","Check flexure in both directions, shear, deflection, cracking and minimum/distribution steel.","Detail top/bottom reinforcement, anchorage, openings and local support zones."],
     "checks":["One-way/two-way classification is justified by support and geometry.","Moment method and coefficients match the stated code edition.","Both directions and serviceability are addressed.","Openings and support zones receive separate checks."],
     "failures":["Wrong aspect ratio or support model","Incorrect effective span","Punching/local shear overlooked"],
     "limits":["A conceptual slab layout is not a construction-ready reinforcement design."]},
    {"id":"ENG-003","domain":"engineering_structural_columns","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Assess a reinforced-concrete column with supplied axial force, moments, end restraints, effective length, section dimensions, reinforcement layout, material grades and design code.",
     "inputs":["N*, Mx*, My* and combinations","unsupported/effective lengths","end restraint and bracing","section and reinforcement layout","material grades","code edition"],
     "workflow":["Confirm whether the column is braced/unbraced and identify end conditions.","Determine effective lengths and slenderness in both axes.","Check minimum eccentricity and second-order effects where required.","Assess axial-flexural interaction and reinforcement limits under the named code.","Check detailing, confinement, lap/anchorage and foundation interface."],
     "checks":["Both axes and all governing combinations are considered.","Slenderness and second-order rules are applied correctly.","Interaction resistance and detailing limits are checked.","Input load provenance is recorded."],
     "failures":["Assuming fixed ends without evidence","Omitting biaxial moment","Confusing design and characteristic loads"],
     "limits":["Do not infer load capacity from gross section dimensions alone."]},
    {"id":"ENG-004","domain":"engineering_geotechnical_foundations","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Develop a shallow-foundation assessment from a geotechnical investigation, column/wall reactions, groundwater level, footing geometry, neighbouring foundations and settlement criteria.",
     "inputs":["borehole/CPT/SPT data and interpreted strata","groundwater level/seasonal range","loads and eccentricities","footing dimensions/depth","nearby foundations/slopes/services","settlement limits and code basis"],
     "workflow":["Review investigation coverage and whether soil parameters represent the founding stratum.","Establish gross/net bearing pressure including eccentricity and groundwater effects.","Check bearing resistance using an identified theory and stated factors.","Assess total/differential settlement and construction/groundwater constraints.","Compare alternative foundation types and identify further investigation needs."],
     "checks":["Bearing and settlement are separate limit states.","Effective dimensions/eccentricity are applied consistently.","Groundwater and nearby features are considered.","Missing parameters are not replaced with guessed values."],
     "failures":["Using average pressure with significant eccentricity","Ignoring groundwater","Treating one borehole as a uniform site profile"],
     "limits":["Preliminary assessment is not a geotechnical design approval or construction instruction."]},
    {"id":"ENG-005","domain":"engineering_geotechnical_settlement","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Select and document an appropriate settlement assessment for a layered soil profile beneath a footing, distinguishing immediate, primary consolidation and secondary compression components.",
     "inputs":["layer thicknesses and sequence","stress history and OCR","e0, Cc/Cr or mv","cv and drainage path","groundwater and effective stresses","foundation pressure distribution"],
     "workflow":["Build the stratigraphic and groundwater model from investigation data.","Calculate initial effective stress and stress increment by layer.","Select immediate and consolidation methods appropriate to soil type and stress history.","Estimate time rate using drainage path and cv where available.","Report settlement components, sensitivity and limitations."],
     "checks":["Stress units and layer boundaries are consistent.","Normally/over-consolidated response is distinguished.","Drainage boundary conditions are explicit.","Time-rate estimate is not confused with ultimate settlement."],
     "failures":["Using Cc for over-consolidated recompression without checking","Wrong drainage path","Ignoring layered profile"],
     "limits":["Simplified one-dimensional methods do not cover every 3D or ground-improvement problem."]},
    {"id":"ENG-006","domain":"engineering_retaining_structures","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Assess a retaining wall using supplied retained height, soil unit weight, friction angle, cohesion assumptions, surcharge, groundwater, wall friction, geometry and foundation parameters.",
     "inputs":["wall geometry and restraint","soil stratigraphy and design parameters","surcharge and adjacent structures","groundwater/drainage","base friction/passive resistance","foundation bearing and settlement criteria"],
     "workflow":["Identify wall movement condition and choose active, at-rest or passive earth pressure model.","Calculate lateral pressure components and resultant locations.","Include water pressure and verify drainage assumptions.","Check sliding, overturning, bearing, global stability and structural actions.","Identify temporary construction stages and instrumentation needs."],
     "checks":["Earth-pressure state matches wall movement/restraint.","Water pressure is treated separately from effective soil pressure.","All external stability checks are addressed.","Passive resistance assumptions are justified."],
     "failures":["Using active pressure for a restrained wall","Omitting hydrostatic pressure","Double-counting surcharge"],
     "limits":["No wall reinforcement or construction detail is approved by this workflow alone."]},
    {"id":"ENG-007","domain":"engineering_pile_foundations","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Plan a pile foundation assessment from pile type, installation method, borehole/CPT data, groundwater, axial/lateral loads, group layout, settlement criteria and negative skin-friction risk.",
     "inputs":["ground investigation","pile type, diameter and length","axial/lateral load cases","group spacing and layout","downdrag/negative skin friction","testing and construction constraints"],
     "workflow":["Confirm stratigraphy, groundwater and installation method.","Estimate shaft and base resistance using a method suited to the soil and pile type.","Check structural pile resistance, group effects and settlement.","Assess lateral response, downdrag, scour or other site-specific effects.","Define required static/dynamic/load testing and integrity checks."],
     "checks":["Geotechnical and structural resistance are distinct.","Group effects and settlement are considered.","Installation method matches the resistance method.","Testing requirements are specified."],
     "failures":["Applying one empirical factor to every soil type","Ignoring downdrag","Confusing single-pile and group capacity"],
     "limits":["Empirical methods require local calibration and investigation quality review."]},
    {"id":"ENG-008","domain":"engineering_slope_stability","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Set up a slope-stability assessment for a cut slope with layered soils, groundwater, slope geometry, surcharge and proposed construction stages. Compare critical slip surfaces and sensitivity.",
     "inputs":["surveyed slope geometry","soil strength and unit weights by layer","groundwater/pore-pressure model","surcharge and loads","construction sequence","target factors and code criteria"],
     "workflow":["Build a consistent geometry and stratigraphy model.","Select an appropriate limit-equilibrium or numerical method and state assumptions.","Define pore-pressure distribution and search potential slip surfaces.","Evaluate construction and long-term cases with sensitivity to groundwater and strength.","Identify drainage, reinforcement and monitoring options for specialist review."],
     "checks":["Critical surface search covers plausible mechanisms.","Pore pressures match the stated groundwater model.","Construction stages and surcharge are represented.","Sensitivity and parameter uncertainty are reported."],
     "failures":["Using dry strength with elevated groundwater","Restricting search to one assumed slip circle","Mixing peak and residual strengths"],
     "limits":["A single factor of safety is not a complete slope-risk assessment."]},
    {"id":"ENG-009","domain":"engineering_road_geometry","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Develop a preliminary road-alignment workflow from survey control, design speed, terrain, traffic, cross-section requirements, drainage outlets and right-of-way constraints.",
     "inputs":["survey and coordinate system","design speed and road class","horizontal/vertical alignment criteria","terrain and geotechnical data","traffic and pavement criteria","right-of-way/utilities/drainage"],
     "workflow":["Validate survey datum and terrain completeness.","Establish alignment control points and corridor constraints.","Check horizontal curves, transition requirements, grades, vertical curves and sight distance against the named standard.","Develop typical cross-sections, earthworks and drainage interfaces.","Compare alternatives and record environmental, utility and land constraints."],
     "checks":["Units and stationing are consistent.","Horizontal and vertical geometry meet the supplied criteria.","Sight distance and crossfall are checked.","Earthworks and drainage connect to feasible outlets."],
     "failures":["Wrong design-speed criterion","Vertical curve conflicts with drainage","Survey datum mismatch"],
     "limits":["Preliminary geometry does not establish statutory road approval or pavement performance."]},
    {"id":"ENG-010","domain":"engineering_stormwater_drainage","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Plan a stormwater drainage system for a defined catchment using surveyed areas, runoff coefficients, rainfall intensity/duration, design return period, allowable discharge and outfall level.",
     "inputs":["catchment delineation and areas","surface types/runoff coefficients","IDF source and return period","time of concentration","outfall/tailwater level","allowable discharge and design criteria"],
     "workflow":["Delineate subcatchments and verify contributing areas.","Select rainfall intensity from the approved IDF source and duration basis.","Estimate peak flows with the stated method and document its limits.","Size/grade channels or pipes using roughness, hydraulic capacity and cover constraints.","Check inlet capture, surcharge, tailwater, exceedance routes and maintenance access."],
     "checks":["Catchment areas sum correctly.","Rainfall duration and return period match the design basis.","Hydraulic grade and outfall conditions are checked.","Exceedance routing and blockage scenarios are addressed."],
     "failures":["Using intensity without matching duration","Double-counting subcatchment area","Ignoring tailwater"],
     "limits":["Rational Method peak flow alone is not a complete hydrograph or flood-risk study."]},
    {"id":"ENG-011","domain":"engineering_open_channel_flow","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Assess a lined trapezoidal channel using supplied side slopes, bed width, depth, longitudinal slope, roughness, design flow and freeboard criterion.",
     "inputs":["channel section geometry","bed slope and roughness","design discharge","tailwater/control levels","freeboard criterion","lining and erosion limits"],
     "workflow":["Check section geometry, hydraulic radius and units.","Use the specified open-channel method to determine capacity/depth.","Check velocity against lining and erosion/sediment constraints.","Assess freeboard, transitions, bends, energy dissipation and outlet conditions.","Document whether uniform-flow assumptions are appropriate."],
     "checks":["Area, wetted perimeter and hydraulic radius are correct.","Capacity meets design flow with required freeboard.","Velocity limits and transition losses are considered.","Tailwater/control conditions are identified."],
     "failures":["Using wrong hydraulic radius","Ignoring supercritical transitions","Confusing normal and critical depth"],
     "limits":["Uniform-flow capacity is not a full unsteady flood-routing analysis."]},
    {"id":"ENG-012","domain":"engineering_pumping_systems","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Develop a pump-system selection brief from required flow, static lift, pipe route, fittings, fluid properties, operating schedule, power supply and redundancy requirement.",
     "inputs":["duty flow and operating cases","static levels/lift","pipe lengths/diameters/materials","fittings and valves","fluid temperature/viscosity","pump curves and NPSH data","power and redundancy"],
     "workflow":["Define duty points and credible operating cases.","Calculate system head including static and friction/minor losses.","Intersect system curve with candidate pump curves.","Check operating region, NPSH margin, motor power and efficiency.","Assess controls, standby philosophy, transient risks and maintainability."],
     "checks":["Duty flow/head are matched to supplier curves.","NPSH available and required are compared.","Motor power includes efficiency and service conditions.","System operating range and redundancy are documented."],
     "failures":["Sizing from static lift only","Using pump efficiency as motor efficiency","Ignoring suction losses"],
     "limits":["A pump power calculation alone does not select or guarantee a working pump."]},
    {"id":"ENG-013","domain":"engineering_water_distribution","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Plan a small water-distribution network from demand nodes, source/reservoir levels, pipe routes, material/roughness, pressure criteria, storage and fire-flow requirements.",
     "inputs":["demand pattern and node elevations","source hydraulic grade","pipe lengths and route","diameter/material/roughness options","minimum/maximum pressure criteria","storage and fire-flow basis"],
     "workflow":["Build the network graph with nodes, links, elevations and demand cases.","Validate connectivity and demand allocation.","Run an appropriate hydraulic network method for peak/average cases.","Check pressure, velocity, storage turnover and resilience.","Evaluate isolation, leakage, outage and fire-flow scenarios."],
     "checks":["Network nodes and links are connected correctly.","Mass balance closes within solver tolerance.","Pressure/velocity criteria are checked at critical nodes.","Demand assumptions and emergency cases are stated."],
     "failures":["Disconnected link","Incorrect node elevation","Demand double-counting"],
     "limits":["A conceptual network is not a water-quality or public-health approval."]},
    {"id":"ENG-014","domain":"engineering_survey_setting_out","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Prepare setting-out coordinates for a building grid using verified control points, local grid rotation, scale factor, benchmark elevation and approved design coordinates.",
     "inputs":["control point coordinates","coordinate reference and datum","grid rotation/scale factor","benchmark and reduced levels","design grid coordinates","instrument accuracy and tolerances"],
     "workflow":["Check source coordinate systems, datum and control-point quality.","Apply the documented transformation from design/local coordinates to survey coordinates.","Calculate set-out coordinates and independent check distances/bearings.","Create field point lists with units, codes and tolerances.","Specify independent checks and as-set-out recording."],
     "checks":["Transformation is reproducible and invertible within tolerance.","Bearing convention and axis order are explicit.","Benchmarks and reduced levels are traceable.","Independent check measurements are defined."],
     "failures":["Easting/Northing swap","Bearing convention mismatch","Wrong vertical datum"],
     "limits":["Calculated coordinates do not replace licensed survey control verification."]},
    {"id":"ENG-015","domain":"engineering_earthworks_and_quantities","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Prepare cut/fill quantities from surveyed existing and approved formation surfaces, chainage cross-sections, material factors, haul zones and measurement rules.",
     "inputs":["existing and design surfaces","station spacing and section areas","cut/fill classification","shrink/swell factors","haul/disposal zones","measurement rules"],
     "workflow":["Verify surface coordinate reference, units and survey dates.","Compare existing and formation levels by chainage and section.","Calculate cut/fill volumes using a justified method and report interpolation assumptions.","Apply material factors only to the correct volume basis.","Reconcile quantities by material and haul/disposal destination."],
     "checks":["Sections and chainages are ordered correctly.","Cut and fill are not netted where separate handling is required.","Shrink/swell factors and units are traceable.","Outlier sections are reviewed."],
     "failures":["Mixed survey surfaces","Wrong chainage interval","Applying factor twice"],
     "limits":["Preliminary quantity estimates are not payment measurements without contractual rules and survey verification."]},
    {"id":"ENG-016","domain":"engineering_construction_quality","application":"engineering","stage":"discipline_depth","task_type":"analysis",
     "prompt":"Create an inspection and test plan for a reinforced-concrete foundation pour from approved drawings, method statement, material submittals, hold points and project specification.",
     "inputs":["approved drawings and revision","concrete specification and mix approval","reinforcement schedule","ground/foundation inspection criteria","pour sequence and weather limits","hold/witness points"],
     "workflow":["Confirm approved drawing and method-statement revisions.","Define pre-pour checks for excavation, bearing stratum, blinding, reinforcement, cover, embedded items and formwork.","Define concrete delivery, sampling, workability, temperature and cube/cylinder testing per project specification.","Record curing, defects, nonconformance and corrective action.","Close hold points only with signed evidence."],
     "checks":["Inspection criteria have measurable acceptance limits.","Test frequency and standards are project-specified.","Nonconformance has disposition and traceability.","No hold point is bypassed."],
     "failures":["Using superseded drawing","Missing cover inspection","Untraceable concrete test sample"],
     "limits":["The ITP does not certify the structure; acceptance authority remains with the appointed competent persons."]},

    # Complete multidisciplinary projects (10)
    {"id":"PRJ-001","domain":"integrated_project_bungalow","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Take an approved brief for a three-bedroom bungalow on a surveyed plot through architecture, structural concept, foundation inputs, drainage, BIM coordination, schedules and drawing issue. Keep design calculations separate from concept geometry.",
     "inputs":["site survey and boundary","room schedule and circulation brief","architectural dimensions","geotechnical report","structural design basis and loads","water/drainage criteria","applicable jurisdiction and code editions"],
     "workflow":["Resolve missing site, room, accessibility and deliverable requirements.","Build site datum, grids, spaces, walls, openings and roof in Next BIM.","Prepare structural grid/member concept using engineer-approved design inputs.","Use geotechnical report to plan foundation assessment; do not infer soil capacity.","Coordinate plumbing, drainage, electrical routes and architectural openings.","Generate schedules, quantities, drawings and issue register; run independent model checks."],
     "checks":["Brief traceability from each requirement to model/deliverable.","Spatial schedule and opening counts reconcile.","Structural and foundation assumptions are flagged for engineering validation.","MEP and drainage coordination issues are logged.","IFC/drawing outputs reopen and retain required properties."],
     "failures":["Missing survey control","Room area mismatch","Uncoordinated beam/duct or drain route"],
     "limits":["A complete concept package is not a permit, construction issue or structural certification."]},
    {"id":"PRJ-002","domain":"integrated_project_four_storey_apartment","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Develop a four-storey apartment project from brief through repeated and unique floor plates, circulation, structure, MEP risers, room schedules, quantities and IFC handover.",
     "inputs":["site and planning envelope","unit/room schedules by floor","floor-to-floor heights","grid and structural design inputs","vertical circulation/fire strategy","MEP design criteria","exchange requirements"],
     "workflow":["Establish site, orientation, planning envelope and datum.","Model a typical floor and separate unique ground/roof conditions.","Coordinate stairs, lift, shafts, structural framing and service risers.","Assign spaces and validate room schedules by floor.","Coordinate MEP and produce clash/issue records.","Prepare quantities, sheets and IFC exchange with round-trip validation."],
     "checks":["Each floor is correctly identified and editable.","Stairs/lifts and risers connect across levels.","Structure/MEP clashes are tracked and resolved with approval.","Room and quantity schedules reconcile.","IFC spatial hierarchy and IDs survive exchange."],
     "failures":["Typical floor copied into unique level","Shaft discontinuity","Lost element identities during revisions"],
     "limits":["Building-code, fire, acoustic and structural approval require separate authoritative checks."]},
    {"id":"PRJ-003","domain":"integrated_project_ten_storey_office","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Coordinate a ten-storey office tower with two basements, podium, transfer level, typical office floors, plant level and roof. Build an auditable model plan that respects unique level conditions.",
     "inputs":["floor-by-floor programme","survey and site limits","level elevations","structural grid/transfer criteria","core and vertical transport requirements","MEP plant and riser requirements","fire/life-safety design basis"],
     "workflow":["Model the coordinate system, basements, podium and principal core.","Create typical floor instances only where layouts genuinely match.","Model transfer, plant and roof levels independently.","Track structural continuity and MEP riser transitions at non-typical floors.","Run coordination at each unique transition and document design issues.","Issue model views, schedules and exchange deliverables."],
     "checks":["Every storey and unique zone is represented.","No blind repetition across podium/transfer/plant levels.","Risers, stairs, lifts and structure remain continuous where required.","All unresolved high-risk issues are disclosed."],
     "failures":["Vertical discontinuity","Plant clashes","Incorrect level offsets"],
     "limits":["BIM coordination does not verify wind, seismic, fire, lift or structural design."]},
    {"id":"PRJ-004","domain":"integrated_project_clinic","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Coordinate a community clinic from functional room data through architectural BIM, structural zones, HVAC, electrical, plumbing, equipment envelopes, access and IFC exchange.",
     "inputs":["clinical functional brief","room data sheets","site/access conditions","equipment list and service interfaces","MEP design criteria","structural grid","approved accessibility/infection-control requirements"],
     "workflow":["Clarify room function, adjacency, privacy, access and equipment needs.","Create architectural spaces and equipment envelopes.","Coordinate structure with plant, shafts and service zones.","Plan HVAC, power, lighting, water and drainage using approved schedules.","Run room, system and clash checks; record exceptions.","Prepare schedules, views and IFC handover."],
     "checks":["All required rooms and adjacencies are accounted for.","Equipment has required access and service clearances.","MEP networks are connected and coordinated.","Missing clinical criteria are not guessed."],
     "failures":["Equipment cannot be maintained","Duct clashes with beam","Room classification missing"],
     "limits":["No health-facility regulatory or clinical-performance approval is implied."]},
    {"id":"PRJ-005","domain":"integrated_project_road_drainage","application":"integrated","stage":"integrated_projects","task_type":"analysis",
     "prompt":"Develop a preliminary urban road and stormwater corridor from terrain survey, traffic/design brief, alignment criteria, drainage catchments, utilities and outfall constraints.",
     "inputs":["topographic survey/control","road class and design speed","traffic data","geotechnical/pavement inputs","catchment/rainfall/IDF data","utility records","outfall and right-of-way constraints"],
     "workflow":["Validate survey control and terrain coverage.","Develop horizontal/vertical alignment alternatives and cross-sections.","Estimate earthworks and identify geotechnical/pavement information gaps.","Delineate drainage catchments and derive design flows from the stated method.","Coordinate channels, culverts, access, utilities and outfalls.","Prepare plans, profiles, quantity schedules and unresolved-risk register."],
     "checks":["Alignment criteria and stationing are consistent.","Cut/fill quantities use the correct surfaces.","Drainage capacity and outfall conditions are checked.","Utility conflicts and exceedance routes are recorded."],
     "failures":["Survey datum mismatch","Drainage outlet above hydraulic grade","Unverified utility conflict"],
     "limits":["Preliminary route and drainage design is not a statutory road or flood-risk approval."]},
    {"id":"PRJ-006","domain":"integrated_project_bridge_culvert","application":"integrated","stage":"integrated_projects","task_type":"analysis",
     "prompt":"Prepare a bridge/culvert concept coordination model from roadway profile, hydraulic opening requirements, geotechnical report, structural design inputs, approach geometry and maintenance access.",
     "inputs":["roadway levels and alignment","design flood/hydraulic study","channel geometry and scour data","geotechnical investigation","structural load basis","clearance and maintenance requirements"],
     "workflow":["Resolve roadway, hydraulic and geotechnical reference datums.","Set out the opening, approaches, foundations and access envelopes.","Prepare structural geometry as a concept tied to engineer-supplied member criteria.","Coordinate waterway clearance, debris, scour and maintenance constraints.","Record analysis/verification inputs and independent review requirements."],
     "checks":["Hydraulic opening and roadway levels reconcile.","Foundation geometry is tied to investigation data.","Structural load basis is explicit.","Scour and debris risks remain visible."],
     "failures":["Insufficient waterway opening","Foundation conflicts with scour zone","Incorrect vertical datum"],
     "limits":["Concept geometry does not certify hydraulic capacity, bridge load rating or scour resistance."]},
    {"id":"PRJ-007","domain":"integrated_project_water_tower","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Model a water-tower project with tank, staging, access ladder/platforms, inlet/outlet/overflow pipes, foundation interface and pump-system context using confirmed capacity and site data.",
     "inputs":["required storage volume and operating levels","tank geometry/material basis","site wind/seismic criteria","geotechnical report","pipe sizes and pump duty data","access and maintenance requirements"],
     "workflow":["Confirm storage capacity and operating water levels.","Build tank geometry and staging as separate editable components.","Coordinate access, overflow, inlet/outlet and maintenance envelopes.","Link the foundation interface to supplied structural/geotechnical design inputs.","Prepare a hydraulic/pump schedule and native model checks."],
     "checks":["Tank volume reconciles with required usable storage.","Access and pipe interfaces are represented.","Foundation and staging loads are traceable.","Maintenance and overflow access are considered."],
     "failures":["Confusing gross and usable capacity","Uncoordinated outlet","Foundation assumed without soil data"],
     "limits":["No tank pressure, wind, seismic, buckling, foundation or potable-water approval is implied."]},
    {"id":"PRJ-008","domain":"integrated_project_pump_station","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Develop a small water-pump station project with pump duty, suction/discharge pipework, valves, manifold, base, equipment access, electrical panel envelope and maintenance clearance.",
     "inputs":["design flow and duty/standby philosophy","system head and pipe route","pump and motor datasheets","electrical supply and protection requirements","site levels and flood level","maintenance lifting/access envelope"],
     "workflow":["Verify system curve and selected pump operating point from approved hydraulic data.","Place pump, motor and base as separate components using supplier interfaces.","Route suction/discharge pipework with valves, reducers and support zones.","Coordinate electrical panel, cable access, lifting and maintenance clearances.","Inspect clashes, flow direction labels and equipment schedules."],
     "checks":["Equipment interfaces match datasheets.","Maintenance removal paths are clear.","Pipe network connects to the correct suction/discharge points.","Electrical design inputs and protection are not guessed."],
     "failures":["Wrong pump orientation","Insufficient maintenance clearance","Suction pipe air pocket or unverified loss"],
     "limits":["A spatial arrangement is not a commissioned pump station or electrical safety approval."]},
    {"id":"PRJ-009","domain":"integrated_project_industrial_skid","application":"integrated","stage":"integrated_projects","task_type":"create",
     "prompt":"Coordinate an industrial pump/compressor skid with baseframe, equipment packages, pipework, valves, instrument envelopes, cable tray, lifting points and transport envelope.",
     "inputs":["equipment vendor models/datasheets","process flow and line list","structural load/support basis","instrument index","electrical area classification","lifting/transport constraints"],
     "workflow":["Establish skid coordinate system and vendor model revisions.","Place equipment from verified interface datums and maintenance envelopes.","Route process piping and instrument connections with line identities.","Coordinate structural supports, lifting and transport envelope.","Run clash, access, weight/centre-of-gravity and interface checks."],
     "checks":["Vendor nozzle/interface coordinates are preserved.","Maintenance and lifting access are clear.","Line and instrument identifiers remain traceable.","Weight and centre of gravity are calculated from approved mass data."],
     "failures":["Vendor revision mismatch","Pipe clashes with removable cover","Lifting point conflicts with centre of gravity"],
     "limits":["Layout is not a pressure-system, lifting or hazardous-area certification."]},
    {"id":"PRJ-010","domain":"integrated_project_existing_building_retrofit","application":"integrated","stage":"integrated_projects","task_type":"edit",
     "prompt":"Plan a retrofit of an existing building to add an accessible entrance, new stair/core and upgraded MEP while preserving the existing model's unaffected geometry and recording uncertainty in captured conditions.",
     "inputs":["existing model and survey confidence","proposed occupancy/use","accessibility criteria","structural investigation","MEP capacity survey","phasing and temporary works plan"],
     "workflow":["Audit model sources and classify existing-condition confidence.","Identify affected and unaffected elements by stable IDs.","Prepare options for access, core and service routing with structural review points.","Model demolition/new work by phase and preserve unaffected element identity.","Check temporary access, clashes, quantities and handover evidence."],
     "checks":["Existing-condition uncertainty is visible.","Unaffected elements preserve their identity.","Structural interventions are reviewed before execution.","Phases and temporary works are represented."],
     "failures":["Assuming incomplete scan is authoritative","Deleting hosted elements unexpectedly","Temporary access blocked"],
     "limits":["A retrofit concept is not an intrusive survey, structural approval or construction method statement."]},

    # Operator decision, command selection and recovery (12)
    {"id":"OPS-001","domain":"operator_design_intake","application":"operator","stage":"operator_method","task_type":"clarify",
     "prompt":"A user says: 'Design me a factory.' Demonstrate how to identify the minimum information needed before modelling, without overwhelming the user or inventing requirements.",
     "inputs":["only a general factory request"],
     "workflow":["Ask about product/process, site, capacity and major zones.","Clarify building scale, material handling, vehicle access and hazardous/process areas as relevant.","Ask for the available survey, functional brief and deliverables.","Summarise confirmed facts separately from assumptions and unresolved questions.","Do not create geometry until minimum layout constraints are confirmed."],
     "checks":["Questions are grouped and prioritised.","No already answered question is repeated.","Critical unknowns block premature modelling.","Optional preferences are distinguished from required inputs."],
     "failures":["Asking an excessive questionnaire","Assuming a generic factory layout","Treating a concept as permit-ready"],
     "limits":["Do not infer process safety, hazardous-area classification or production capacity."]},
    {"id":"OPS-002","domain":"operator_live_tool_discovery","application":"operator","stage":"operator_method","task_type":"inspect",
     "prompt":"A request needs an unfamiliar operation that is not in the currently supplied tool list. Show how NextAI should discover whether the pinned application supports it before planning.",
     "inputs":["user intent","current allowed tool schemas","live capability-discovery interface"],
     "workflow":["Inspect the current tool list and its schema revision.","Query the application's live capability catalogue for the closest supported operation.","Compare exact command identity, parameters, preconditions and permission status.","If callable and approved, construct a schema-valid plan; otherwise report the capability gap and alternatives.","Never guess a command name or parameter key."],
     "checks":["Capability discovery is performed before selection.","Exact native ID and schema are captured.","Unsupported/unavailable status is explicit.","No write operation bypasses permission policy."],
     "failures":["Invented command ID","Stale schema","Discovery result mistaken for execution permission"],
     "limits":["Discovery does not prove native execution or command correctness."]},
    {"id":"OPS-003","domain":"operator_native_tool_selection","application":"operator","stage":"operator_method","task_type":"plan",
     "prompt":"The user asks to add four identical holes to an existing plate. Choose a native strategy after inspecting the available tools, and explain when to use a patterned feature rather than four unrelated cuts.",
     "inputs":["plate document and stable body ID","hole diameter/depth/location specification","current tool schemas","design intent for equal spacing"],
     "workflow":["Inspect the document and identify the target body and datum.","Discover sketch, hole/pocket and pattern capabilities from the supplied native registry.","Choose one driving hole definition plus a parametric pattern when supported and appropriate.","Validate pattern axis, count, spacing and references before execution.","Inspect the result and preserve the feature history."],
     "checks":["Selected tools exist in the supplied schema.","Pattern parameters are explicit and dimensionally consistent.","Target body identity is preserved.","Result contains exactly four holes at requested positions."],
     "failures":["Using a guessed tool","Patterning around wrong axis","Cutting unrelated bodies"],
     "limits":["No actual tool call is claimed by this authored example."]},
    {"id":"OPS-004","domain":"operator_workflow_decomposition","application":"operator","stage":"operator_method","task_type":"plan",
     "prompt":"Convert the approved brief for a small pump room into a dependency-aware work plan covering architectural enclosure, equipment placement, pipe interfaces, electrical clearance, schedules and inspection.",
     "inputs":["approved brief","equipment schedule","room envelope","service access criteria","available native capabilities"],
     "workflow":["Break the request into deliverables and ordered dependencies.","Identify which objects/inputs must exist before later operations.","Separate independent workstreams from coordination gates.","Insert inspection checkpoints after each coherent stage.","Expose blockers and ask for approval before consequential modifications."],
     "checks":["No dependent operation precedes its prerequisites.","Every deliverable has an acceptance check.","Cross-discipline clashes are checked before issue.","Progress status distinguishes planned, executed and verified."],
     "failures":["Monolithic plan with no checkpoints","Unresolved input hidden inside execution","Skipping model inspection"],
     "limits":["A plan is not evidence that the application carried it out."]},
    {"id":"OPS-005","domain":"operator_state_preserving_edit","application":"operator","stage":"revision_and_recovery","task_type":"edit",
     "prompt":"Change the width of one selected BIM wall while preserving its identifier, hosted door/window openings, attached properties and all unrelated walls.",
     "inputs":["current model snapshot","target wall ID","new width","hosted element IDs","properties that must remain unchanged"],
     "workflow":["Query the exact wall and hosted elements by stable IDs.","Record before-state properties and relationships.","Use the supplied typed modify capability on the existing wall.","Inspect hosted openings, constraints, quantities and adjacent joins.","Compare before/after identity and unaffected object state."],
     "checks":["Target wall ID remains stable.","Hosted doors/windows remain associated and correctly positioned.","Unrelated elements are unchanged.","Modified geometry and schedule values reconcile."],
     "failures":["Delete/recreate instead of modify","Host relationships lost","Adjacent wall joins break"],
     "limits":["If the bridge cannot preserve identity, stop and ask for an approved alternative."]},
    {"id":"OPS-006","domain":"operator_failed_recompute_recovery","application":"operator","stage":"revision_and_recovery","task_type":"recover",
     "prompt":"A CAD feature edit causes the document recompute to fail. Explain the safe recovery sequence; do not repeatedly retry the same invalid operation.",
     "inputs":["operation result and native error","before-state snapshot/checkpoint","feature dependency tree","document transaction/undo availability"],
     "workflow":["Stop further write operations and capture the error and current state.","Inspect the failed feature and upstream references to isolate the first broken dependency.","Rollback or undo to the last known-good state using the native transaction mechanism.","Correct the root cause only after confirming the intended geometry and inputs.","Recompute, inspect, save and reopen before reporting recovery."],
     "checks":["No cascading edits occur while the model is invalid.","Last known-good state is recoverable.","Root cause and changed properties are recorded.","Final recompute and save/reopen pass."],
     "failures":["Repeated blind retries","Saving corrupted state","Undo removes unrelated user work"],
     "limits":["If rollback cannot be proven safe, preserve the file and request user intervention."]},
    {"id":"OPS-007","domain":"operator_sketch_constraint_diagnosis","application":"operator","stage":"revision_and_recovery","task_type":"recover",
     "prompt":"A parametric sketch reports conflicting constraints after a dimension change. Diagnose it without deleting constraints arbitrarily or converting the sketch to dumb geometry.",
     "inputs":["sketch geometry","constraint list and solver diagnostics","recent parameter change","required design intent"],
     "workflow":["Inspect solver status and identify conflicting/redundant constraints.","Map constraints to intended geometric relationships and driving dimensions.","Find the minimal inconsistent constraint set.","Propose the smallest reversible correction and retain design intent.","Solve again and verify degrees of freedom and key dimensions."],
     "checks":["No required design-intent constraint is silently removed.","Solver reports a valid state.","Driving dimensions remain correct.","Feature dependencies recompute."],
     "failures":["Removing all dimensions","Changing geometry to hide conflict","Redundant constraints remain"],
     "limits":["If design intent cannot be inferred, ask the user before changing constraints."]},
    {"id":"OPS-008","domain":"operator_bim_command_schema_recovery","application":"operator","stage":"revision_and_recovery","task_type":"recover",
     "prompt":"A BIM command fails because an argument has the wrong type or a required parameter is missing. Show how to correct the call using the live schema.",
     "inputs":["failed command response","live command schema","intended target element and values"],
     "workflow":["Read the returned validation error without assuming the command partially succeeded.","Re-query the exact command schema and required/optional fields.","Check enum values, units, coordinate shapes and target ID.","Inspect model state to determine whether any partial mutation occurred.","Submit one corrected call only when the before-state is understood."],
     "checks":["Corrected arguments conform to the live schema.","No duplicate object is created by retry.","Target identity and units are valid.","Post-call state is inspected."],
     "failures":["Blindly coercing values","Retrying after partial success","Using stale schema"],
     "limits":["A command error does not prove that no state changed; inspect before retrying."]},
    {"id":"OPS-009","domain":"operator_ifc_roundtrip_recovery","application":"operator","stage":"revision_and_recovery","task_type":"recover",
     "prompt":"An IFC export reopens with missing property sets and shifted coordinates. Diagnose the exchange failure and prepare a corrected export without overwriting the source model.",
     "inputs":["source native model","export settings and schema","reopened IFC report","coordinate reference data","required property-set mapping"],
     "workflow":["Preserve source model and failed IFC as evidence.","Compare source/export/reopened entity counts, property sets and coordinates.","Identify whether the loss originates in mapping, schema, units or coordinate transformation.","Correct the export configuration and export to a new revision file.","Reopen the new file independently and compare required relationships and properties."],
     "checks":["Source model remains unchanged.","Required property sets and entity classes survive.","Coordinate control points reconcile within tolerance.","New export is independently parsed and versioned."],
     "failures":["Overwriting source/export evidence","Applying a second coordinate transform","Treating a successful file write as valid IFC"],
     "limits":["Exchange validation is scoped to the agreed requirements, not every possible downstream application."]},
    {"id":"OPS-010","domain":"operator_unsupported_capability","application":"operator","stage":"operator_method","task_type":"clarify",
     "prompt":"A user asks for an operation that is absent from the current native tool registry. Demonstrate an honest response and safe next step.",
     "inputs":["user request","current complete capability census","current per-turn allowed tools"],
     "workflow":["Search the pinned capability census and current runtime discovery result.","Distinguish not installed, discovered-but-not-callable, schema-missing and permission-blocked.","Offer a supported alternative only when its trade-offs are understood.","Ask the user whether to proceed with the alternative or leave the task unmodified.","Record the capability gap for future adapter work."],
     "checks":["No fictitious tool is proposed.","No write operation occurs without authorization.","Limitations and alternatives are clearly described.","Original model state remains unchanged."],
     "failures":["Pretending unsupported operation succeeded","Substituting a destructive approximation","Confusing discovery with permission"],
     "limits":["The operator must not bypass application permissions or invent capabilities."]},
    {"id":"OPS-011","domain":"operator_precondition_and_missing_input","application":"operator","stage":"operator_method","task_type":"clarify",
     "prompt":"A user asks for a foundation layout, but there is no geotechnical report, verified load schedule or site survey. Decide what can proceed and what must wait.",
     "inputs":["foundation layout request","no site survey","no soil investigation","no verified column reactions"],
     "workflow":["State that final foundation sizing is blocked by missing ground, load and coordinate inputs.","Ask for geotechnical investigation, design actions and site control data.","Offer a non-dimensional conceptual layout or information checklist if useful.","Do not generate guessed dimensions or bearing values.","Record unresolved decisions and their consequences."],
     "checks":["No bearing pressure or footing size is fabricated.","Required inputs are named and prioritised.","Conceptual work is clearly separated from design.","The user retains control over assumptions."],
     "failures":["Guessing safe bearing capacity","Using a typical footing dimension as design","Claiming code compliance"],
     "limits":["Foundation design requires competent geotechnical and structural review."]},
    {"id":"OPS-012","domain":"operator_native_save_reopen_verification","application":"operator","stage":"revision_and_recovery","task_type":"inspect",
     "prompt":"After a multi-step native design task, verify that the result is truly saved and editable rather than reporting success from an in-memory viewport alone.",
     "inputs":["native application success responses","target file path and format","expected object IDs/properties/geometry","reopen capability"],
     "workflow":["Inspect each operation result and the final in-memory document state.","Save to the requested revision path and verify the write response.","Close and reopen the saved project using the native application.","Re-query expected objects, identities, properties, geometry and relationships.","Compare the reopened state with the expected acceptance criteria and report exceptions."],
     "checks":["Saved artifact exists and is readable.","Reopened state matches required objects and properties.","No unexpected identity loss or missing relationship occurs.","Report distinguishes native execution from round-trip validation."],
     "failures":["Checking only the viewport","Saving to wrong path","Unverified export treated as reopen success"],
     "limits":["Round-trip success does not equal independent engineering validation."]},
]




EXAMPLES_PER_SUBJECT = 10
COLLECTION_BY_APPLICATION = {
    "nextcad": "NextCAD",
    "nextbim": "Next BIM",
    "engineering": "Engineering disciplines",
    "integrated": "Complex engineering projects",
    "operator": "Native operator, tool selection and recovery",
}

VARIANT_SPLIT_ASSIGNMENT = {
    "BASELINE": "train",
    "BOUNDARY": "train",
    "CLARIFY": "train",
    "REVISION": "train",
    "RECOVERY": "train",
    "COORDINATION": "train",
    "ALTERNATIVE": "train",
    "CHANGE_IMPACT": "train",
    "DELIVERY": "validation",
    "INDEPENDENT_REVIEW": "test",
}

# Nine additional teaching situations accompany every baseline subject. They
# deliberately vary the decision, initial model state, missing information,
# failure mechanism, interface, revision scope or acceptance evidence.
VARIATION_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "nextcad": [
        {"id":"BOUNDARY","title":"Boundary and tolerance case",
         "scenario":"The key interface is now close to its minimum geometric clearance or manufacturing limit. Check feasibility and expose any dimension that cannot be met simultaneously; do not silently relax the specification.",
         "steps":["Identify the limiting interface, tolerance and datum from the approved specification.","Check geometric feasibility and tolerance stack before choosing a feature strategy.","Compare the resulting geometry against the stated limit and flag unresolved manufacturing data."],
         "checks":["The limiting condition is named and measured.","Conflicting constraints are surfaced before modelling.","No tolerance or material limit is invented."],
         "failures":["Negative or zero clearance","Overlapping feature boundaries","Tolerance stack omitted"],
         "limits":["Geometric feasibility is not proof of manufacturing capability or product safety."],"mode":"feasibility_check"},
        {"id":"CLARIFY","title":"Incomplete drawing and clarification",
         "scenario":"The drawing revision omits one critical datum or unit and gives two conflicting dimensions for the same interface. Decide what can safely be inferred and ask only the blocking questions before making a change.",
         "steps":["Compare the drawing title block, revision and dimension references.","Identify the exact conflicting or absent datum/unit/interface value.","Ask a concise clarification and keep the native write plan empty until it is resolved."],
         "checks":["The contradiction is stated precisely.","Already supplied facts are not asked again.","No guessed dimension enters a native operation."],
         "failures":["Assuming a default unit","Choosing one of two conflicting values","Editing before clarification"],
         "limits":["No geometry change is authorised while a critical design dimension remains unresolved."],"mode":"clarify_before_action"},
        {"id":"REVISION","title":"Existing-model parametric revision",
         "scenario":"The task begins from an existing FCStd document with several bodies, sketches and downstream features. Change only the approved target while preserving body identity, feature dependencies and unrelated components.",
         "steps":["Inspect the current document and record the target body's stable identity and feature tree.","Locate the driving sketch/parameter instead of replacing the body with new primitives.","Make the smallest reversible edit, recompute and compare downstream dependencies.","Save a revision copy and reopen it to verify identities and geometry."],
         "checks":["Target body and intended feature identities are preserved.","Unrelated bodies remain unchanged.","Dependent features recompute and the reopened file matches the intended revision."],
         "failures":["Topology naming/reference breakage","Collateral change to unrelated bodies","Stale TechDraw view"],
         "limits":["An in-memory viewport change is not a verified saved revision."],"mode":"state_preserving_revision"},
        {"id":"RECOVERY","title":"Native modelling failure recovery",
         "scenario":"A pad, pocket, boolean or constraint operation fails after an earlier feature was valid. Diagnose the first failed dependency and recover without stacking blind retries or corrupting the source document.",
         "steps":["Stop additional writes and capture the native error and last known-good state.","Inspect the failed feature, referenced geometry and upstream dependencies.","Rollback through the native transaction/undo mechanism when safe.","Correct the root cause, recompute and verify the complete feature chain.","Save/reopen a recovery copy and compare it with the last known-good state."],
         "checks":["The original file is recoverable.","The first broken dependency is identified.","No unverified partial operation remains in the final tree.","Save/reopen and recompute both pass."],
         "failures":["Repeated blind retries","Saving an invalid document over the source","Removing constraints without understanding intent"],
         "limits":["If rollback safety is uncertain, preserve evidence and request user intervention."],"mode":"failure_recovery"},
        {"id":"COORDINATION","title":"Assembly and downstream discipline interface",
         "scenario":"The component is part of a larger assembly and must interface with a neighbouring component, drawing and analysis model. Keep mating datums and downstream references consistent.",
         "steps":["Inspect the neighbouring component interfaces and their source revisions.","Define mating datums and verify fit/clearance before changing the part.","Update only the dependent assembly relationships and drawing/analysis references.","Run interference, dimension and reference-integrity checks."],
         "checks":["Mating coordinate systems are consistent.","The assembly remains editable and component identities persist.","Drawing and analysis references identify the correct revision."],
         "failures":["Mismatched datum orientation","Assembly interference","Downstream reference to an obsolete body"],
         "limits":["A coordinated geometry model does not establish structural or operational adequacy."],"mode":"cross_discipline_coordination"},
        {"id":"ALTERNATIVE","title":"Compare native modelling strategies",
         "scenario":"Two native modelling strategies could produce the requested shape, such as a parametric PartDesign feature sequence or a separately editable Part/assembly construction. Compare editability, dependencies and validation before selecting one.",
         "steps":["Discover the exact native tools and schemas currently available.","Compare feature-history clarity, editability, reference stability and expected checks.","Choose the least fragile strategy for the stated design intent and explain the trade-off.","Keep a fallback plan if the preferred operation is unsupported."],
         "checks":["Every selected tool exists in the supplied tool schema.","The chosen approach preserves intended editability.","Trade-offs and unsupported features are explicit."],
         "failures":["Selecting a familiar but unsuitable tool","Using generic GUI commands as an unchecked write path","Creating a dumb solid where a parametric model is required"],
         "limits":["Command discovery is not execution permission or proof of success."],"mode":"native_strategy_selection"},
        {"id":"CHANGE_IMPACT","title":"Parameter change and dependency impact",
         "scenario":"A master dimension changes after downstream sketches, patterns, assembly placements and drawing views already exist. Predict affected dependencies before editing, then verify the change did not damage unrelated features.",
         "steps":["Build a dependency map from the driving parameter to downstream features and references.","Identify affected, unaffected and potentially unstable references.","Apply the approved parameter change and recompute in dependency order.","Compare geometry, feature status and downstream drawing/assembly state."],
         "checks":["Affected dependencies are identified before the edit.","Unrelated objects remain unchanged.","All impacted references recompute or are reported as failed."],
         "failures":["Hidden downstream dependency","Broken edge/face reference","Stale drawing dimensions"],
         "limits":["Impact prediction must be confirmed by native post-state inspection."],"mode":"change_impact_analysis"},
        {"id":"DELIVERY","title":"Drawing and neutral-format delivery",
         "scenario":"Prepare a controlled drawing and neutral-format exchange from the approved native revision. Preserve units, orientation, revision metadata and component identity where the exchange format supports it.",
         "steps":["Confirm the exact source revision and requested drawing/exchange standards.","Generate linked views and functional dimensions from stable model references.","Export to the requested neutral format with explicit units and tessellation/solid options.","Reopen the exported file independently and compare solids, bounds and key dimensions.","Record omissions, lost parametric history and revision metadata."],
         "checks":["Drawing views reference the approved revision.","Exported geometry and units reconcile with the source.","Round-trip exceptions are reported rather than hidden."],
         "failures":["Stale drawing views","Unit conversion error","Export silently drops bodies or features"],
         "limits":["Neutral geometry exchange does not preserve every parametric feature or certify manufacturing readiness."],"mode":"controlled_delivery"},
        {"id":"INDEPENDENT_REVIEW","title":"Independent model quality examination",
         "scenario":"A reviewer receives the completed model without access to the modelling conversation. Audit it against the brief and determine whether geometry, feature history, constraints and saved state independently satisfy the acceptance criteria.",
         "steps":["Read the approved brief and derive independent measurable acceptance checks.","Inspect object count, solid validity, feature tree, critical dimensions and units.","Reopen the saved file and repeat the checks from the stored artifact.","List every failed, untested or unsupported criterion separately."],
         "checks":["The review uses the brief, not the model author's claims.","Geometry and feature-history checks are measurable.","The saved artifact is reopened and inspected.","Failures remain visible."],
         "failures":["Reviewing only screenshots","Treating a valid solid as fully constrained/editable","Omitting failed criteria from the report"],
         "limits":["This is a software/model-quality review, not professional product certification."],"mode":"independent_review"},
    ],
    "nextbim": [
        {"id":"BOUNDARY","title":"Level, host and spatial boundary case",
         "scenario":"The model contains an opening close to a wall end, a room boundary crossing a level transition and a component near a sloping roof. Check host, containment and spatial rules before modifying the model.",
         "steps":["Query the exact host, level, space and neighbouring element identifiers.","Check geometric tolerance, host extent and level assignment.","Determine whether the element is valid in the native model and intended IFC representation."],
         "checks":["Opening host and spatial containment are correct.","Level and storey assignment is explicit.","No element is moved merely to hide a boundary error."],
         "failures":["Opening outside host extent","Room boundary leak","Incorrect storey elevation"],
         "limits":["Model topology is not proof of statutory spatial or accessibility compliance."],"mode":"boundary_validation"},
        {"id":"CLARIFY","title":"Incomplete BIM brief",
         "scenario":"The brief omits the survey coordinate reference, level datum and required IFC exchange schema. Identify what can proceed and ask the blocking questions without inventing project defaults.",
         "steps":["Inspect current project units, origin, levels and source metadata.","Separate confirmed architectural requirements from missing survey/exchange inputs.","Ask the user to confirm coordinate reference, vertical datum and IFC deliverable requirement.","Keep coordinate-sensitive writes and export operations blocked."],
         "checks":["Each missing input is named with its consequence.","No coordinate transform is guessed.","The write plan is empty for blocked operations."],
         "failures":["Assuming project origin is survey origin","Using an unspecified IFC schema","Changing levels to fit an assumed datum"],
         "limits":["Coordinate-sensitive model changes wait for authoritative survey information."],"mode":"clarify_before_action"},
        {"id":"REVISION","title":"Identity-preserving BIM revision",
         "scenario":"The project already contains walls, doors, windows, spaces, schedules and property sets. Modify one approved wall/space configuration while preserving stable element IDs, hosts and unaffected elements.",
         "steps":["Query the target and its hosted/opening/space relationships by stable ID.","Record before-state properties, classifications and connected elements.","Use the native modify operation on the existing object.","Re-query host, spatial, schedule and property relationships after modification."],
         "checks":["The target ID remains stable where the native application promises identity preservation.","Hosted openings and spaces remain correctly related.","Unrelated elements and schedules remain unchanged."],
         "failures":["Delete/recreate masquerading as edit","Lost host relationship","Duplicate type/instance properties"],
         "limits":["If identity cannot be preserved by the available native command, stop and request approval."],"mode":"state_preserving_revision"},
        {"id":"RECOVERY","title":"BIM command and IFC failure recovery",
         "scenario":"A BIM command reports a schema error or an IFC export reopens with missing relationships. Inspect the actual project state before retrying, because a failed response may still have partially mutated the model.",
         "steps":["Capture the native response and inspect whether any object/state change occurred.","Retrieve the live command schema and validate argument names, types, enums and IDs.","For export loss, compare entity counts, GlobalIds, containment, property sets and coordinates.","Correct only the demonstrated cause and write to a new revision/export path.","Reopen and independently validate the corrected result."],
         "checks":["No duplicate mutation occurs during retries.","Live command schema is used.","Source model and failed export remain recoverable.","Independent round-trip validates required relationships."],
         "failures":["Blind retry after partial success","Stale command schema","Overwriting failed export evidence"],
         "limits":["A successful file write is not proof of valid IFC exchange."],"mode":"failure_recovery"},
        {"id":"COORDINATION","title":"Multi-discipline BIM coordination",
         "scenario":"Coordinate architecture, structure and MEP where a riser, duct and beam occupy competing space. Preserve discipline ownership and require approval for safety-critical changes.",
         "steps":["Inspect exact element IDs, levels, systems and connector relationships.","Classify true clash, clearance issue or data-quality problem.","Propose alternatives with responsible discipline and required decision.","Apply only the approved alternative and rerun coordination checks."],
         "checks":["All affected elements are identified by stable IDs.","Clash responsibility and approval are recorded.","System connections and structural member identities are preserved."],
         "failures":["Moving a structural member without approval","Breaking connector systems","Closing a clash without rerunning checks"],
         "limits":["BIM coordination does not approve structural openings, fire strategy or MEP capacity."],"mode":"cross_discipline_coordination"},
        {"id":"ALTERNATIVE","title":"Compare BIM authoring strategies",
         "scenario":"A repeated multi-storey layout could be represented by controlled instances, linked types or separately authored floors. Compare editability, level-specific variation and identity implications before selecting a method.",
         "steps":["Inspect available native copy/instance/type and relationship commands.","Compare how each method handles unique floor plates, hosted components and schedules.","Choose the strategy that preserves required independent edits and traceability.","Test it on one representative level before expanding the pattern."],
         "checks":["The strategy matches actual native command capability.","Unique floors remain independently editable.","Type and instance data stay distinct."],
         "failures":["Blindly copying a unique floor","Linked edits unintentionally changing all levels","Duplicate element identity"],
         "limits":["The most compact model representation is not always the correct information model."],"mode":"native_strategy_selection"},
        {"id":"CHANGE_IMPACT","title":"Building-wide change impact",
         "scenario":"A revised level elevation or room programme affects stairs, lift travel, risers, hosted openings, quantities and schedules. Predict dependencies and revise only affected elements.",
         "steps":["Build an impact list from the changed datum/programme to dependent objects and schedules.","Separate direct edits from derived data that should recompute.","Apply the approved change in a controlled sequence.","Re-query affected levels, connections, rooms, quantities and issue status."],
         "checks":["Every affected relationship is included in the impact list.","Unrelated elements remain unchanged.","Schedules and derived quantities reflect the revised model."],
         "failures":["Unchanged riser segment","Stair termination mismatch","Stale room schedule"],
         "limits":["Predicted impact must be checked against the actual native after-state."],"mode":"change_impact_analysis"},
        {"id":"DELIVERY","title":"IFC and information handover",
         "scenario":"Prepare an IFC deliverable and asset-information package for a named exchange requirement. Preserve spatial hierarchy, classifications, property sets, coordinates and stable identifiers wherever supported.",
         "steps":["Check the required IFC schema, Model View Definition and exchange scope.","Map native categories and types to agreed IFC entities and classifications.","Validate properties, materials, containment, units and coordinate transformation.","Export to a new version, parse/reopen it independently and compare key data.","Generate a handover exceptions list for missing or unsupported attributes."],
         "checks":["Required entities and property sets survive exchange.","Spatial containment and coordinates reconcile.","Identifiers and schedule quantities are compared.","Unsupported data mappings are disclosed."],
         "failures":["Missing property set","Incorrect GlobalId handling","Coordinate shift or unit error"],
         "limits":["A parsed IFC file may still fail a client's full information delivery specification."],"mode":"controlled_delivery"},
        {"id":"INDEPENDENT_REVIEW","title":"Independent BIM information examination",
         "scenario":"An independent reviewer audits the model against the approved room schedule, type data, element relationships and exchange requirements without relying on the authoring conversation.",
         "steps":["Select independent requirements and query native objects by class, level and type.","Check room boundaries, hosts, type/instance data, materials and system relationships.","Validate schedules against the selected model population.","Reopen an IFC exchange and compare entity counts, containment, IDs and properties.","Report missing/untested criteria and failed relationships."],
         "checks":["Checks derive from the source brief and exchange specification.","Every sampled element has traceable identity.","Schedules reconcile to native query results.","IFC round-trip evidence is retained."],
         "failures":["Counting only visible geometry","Ignoring orphaned or unclassified objects","Reporting schedule totals without query scope"],
         "limits":["Independent model review is not statutory building or engineering approval."],"mode":"independent_review"},
    ],
    "engineering": [
        {"id":"BOUNDARY","title":"Parameter validity and boundary conditions",
         "scenario":"A governing input lies close to the method's valid domain, such as a change in stress history, eccentricity, hydraulic regime, slenderness or stability condition. Check applicability before using the formula.",
         "steps":["Identify the method's assumptions and mathematical domain.","Check the governing parameter against limiting cases and sign conventions.","Use a different method or request further data if the assumptions no longer hold.","Report sensitivity and the exact boundary that controls the result."],
         "checks":["Method applicability is justified.","Units and sign conventions are consistent.","A boundary violation is not hidden by a numerical answer."],
         "failures":["Using an elastic solution outside its assumptions","Mixing gross/net quantities","Ignoring uplift or pore pressure"],
         "limits":["A bounded analytical case is not a complete engineering design."],"mode":"method_applicability"},
        {"id":"CLARIFY","title":"Missing design data and clarification",
         "scenario":"The requested calculation or design is missing one or more governing inputs: loads, support conditions, geotechnical parameters, flow criteria, material grade or governing standard. Ask for what is essential and do not invent a typical value.",
         "steps":["List known inputs with source, units and confidence.","Identify which equation/design check each missing input controls.","Ask grouped priority questions and explain what cannot yet be concluded.","Offer a limited conceptual explanation only if it does not imply a design result."],
         "checks":["No missing design value is fabricated.","Each requested input has a clear purpose.","The result is labelled under-specified until resolved."],
         "failures":["Assuming safe bearing capacity","Using a generic load","Selecting a code factor without edition/context"],
         "limits":["No sizing or safety statement is made from an incomplete brief."],"mode":"clarify_before_action"},
        {"id":"REVISION","title":"Engineering assessment revision from new evidence",
         "scenario":"A previous calculation or report must be revised after a new borehole, material test, survey, load combination or design criterion arrives. Preserve the original basis and show what changed.",
         "steps":["Record the old and new evidence sources and revision dates.","Identify the parameters and checks affected by the new evidence.","Recalculate using the same stated method where still applicable, otherwise justify the method change.","Compare old/new results and explain the practical consequence."],
         "checks":["Input provenance and revision are explicit.","Old values are not overwritten without an audit trail.","Changed and unchanged checks are distinguished."],
         "failures":["Mixing values from different reports","Using superseded loads","Changing methods without stating why"],
         "limits":["A revised calculation requires independent review before it is used for construction."],"mode":"controlled_revision"},
        {"id":"RECOVERY","title":"Calculation and unit-error diagnosis",
         "scenario":"A previous solution contains a unit conversion error, sign inconsistency or failed equilibrium check. Diagnose the source rather than adjusting the answer to resemble an expected value.",
         "steps":["Reconstruct the input table with dimensions and units.","Perform dimensional analysis on every governing equation.","Check equilibrium, continuity, boundary conditions and limiting behaviour.","Correct the smallest root cause and recompute independently.","Retain the original failed result and document the correction."],
         "checks":["Dimensional consistency is restored.","Independent equilibrium/continuity check closes within tolerance.","The correction is traceable to the root cause."],
         "failures":["Metres/mm conversion error","Wrong load sign or support condition","Circularly adjusting outputs to match a target"],
         "limits":["A numerically consistent result can still use an unsuitable model or unverified inputs."],"mode":"calculation_recovery"},
        {"id":"COORDINATION","title":"Calculation-to-model coordination",
         "scenario":"Transfer the checked engineering basis into a CAD/BIM model without treating model geometry as proof of design adequacy. Maintain links between calculation inputs, member identifiers and model revisions.",
         "steps":["Identify the engineering outputs that are permitted to drive model parameters.","Map each output to a named native object/property and record units/source.","Check model revision, member identity and coordinate conventions before applying data.","Re-query the model and compare the assigned values with the reviewed calculation."],
         "checks":["Every mapped value has a source and unit.","Model IDs correspond to the intended members.","The calculation and model revisions are traceable."],
         "failures":["Applying loads to wrong member","Mixing local/global axes","Treating a geometry update as a passed design check"],
         "limits":["Calculation-to-model transfer is data coordination, not independent engineering validation."],"mode":"engineering_model_interface"},
        {"id":"ALTERNATIVE","title":"Compare analytical methods and assumptions",
         "scenario":"More than one accepted method could be applied to the same problem. Compare method assumptions, input requirements, limitations and expected conservatism before choosing the appropriate approach.",
         "steps":["State the candidate methods and their governing assumptions.","Compare required data, boundary conditions and intended applicability.","Choose one method for the stated case and explain why alternatives are unsuitable or less appropriate.","Where feasible, calculate an independent check using a genuinely different formulation."],
         "checks":["Methods are not mixed inconsistently.","Assumptions and factors are source-traceable.","Differences between methods are interpreted, not averaged blindly."],
         "failures":["Using coefficients from different code methods","Comparing incompatible limit states","Calling a rough estimate an independent check"],
         "limits":["Method comparison does not replace the governing standard or competent review."],"mode":"method_selection"},
        {"id":"CHANGE_IMPACT","title":"Sensitivity and parameter-change impact",
         "scenario":"The design team changes one governing parameter such as load, span, water level, soil strength, stiffness, flow demand or drainage condition. Assess the effect on dependent outputs and identify any method change.",
         "steps":["Identify direct and derived variables controlled by the changed parameter.","Recompute affected outputs and check whether the original assumptions remain valid.","Perform a bounded sensitivity comparison around the approved change.","Report which checks become governing and which require new data."],
         "checks":["Parameter provenance and units remain intact.","Derived quantities are recomputed consistently.","A change in method applicability is flagged."],
         "failures":["Updating one output but not related checks","Ignoring nonlinear response or regime change","Extrapolating beyond source data"],
         "limits":["Sensitivity is conditional on the selected model and supplied parameter range."],"mode":"sensitivity_analysis"},
        {"id":"DELIVERY","title":"Calculation report and audit trail",
         "scenario":"Prepare an auditable calculation note for engineering review. It must contain the governing basis, source inputs, equations, substitutions, units, assumptions, checks, limitations and revision metadata.",
         "steps":["Set out design basis, jurisdiction/code edition and source register.","Present equations and substitutions with consistent units.","Separate calculated results from assumptions and selected design values.","Include independent checks, sensitivity, limitations and unresolved items.","Issue the calculation note with revision and reviewer fields."],
         "checks":["Every value traces to an input or calculation step.","Units are present on all reported results.","Assumptions/limitations and code edition are clear.","Review status is not fabricated."],
         "failures":["Missing units","Unsupported code clause","Claiming approval without signature/evidence"],
         "limits":["An authored calculation note is not an approved design certificate."],"mode":"auditable_reporting"},
        {"id":"INDEPENDENT_REVIEW","title":"Independent numerical and engineering review",
         "scenario":"An independent reviewer checks the solution from the original problem statement, not the author's worked answer. Recalculate key outputs and test dimensional consistency, limiting cases and missing-input discipline.",
         "steps":["Rebuild the calculation from source inputs using an independent derivation or solver.","Check dimensions, numerical precision, equilibrium and limiting cases.","Compare governing outputs and explain any discrepancy.","Check whether the method and input evidence support the stated conclusion.","Classify the result as pass, fail, insufficient information or out-of-scope."],
         "checks":["The reviewer does not copy the original answer as its reference.","Numeric tolerance and units are explicit.","Method validity and evidence quality are assessed separately."],
         "failures":["Shared formula error in both solutions","False confidence from matching rounded values","Overstating a calculation as design approval"],
         "limits":["Independent calculation review is not a substitute for statutory checking or professional sign-off."],"mode":"independent_review"},
    ],
    "integrated": [
        {"id":"BOUNDARY","title":"Project capacity and site boundary case",
         "scenario":"A major brief constraint changes near the design boundary: an altered building height, reduced site envelope, different plant capacity, revised flood level or constrained access. Identify affected disciplines before committing to a new concept.",
         "steps":["Identify the changed project requirement and its source.","Trace effects across architecture, structure, geotechnical, civil, MEP and delivery workstreams as applicable.","Mark design decisions blocked by missing discipline inputs.","Update the staged project plan and acceptance criteria."],
         "checks":["The controlling constraint is explicit.","All affected disciplines are identified.","A local change is not treated as isolated when systems depend on it."],
         "failures":["Ignoring planning/site envelope","Missing downstream plant or access impact","Proceeding without geotechnical/hydraulic evidence"],
         "limits":["The integrated concept is not a statutory, safety or construction approval."],"mode":"project_constraint_review"},
        {"id":"CLARIFY","title":"Incomplete multidisciplinary project brief",
         "scenario":"The project brief has an architectural programme but lacks important survey, ground, structural, MEP, authority or delivery information. Establish a minimum information register and stage-gate what can proceed.",
         "steps":["Classify requirements by discipline and project stage.","Identify blocking inputs and responsible information providers.","Ask prioritised questions while preserving known project facts.","Separate early concept work from decisions requiring verified specialist data."],
         "checks":["All critical discipline gaps are recorded.","No hidden design assumption is converted into a dimension.","Stage gates distinguish concept work from detailed design."],
         "failures":["Architecture proceeds on an unverified boundary","Foundation layout without ground data","MEP routes without plant/load criteria"],
         "limits":["No detailed design or compliance claim is made from an incomplete project brief."],"mode":"clarify_before_action"},
        {"id":"REVISION","title":"Integrated project revision and phasing",
         "scenario":"An approved project change modifies a room programme, equipment package, road alignment or building core after several disciplines have begun modelling. Preserve existing model identity and establish a controlled revision sequence.",
         "steps":["Record the baseline brief, model revision and existing discipline deliverables.","Identify affected spaces, structural members, service routes, quantities and drawings.","Separate demolition/retained/new work and assign revision ownership.","Apply approved changes in dependency order and re-run coordination."],
         "checks":["Baseline revision remains available.","Affected and unaffected model elements are distinguished.","Discipline impacts and approvals are traceable."],
         "failures":["Overwriting baseline","Unapproved removal of structural/service elements","Stale schedules and drawings"],
         "limits":["A coordinated revision plan is not approval of the design change."],"mode":"controlled_project_revision"},
        {"id":"RECOVERY","title":"Cross-discipline project failure recovery",
         "scenario":"The current project has a failed model recompute, a major clash, missing IFC data or inconsistent quantities after a design change. Stabilise the project and recover without masking unresolved issues.",
         "steps":["Freeze affected write operations and preserve the last known-good project revision.","Classify the failure by discipline, model element and dependency.","Assign a responsible reviewer and define a measurable recovery criterion.","Apply an approved correction, rerun dependent checks and issue a new revision."],
         "checks":["The failure is recorded with source and location.","Unrelated deliverables remain recoverable.","Recovery evidence is retained across discipline interfaces."],
         "failures":["Fixing clash by moving an unapproved structural element","Losing revision lineage","Closing an issue without retesting"],
         "limits":["Recovery does not imply that the overall project is fit for construction."],"mode":"project_recovery"},
        {"id":"COORDINATION","title":"Interface and sequence coordination",
         "scenario":"Coordinate the project across architecture, structure, geotechnical, hydraulics/civil, MEP, construction and information delivery. Establish interfaces, owners, dependencies and inspection gates.",
         "steps":["Build an interface matrix for each discipline and model deliverable.","Define which verified outputs are inputs to another discipline.","Order the work so upstream decisions exist before dependent modelling.","Insert multidisciplinary review gates at critical interfaces.","Record interface closure and outstanding decisions."],
         "checks":["Every interface has an owner and source input.","Dependencies are ordered correctly.","Cross-discipline checks have measurable closure evidence."],
         "failures":["Unowned interface","Contradictory datums","Late discovery of a major service/structure conflict"],
         "limits":["Coordination is not a substitute for each discipline's independent design checks."],"mode":"interface_management"},
        {"id":"ALTERNATIVE","title":"Compare project concepts",
         "scenario":"Compare at least two project strategies that differ in structural grid, building massing, site arrangement, infrastructure route, equipment layout or construction sequence. Evaluate them against the confirmed brief.",
         "steps":["Define alternatives with common evaluation criteria and comparable information.","Compare site, function, buildability, interfaces, maintenance, cost inputs and risks.","Identify which benefits are evidence-based and which remain assumptions.","Present a traceable recommendation and unresolved trade-offs."],
         "checks":["Alternatives satisfy the same stated brief.","Evaluation criteria and weighting are explicit.","No unsupported cost, carbon or performance benefit is asserted."],
         "failures":["Comparing unequal scopes","Invented cost or programme data","Ignoring maintenance and access"],
         "limits":["Concept option analysis is not a full feasibility study or tender estimate."],"mode":"option_appraisal"},
        {"id":"CHANGE_IMPACT","title":"Project-wide change impact analysis",
         "scenario":"A change in occupancy, site level, equipment duty, floor count or structural system is proposed. Trace its effects through all dependent models, calculations, schedules and deliverables.",
         "steps":["Identify the change source, approval status and baseline revision.","Build a dependency graph from changed requirement to affected outputs.","Flag specialist calculations requiring re-analysis and model relationships requiring edits.","Reconcile quantities, drawings, exchange data and construction sequence after the change."],
         "checks":["Every affected deliverable is identified.","No stale calculation or drawing is presented as current.","The decision and approval history is preserved."],
         "failures":["Changing geometry without updating calculations","Stale quantity schedule","Unchanged MEP riser after floor height revision"],
         "limits":["Impact mapping is a planning step; each changed discipline result requires its own validation."],"mode":"change_impact_analysis"},
        {"id":"DELIVERY","title":"Integrated project package and handover",
         "scenario":"Prepare a coordinated issue package containing native models, drawings, schedules, quantities, calculation references, IFC exchanges, issue records and revision history.",
         "steps":["Define the required deliverables and naming/revision convention.","Check model and drawing revision alignment across disciplines.","Validate schedules, quantities, model relationships and exchange files.","Collect calculation/review references and open-issue disclosures.","Create a handover manifest with file hashes and status for every item."],
         "checks":["Every deliverable has a revision and status.","Cross-discipline references point to the same approved baseline.","Missing or unapproved items are disclosed.","Exchange files reopen and reconcile."],
         "failures":["Mixed model revisions","Missing calculation basis","Undisclosed open coordination issues"],
         "limits":["A compiled package is not a permit, construction release or professional certification."],"mode":"controlled_delivery"},
        {"id":"INDEPENDENT_REVIEW","title":"Independent multidisciplinary examination",
         "scenario":"A separate reviewer audits the project against its brief and design basis. Test requirement traceability, model coordination, engineering evidence, quantities, deliverables and unresolved risks without relying on the author's narrative.",
         "steps":["Create a requirements-to-evidence matrix from the original approved brief.","Inspect representative native objects and cross-discipline relationships.","Recalculate/check critical quantities and review calculation references independently.","Reopen selected deliverables and verify revision lineage.","Issue a pass/fail/insufficient-evidence result for each requirement."],
         "checks":["Each requirement is supported by an artifact or marked unresolved.","Geometry is not used as a proxy for engineering adequacy.","Every failed and untested item remains visible."],
         "failures":["Accepting a rendered view as proof","Using obsolete calculations","Concealing unresolved project risks"],
         "limits":["The examination does not replace licensed design review or statutory approval."],"mode":"independent_review"},
    ],
    "operator": [
        {"id":"BOUNDARY","title":"Conflicting instructions and state boundary",
         "scenario":"The user's requested result conflicts with the current native document, tool permission or a dependent constraint. Identify the conflict and the safe boundary for action before choosing a command.",
         "steps":["Compare the confirmed user request, current document state and allowed tool schemas.","Identify which requirement or permission conflicts.","Ask for approval or clarification before any consequential write.","Record the untouched state and the reason for stopping."],
         "checks":["The conflict is identified precisely.","No unauthorised write occurs.","The operator does not invent a workaround that changes user intent."],
         "failures":["Treating vague approval as permission for destructive edits","Using a tool not supplied for the turn","Changing unrelated elements"],
         "limits":["The operator must stop when permissions or design intent are unresolved."],"mode":"permission_and_conflict_handling"},
        {"id":"CLARIFY","title":"Ambiguous request and minimal questions",
         "scenario":"A user gives a short ambiguous request such as 'make it stronger', 'fix the model' or 'finish the building'. Ask the smallest useful set of questions based on the current native state and likely consequence.",
         "steps":["Inspect what is already known from the conversation and native project.","Identify the ambiguity that changes the operation or engineering meaning.","Ask one concise high-value question rather than a broad questionnaire.","Do not construct a write plan until intent is sufficiently clear."],
         "checks":["Known facts are not requested again.","The question distinguishes materially different interpretations.","No hidden assumptions are introduced."],
         "failures":["Asking too many unrelated questions","Assuming structural strengthening from a vague phrase","Executing before scope is confirmed"],
         "limits":["Clarification is mandatory when ambiguity changes safety, geometry or project scope."],"mode":"clarify_before_action"},
        {"id":"REVISION","title":"Stable identity and revision control",
         "scenario":"The operator must revise an existing model rather than recreate it. Preserve stable IDs, object properties, hosting, dependencies and prior file state.",
         "steps":["Inspect and record the exact target IDs and current relationships.","Confirm the intended change and required invariants with the user.","Select a native modify operation using the current schema.","Compare before/after IDs and dependent relationships, then save a revision copy."],
         "checks":["Only approved target IDs are changed.","Unrelated IDs and relationships remain stable.","The prior revision is recoverable."],
         "failures":["Delete/recreate used as a shortcut","Operating on a similarly named wrong object","Losing the user's prior state"],
         "limits":["If the native tool does not guarantee identity behaviour, verify before proceeding."],"mode":"state_preserving_revision"},
        {"id":"RECOVERY","title":"Partial tool success and safe retry",
         "scenario":"A native tool returns an error or timeout after a write was attempted. The operator cannot assume the operation failed completely. Inspect actual state before deciding whether to retry, compensate or stop.",
         "steps":["Stop further writes and read the full tool response.","Inspect the target object and document state to determine whether the action partially succeeded.","Check transaction IDs, operation history or idempotency where supported.","Choose one safe recovery path and avoid duplicate creation.","Verify the postcondition and report uncertainty if the state cannot be established."],
         "checks":["No duplicate operation is triggered by blind retry.","Partial mutation is explicitly checked.","Recovery action is reversible or approved."],
         "failures":["Assuming timeout equals rollback","Repeating a non-idempotent create","Concealing uncertain state"],
         "limits":["If the resulting state cannot be inspected, the operator must not claim success."],"mode":"partial_success_recovery"},
        {"id":"COORDINATION","title":"Multi-tool workflow orchestration",
         "scenario":"A task requires sequential use of inspection, capability discovery, query, a typed native write and post-operation validation. Keep each result attached to the next decision.",
         "steps":["Inspect the current document and current allowed tool list.","Discover the exact native operation and schema needed.","Query target identity and preconditions before writing.","Execute one coherent operation and inspect its actual result.","Continue only when the observed state satisfies the next prerequisite."],
         "checks":["Tool calls follow dependency order.","Exact arguments derive from the live schema and confirmed user inputs.","The observed result, not the planned result, controls the next step."],
         "failures":["Using stale inspection data","Combining too many writes before validation","Assuming a planned operation succeeded"],
         "limits":["The operator cannot turn tool availability into permission to bypass approval."],"mode":"tool_chain_orchestration"},
        {"id":"ALTERNATIVE","title":"Native tool selection under uncertainty",
         "scenario":"Several native commands may achieve the requested outcome, or the preferred tool is not exposed. Discover candidates and compare reversibility, schema fit, object identity and validation support.",
         "steps":["Search the current capability registry and allowed per-turn tools.","Compare native candidates by exact schema, preconditions, effects and undo behaviour.","Choose the smallest reversible operation that satisfies the confirmed request.","Report a capability gap if no safe option is available."],
         "checks":["Selected tool exists and is permitted.","Command parameters conform to its current schema.","Unsupported capability is not fabricated."],
         "failures":["Guessing undocumented command names","Choosing a destructive approximation","Confusing discovery with callable permission"],
         "limits":["The operator must not invoke arbitrary scripts or unreviewed GUI commands as a write shortcut."],"mode":"tool_selection"},
        {"id":"CHANGE_IMPACT","title":"Action dependency and change impact",
         "scenario":"The requested change affects a chain of model objects, schedules, drawings or downstream engineering data. Predict dependencies, sequence the edits and identify which validations must be rerun.",
         "steps":["Inspect relationships and dependencies of the target object.","Map direct and indirect affected objects and deliverables.","Sequence writes to preserve preconditions and stable references.","After each stage, inspect observed state and re-evaluate downstream impact."],
         "checks":["Dependency graph includes downstream outputs.","No stale result is reported as current.","Every invalidated check is rerun or marked outstanding."],
         "failures":["Editing a parent without checking children","Using stale schedules","Skipping a dependent validation"],
         "limits":["Impact prediction is provisional until native post-state checks pass."],"mode":"dependency_analysis"},
        {"id":"DELIVERY","title":"Execution report and evidence bundle",
         "scenario":"The task is complete only when the operator can report what was requested, what native actions actually ran, what was verified, what remains unresolved and where the saved artifact is located.",
         "steps":["Collect tool responses and native operation identifiers.","Inspect final model state and required properties.","Save/close/reopen where supported and compare postconditions.","Record failed, skipped and untested checks separately.","Produce a user-facing report that distinguishes plan, execution and verification."],
         "checks":["Every success statement maps to native evidence.","Saved artifact and revision are identifiable.","Unresolved items and failures are disclosed."],
         "failures":["Reporting the plan as completed work","Omitting a failed check","Claiming save/reopen without an actual reopen"],
         "limits":["Do not claim evidence that the application did not provide."],"mode":"evidence_based_reporting"},
        {"id":"INDEPENDENT_REVIEW","title":"Independent practical examination",
         "scenario":"The operator is given a new task without a demonstration and is scored on clarification, discovery, planning, schema-valid tool selection, execution, recovery, state verification and honest reporting.",
         "steps":["Understand the brief and ask for missing critical inputs.","Discover and select the correct native tools from current schemas.","Execute in small validated stages and preserve object identity.","Recover safely from one injected failure or unexpected state.","Verify save/reopen and report all criteria with evidence."],
         "checks":["Clarification and tool choice are correct.","Plans conform to native schemas.","The real after-state satisfies acceptance criteria.","The result is saved/reopened where required.","Failures and limits are reported honestly."],
         "failures":["Memorised command selection without state inspection","Ignoring the injected error","Claiming success from a generated plan"],
         "limits":["This authored rubric is not a practical pass until the native application is actually exercised."],"mode":"heldout_practical_behavior"},
    ],
}


def _master_target(spec: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    if variant["mode"] == "clarify_before_action":
        # A clarification example must not leak an executable baseline plan.
        workflow = [
            {"sequence": index + 1, "objective": item}
            for index, item in enumerate(variant["steps"])
        ]
    else:
        workflow = [
            {"sequence": index + 1, "objective": item}
            for index, item in enumerate(spec["workflow"])
        ]
        offset = len(workflow)
        workflow.extend(
            {"sequence": offset + index + 1, "objective": item}
            for index, item in enumerate(variant["steps"])
        )
    return {
        "schema": "nextai.master_curriculum_response.v2",
        "curriculum_version": VERSION,
        "scenario_id": spec["id"],
        "variant_id": variant["id"],
        "variant_type": variant["id"].lower(),
        "collection": COLLECTION_BY_APPLICATION[spec["application"]],
        "application": spec["application"],
        "data_split": VARIANT_SPLIT_ASSIGNMENT[variant["id"]],
        "task_type": spec["task_type"],
        "response_mode": variant["mode"],
        "confirmed_inputs": spec["inputs"],
        "scenario_change_or_challenge": variant["scenario"],
        "workflow": workflow,
        "acceptance_checks": list(spec["checks"]) + list(variant["checks"]),
        "failure_modes_to_watch": list(spec["failures"]) + list(variant["failures"]),
        "limitations_and_non_claims": list(spec["limits"]) + list(variant["limits"]),
        "evidence_level": "L0_authored_learning_example",
        "execution_status": "not_executed_by_this_example",
        "execution_blocked_until_clarification": variant["mode"] == "clarify_before_action",
        "native_write_plan": [] if variant["mode"] == "clarify_before_action" else "requires live schemas and current state",
        "plan_policy": (
            "Ask for the blocking information and return an empty native write plan until confirmed."
            if variant["mode"] == "clarify_before_action"
            else "Use exact currently supplied native schemas; inspect actual state after each coherent write."
        ),
        "tool_selection_rule": (
            "Discover unfamiliar operations in the pinned native application. Never guess command IDs, "
            "arguments or permission state. This authored example does not prove native execution."
        ),
        "training_note": "This is one distinct supervised scenario; it is not native execution evidence.",
    }


def make_master_project_curriculum() -> list[dict[str, Any]]:
    """Return ten meaningful scenarios for every one of the 62 curriculum subjects."""
    records: list[dict[str, Any]] = []
    for spec in SPECS:
        application = spec["application"]
        library_key = application
        profiles = VARIATION_LIBRARY[library_key]
        if len(profiles) != EXAMPLES_PER_SUBJECT - 1:
            raise ValueError(f"{library_key} must define exactly nine variants per subject")
        base_variant = {
            "id": "BASELINE", "mode": "standard_workflow",
            "scenario": "Baseline learning task using the confirmed inputs in the original brief.",
            "steps": [],
            "checks": ["Base scenario acceptance criteria are checked."],
            "failures": ["Unstated assumptions are introduced."],
            "limits": ["This authored scenario is not execution or approval evidence."],
        }
        variants = [base_variant] + profiles
        if len({item["id"] for item in variants}) != EXAMPLES_PER_SUBJECT:
            raise ValueError(f"Duplicate/missing variants for subject {spec['id']}")
        for variant in variants:
            item_id = spec["id"] if variant["id"] == "BASELINE" else f"{spec['id']}-V{variant['id']}"
            prompt = spec["prompt"]
            if variant["id"] != "BASELINE":
                prompt += (
                    "\n\nAdditional scenario — " + variant["title"] + ":\n"
                    + variant["scenario"]
                    + "\nRespond to this changed situation using the same learning objective. "
                      "Do not merely repeat the baseline answer."
                )
            target = _master_target(spec, variant)
            records.append({
                "record_id": item_id,
                "domain": spec["domain"],
                "system": SYSTEM,
                "prompt": prompt,
                "completion": json.dumps(target, ensure_ascii=False),
                "images": [],
                "source": "Next3D master curriculum v2",
                "license": "project-authored",
                "split_group": "master-curriculum-" + item_id.lower(),
                "stage": spec["stage"],
                "curriculum_version": VERSION,
                "curriculum_item_id": item_id,
                "curriculum_subject_id": spec["id"],
                "curriculum_collection": COLLECTION_BY_APPLICATION[application],
                "curriculum_variant_id": variant["id"],
                "application": application,
                "curriculum_split": VARIANT_SPLIT_ASSIGNMENT[variant["id"]],
                "evidence_level": "L0_authored_learning_example",
            })
    expected_total = len(SPECS) * EXAMPLES_PER_SUBJECT
    if len(records) != expected_total:
        raise ValueError(f"Expected {expected_total} master curriculum examples; generated {len(records)}")
    identities = [row["record_id"] for row in records]
    if len(identities) != len(set(identities)):
        raise ValueError("Master curriculum generated duplicate record IDs")
    normalized_prompts = [" ".join(row["prompt"].lower().split()) for row in records]
    if len(normalized_prompts) != len(set(normalized_prompts)):
        raise ValueError("Master curriculum generated duplicate normalized prompts")
    return records


def summarize_master_curriculum_splits(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Count all v2 examples after split assignment; reject missing or mislabelled lessons."""
    summary: dict[str, Any] = {
        "version": VERSION,
        "subjects": len(SPECS),
        "examples_per_subject": EXAMPLES_PER_SUBJECT,
        "total": 0,
        "by_split": {},
        "by_collection": {},
        "by_application": {},
        "by_domain": {},
        "by_variant": {},
        "by_split_and_variant": {},
        "by_split_and_collection": {},
        "evidence_level": "L0_authored_learning_example",
        "native_execution_claimed": False,
    }
    seen_ids: set[str] = set()
    for split in ("train", "validation", "test"):
        rows = [
            row for row in splits.get(split, [])
            if row.get("curriculum_version") == VERSION
        ]
        summary["by_split"][split] = len(rows)
        summary["by_split_and_collection"][split] = {}
        summary["by_split_and_variant"][split] = {}
        summary["total"] += len(rows)
        for row in rows:
            rid = str(row.get("record_id", ""))
            if not rid or rid in seen_ids:
                raise ValueError(f"Missing or duplicate master curriculum record ID: {rid!r}")
            seen_ids.add(rid)
            collection = str(row.get("curriculum_collection", "unknown"))
            application = str(row.get("application", "unknown"))
            domain = str(row.get("domain", "unknown"))
            variant_id = str(row.get("curriculum_variant_id", "unknown"))
            assigned_split = str(row.get("curriculum_split", ""))
            if assigned_split != split:
                raise ValueError(f"Master curriculum record {rid} assigned to {split}, expected {assigned_split}")
            for key, value in (("by_collection", collection), ("by_application", application),
                               ("by_domain", domain), ("by_variant", variant_id)):
                summary[key][value] = summary[key].get(value, 0) + 1
            split_collection = summary["by_split_and_collection"][split]
            split_collection[collection] = split_collection.get(collection, 0) + 1
            split_variant = summary["by_split_and_variant"][split]
            split_variant[variant_id] = split_variant.get(variant_id, 0) + 1
            try:
                target = json.loads(row.get("completion", "{}"))
            except (TypeError, json.JSONDecodeError):
                target = {}
            if target.get("evidence_level") != "L0_authored_learning_example":
                raise ValueError(f"Master curriculum record {rid} has an invalid evidence level")
            if target.get("execution_status") != "not_executed_by_this_example":
                raise ValueError(f"Master curriculum record {rid} claims native execution")
            if target.get("scenario_id") != row.get("curriculum_subject_id"):
                raise ValueError(f"Master curriculum record {rid} lost its subject lineage")
            if target.get("variant_id") != variant_id:
                raise ValueError(f"Master curriculum record {rid} lost its variant identity")
    expected_total = len(SPECS) * EXAMPLES_PER_SUBJECT
    if summary["total"] != expected_total:
        raise ValueError(f"Expected {expected_total} master curriculum records, found {summary['total']}")
    expected_splits = {"train": 496, "validation": 62, "test": 62}
    if summary["by_split"] != expected_splits:
        raise ValueError(f"Master curriculum split counts mismatch: {summary['by_split']}")
    expected_collections = {
        "NextCAD": 120, "Next BIM": 120, "Engineering disciplines": 160,
        "Complex engineering projects": 100,
        "Native operator, tool selection and recovery": 120,
    }
    if summary["by_collection"] != expected_collections:
        raise ValueError(f"Master curriculum collection counts mismatch: {summary['by_collection']}")
    expected_variants = {"BASELINE": 62}
    for profile in VARIATION_LIBRARY["nextcad"]:
        expected_variants[profile["id"]] = 62
    if summary["by_variant"] != expected_variants:
        raise ValueError(f"Master curriculum variant coverage mismatch: {summary['by_variant']}")
    if summary["by_split_and_variant"]["train"] != {
        "BASELINE": 62, "BOUNDARY": 62, "CLARIFY": 62, "REVISION": 62,
        "RECOVERY": 62, "COORDINATION": 62, "ALTERNATIVE": 62, "CHANGE_IMPACT": 62,
    }:
        raise ValueError("Training split must include the baseline and six/seven core scenario variants for every subject")
    if summary["by_split_and_variant"]["validation"] != {"DELIVERY": 62}:
        raise ValueError("Validation split must contain one delivery example per subject")
    if summary["by_split_and_variant"]["test"] != {"INDEPENDENT_REVIEW": 62}:
        raise ValueError("Held-out test split must contain one independent-review example per subject")
    return summary


def separate_master_curriculum_splits(
    splits: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    """Separate required first-party examples from the cap-limited mixed curriculum."""
    master: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    remainder: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for split in ("train", "validation", "test"):
        for row in splits.get(split, []):
            destination = master if row.get("curriculum_version") == VERSION else remainder
            destination[split].append(row)
    if sum(len(rows) for rows in master.values()) != len(SPECS) * EXAMPLES_PER_SUBJECT:
        raise ValueError("Master curriculum would be lost or duplicated while separating sampler pools")
    return master, remainder
