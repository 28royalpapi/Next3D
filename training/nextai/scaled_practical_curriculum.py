#!/usr/bin/env python3
"""Generate a scenario-diverse, split-safe 100k NextAI practical curriculum.

The existing 620 authored v2 examples are retained. This module adds enough
new L0 scenario blueprints to bring each of the five practical collections to
20,000 records. It does not generate native execution evidence or engineering
approvals. The 250k closed-form calculation corpus remains separate.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nextai_master_curriculum import (  # noqa: E402
    COLLECTION_BY_APPLICATION,
    SPECS,
    make_master_project_curriculum,
)

VERSION = "nextai-scaled-practical-curriculum-v1"
SEED = 20261128
TARGET_PER_COLLECTION = 20_000
TARGET_SPLITS = {"train": 0.80, "validation": 0.10, "test": 0.10}
COLLECTIONS = tuple(COLLECTION_BY_APPLICATION.values())

# Each profile axis changes a task decision, model state or acceptance condition.
# Their Cartesian product is deliberately much larger than the required sample.
PROFILES: dict[str, dict[str, list[Any]]] = {
    "NextCAD": {
        "contexts": [
            "a replaceable pump casing in a small water-treatment plant",
            "a serviceable gearbox housing for agricultural machinery",
            "a lightweight mounting bracket in a vehicle assembly",
            "a modular enclosure for industrial electrical equipment",
            "a precision fixture used on a manufacturing line",
            "a hand-held product enclosure with repeated fasteners",
            "a marine equipment support exposed to a corrosive environment",
            "a building-services component routed through a congested plant room",
        ],
        "objectives": [
            "preserve parametric editability while simplifying the feature history",
            "reduce mass without changing the approved interface geometry",
            "improve manufacturability while retaining the stated design intent",
            "make assembly and maintenance access easier",
            "control tolerance-sensitive interfaces and mating datums",
            "avoid fragile references after foreseeable dimension changes",
            "prepare a clean neutral-format exchange without hiding lost feature history",
            "make the model easier to inspect, revise and document",
        ],
        "operations": [
            {"id":"CREATE","title":"create a new parametric model","steps":["Establish the approved datum, units and driving dimensions before creating geometry.","Build the feature sequence in a stable, editable order.","Recompute and inspect the resulting solid and feature dependencies."],"checks":["Driving parameters remain editable","Feature history is ordered and understandable"]},
            {"id":"REVISE","title":"revise an existing model in place","steps":["Identify the target object and driving parameters by stable identity.","Change only the approved parameters and recompute dependent features.","Compare affected and unaffected geometry with the source revision."],"checks":["Target object identity is preserved","Unrelated components and references remain unchanged"]},
            {"id":"REPAIR","title":"diagnose and repair an imported or damaged model","steps":["Preserve an untouched source copy and inspect units, bounds and topology.","Classify each defect before selecting a reversible repair.","Recheck topology, dimensions and volume before accepting the repaired result."],"checks":["Source artifact remains recoverable","Repair does not silently alter design-critical geometry"]},
            {"id":"ASSEMBLE","title":"coordinate a multi-component assembly","steps":["Inspect component coordinate systems and mating interfaces.","Choose constraints that represent the intended degrees of freedom.","Check fit, interference, motion and reference stability."],"checks":["Component identities remain distinct","Mating datums and clearances reconcile"]},
            {"id":"ANALYSE_PREP","title":"prepare geometry for analysis","steps":["Check geometric validity, units, material data and the intended load path.","Identify missing boundary, contact and material inputs before analysis setup.","Document mesh and solver checks without claiming a completed solution."],"checks":["No missing critical analysis input is silently invented","Pre-processing is distinguished from solved results"]},
            {"id":"DOCUMENT","title":"prepare controlled engineering documentation","steps":["Confirm the approved model revision and drawing purpose.","Create views and dimensions from stable model references.","Check drawing-to-model consistency, units and revision metadata."],"checks":["Drawing references the approved revision","Dimensions are traceable and non-contradictory"]},
            {"id":"COMPARE","title":"compare alternative modelling strategies","steps":["Discover the exact native operations available in the running application.","Compare editability, dependency stability and validation burden of alternatives.","Select a reversible strategy and record unsupported operations."],"checks":["No unavailable native command is assumed","The selected strategy meets the stated design intent"]},
            {"id":"EXPORT","title":"prepare and verify a neutral-format exchange","steps":["Confirm format, units, coordinate system and required object scope.","Export from the approved native revision with explicit options.","Reopen independently and compare solid count, bounds and critical dimensions."],"checks":["Exported units and geometry reconcile","Round-trip losses are disclosed"]},
        ],
        "states": [
            {"id":"EMPTY","text":"the document is new and contains no modeled feature history","steps":["Confirm the intended origin and coordinate reference before creating the first object."]},
            {"id":"LEGACY","text":"the document contains an older design revision with downstream references","steps":["Record the source revision and map dependent sketches, assemblies and drawings before editing."]},
            {"id":"IMPORTED","text":"the starting geometry was imported and has no trusted parametric history","steps":["Separate verified geometry from inferred design intent and preserve the import unchanged."]},
            {"id":"PARTIAL","text":"some features exist, but the design is incomplete","steps":["Inspect feature status and identify the last known-good state before continuing."]},
            {"id":"FAILED","text":"the last recompute or feature operation failed","steps":["Capture the failing feature and error state before any rollback or repair."]},
            {"id":"MULTIBODY","text":"the document contains several related bodies and assembly references","steps":["Map object ownership and dependencies so the requested edit does not replace unrelated bodies."]},
        ],
        "constraints": [
            {"id":"TOLERANCE","text":"a critical interface has a tight tolerance and a defined datum scheme","step":"Check the tolerance chain and datum references before selecting dimensions or mating constraints.","checks":["Tolerance assumptions are explicit","Critical interfaces are measured from the correct datum"]},
            {"id":"CLEARANCE","text":"the part must fit inside a restricted clearance envelope","step":"Check the complete swept or assembled envelope against the supplied clearance boundary.","checks":["No unreviewed interference remains","Clearance is measured in the approved coordinate frame"]},
            {"id":"FABRICATION","text":"the geometry must respect a specified fabrication process and tool access","step":"Check tool reach, minimum feature size, bend or machining constraints against supplied process data.","checks":["Process-specific limits are sourced rather than guessed","Manufacturing assumptions are recorded"]},
            {"id":"TOPOLOGY","text":"an operation may fail because of thin faces, short edges or unstable topology","step":"Inspect the local topology and use stable datums or references rather than assuming generated edge indices.","checks":["Topological failures are localized","The repair remains stable after recompute"]},
            {"id":"MASS","text":"the design has a mass target but its material and density inputs must be confirmed","step":"Separate geometric volume from mass and request material density when it is absent.","checks":["Mass is not reported without a stated material density","Geometry changes are linked to the mass objective"]},
            {"id":"SERVICE","text":"fasteners and service components must remain accessible after assembly","step":"Check installation sequence, tool access and removal paths around service interfaces.","checks":["Service access is demonstrated geometrically","No component is moved without preserving its interface intent"]},
            {"id":"CHANGE","text":"a late dimension change may invalidate downstream references","step":"Map the dependency chain and identify references likely to be affected before changing the master parameter.","checks":["Affected references are known before editing","Unrelated references are checked after recompute"]},
            {"id":"EXCHANGE","text":"the receiving system may not preserve native parametric feature history","step":"Identify required exchange entities and record which native features or metadata will not survive translation.","checks":["Required exchange scope is explicit","Loss of parametric history is disclosed"]},
        ],
        "input_quality": [
            {"id":"CONFIRMED","text":"all critical dimensions, units, datums and acceptance criteria are confirmed","blocked":False,"step":"Proceed only with the confirmed inputs and retain their source references.","check":"Every driving value is traceable to the supplied brief or model."},
            {"id":"MISSING","text":"one or more critical dimensions, material properties or datum definitions are missing","blocked":True,"step":"Ask for the exact missing value or approved source; keep the native write plan empty until it is supplied.","check":"No geometry or manufacturing assumption is invented to fill a critical gap."},
            {"id":"CONFLICT","text":"two supplied dimensions or design requirements conflict","blocked":True,"step":"Show the conflict and ask which requirement controls; do not choose a convenient value.","check":"Conflicting requirements are resolved explicitly before mutation."},
            {"id":"UNVERIFIED","text":"the source drawing or imported model has uncertain units, scale or revision","blocked":True,"step":"Inspect and verify source units, scale and revision before modifying the document.","check":"Unverified source data is not treated as an approved design input."},
        ],
        "deliverables": [
            {"id":"NATIVE","text":"an editable native model and an inspection report","step":"Report the native objects, parameter dependencies and checks still requiring live application confirmation.","check":"The model remains editable and the inspection report lists any unverified criterion."},
            {"id":"DRAWING","text":"a controlled drawing package linked to the approved model","step":"Record drawing revision, view references, units and dimensions derived from the approved model.","check":"Drawing and model revisions agree."},
            {"id":"ASSEMBLY","text":"an assembly with preserved component identity and mating relationships","step":"Summarize the component tree, coordinate frames, constraints and interference checks.","check":"Assembly relationships and component identity are preserved."},
            {"id":"ANALYSIS","text":"an analysis-ready model definition with explicit assumptions","step":"Separate model preparation, solver execution and engineering review as distinct evidence stages.","check":"No solver result or design approval is claimed without its own evidence."},
            {"id":"EXCHANGE","text":"a neutral-format file plus round-trip comparison","step":"List format options, coordinate system, units and any translated or omitted properties.","check":"The exported file is reopened and compared to the native source."},
            {"id":"REVIEW","text":"an independent model-quality review record","step":"Derive measurable checks from the brief and report pass, fail and untested items separately.","check":"Review is based on the artifact, not the author's assertion."},
        ],
    },
    "Next BIM": {
        "contexts": [
            "a low-rise residential building with several repeated unit types",
            "a multi-storey office with shared core and tenant spaces",
            "a healthcare facility with critical room and service relationships",
            "an industrial workshop with plant rooms and heavy equipment zones",
            "a school campus with multiple buildings and external circulation",
            "a water-treatment facility with process buildings and pipe networks",
            "a transport terminal with large public spaces and complex circulation",
            "an existing occupied building undergoing phased renovation",
        ],
        "objectives": [
            "preserve spatial hierarchy, level assignment and shared coordinates",
            "make hosted elements and openings consistent with their host objects",
            "maintain reliable type, instance and property-set information",
            "coordinate architectural, structural and MEP model interfaces",
            "produce quantities that can be traced to native properties and geometry",
            "preserve IFC relationships and stable element identity during exchange",
            "support phased construction and existing/new element distinction",
            "prepare an auditable handover model with explicit information gaps",
        ],
        "operations": [
            {"id":"AUTHOR","title":"author a new information model","steps":["Establish project, site, building, storey, grid and coordinate hierarchy.","Create required spatial and physical objects with explicit types and relationships.","Inspect placement, containment, connectivity and required properties."],"checks":["Spatial hierarchy is valid","Elements have stable identities and intended containment"]},
            {"id":"REVISE","title":"revise existing BIM objects and properties","steps":["Identify target elements by stable identifiers and current revision.","Change only approved properties, placements or relationships.","Recheck hosts, containment, schedules and downstream references."],"checks":["Element identity is preserved","Unrelated property values and relationships remain unchanged"]},
            {"id":"HOST_REPAIR","title":"repair host, opening or containment relationships","steps":["Inspect host extent, opening geometry, level and spatial containment.","Correct only relationships supported by the model and confirmed brief.","Recheck void/fill, placement and spatial boundaries."],"checks":["Opening and filling relationships are valid","No element is reassigned merely to hide a geometric error"]},
            {"id":"COORDINATE","title":"coordinate a cross-discipline model issue","steps":["Identify the affected elements, disciplines, revisions and coordinate frames.","Classify the clash or interface issue and record measurable evidence.","Agree an approved resolution, revise the relevant model and rerun checks."],"checks":["Issue ownership and resolution evidence are recorded","No structural or service element is moved without approval"]},
            {"id":"QUANTIFY","title":"prepare a model-based quantity schedule","steps":["Define measurement rules, units and included IFC classes.","Read quantities from validated native properties or geometry.","Report missing classifications, duplicates and exceptions separately."],"checks":["Each quantity has a source property or measurement rule","Type and instance totals are not double-counted"]},
            {"id":"IFC","title":"prepare and validate an IFC exchange","steps":["Confirm IFC schema, model view, coordinate system and exchange requirements.","Map native types, properties, spatial relationships and classifications.","Export, reopen independently and compare entity and relationship inventories."],"checks":["IFC entities and relationships reconcile with scope","Unsupported or lost data is disclosed"]},
            {"id":"RENOVATE","title":"model a phased renovation","steps":["Separate existing, demolished, temporary and proposed elements.","Preserve existing survey/model provenance and assign approved phases.","Check containment, connections and phase filters after revision."],"checks":["Existing and new elements remain distinguishable","Phase and demolition status are consistent"]},
            {"id":"AUDIT","title":"audit BIM quality without changing the model","steps":["Inspect entity identities, spatial hierarchy, types, properties and relationships.","Compare model content to explicit information requirements.","Produce a non-destructive issue register with evidence and severity."],"checks":["Audit is read-only until an approved correction is authorized","Missing and inconsistent information is reported"]},
        ],
        "states": [
            {"id":"NEW","text":"the BIM project is empty apart from project units and location settings","steps":["Verify units, project origin, north rotation and coordinate reference before authoring."]},
            {"id":"PARTIAL","text":"the architectural model exists but structural and services models are incomplete","steps":["Identify discipline model revisions and establish the missing interfaces before coordination."]},
            {"id":"LEGACY","text":"the project contains older IFC imports with incomplete property mapping","steps":["Preserve source GlobalIds where required and record properties that cannot be mapped reliably."]},
            {"id":"CLASHED","text":"the model contains unresolved geometric and clearance clashes","steps":["Classify hard clashes, soft clearances and duplicate intersections before proposing changes."]},
            {"id":"PHASED","text":"the project combines existing, demolished, temporary and proposed elements","steps":["Inspect phase assignments and verify that each element belongs to the intended project stage."]},
            {"id":"HANDOVER","text":"the model is near handover but has incomplete asset and classification data","steps":["Run an information-completeness audit and retain unresolved asset fields as exceptions."]},
        ],
        "constraints": [
            {"id":"COORDS","text":"discipline models use different coordinate origins or rotations","step":"Confirm the transformation between model coordinate systems and verify known control points.","checks":["Shared coordinates are traceable to survey control","No silent project-wide translation is applied"]},
            {"id":"HOST","text":"doors, windows or openings may be detached from their intended host","step":"Check host identifiers, host extents and void/fill relationships before changing placement.","checks":["Hosted elements reference the correct host","Opening and filling relationships are consistent"]},
            {"id":"LEVEL","text":"elements may be assigned to the wrong storey or elevation","step":"Compare element placements and storey assignments against the approved level datum.","checks":["Storey assignment and elevation agree","No element is shifted to conceal a level error"]},
            {"id":"PROPERTY","text":"property sets contain missing, duplicate or inconsistent values","step":"Validate required property names, types, units and source values before mapping or writing.","checks":["Required properties are typed and unit-consistent","Unknown values remain explicitly unknown"]},
            {"id":"CLASH","text":"a model interface has a potential hard clash or insufficient clearance","step":"Capture element IDs, clash location, tolerance and discipline ownership before proposing a resolution.","checks":["Clash classification and tolerance are stated","Resolution has an approved owner"]},
            {"id":"CONNECT","text":"MEP segments or equipment ports may not form a continuous system","step":"Inspect connector compatibility, network continuity and served-space assignment.","checks":["System connectivity is valid","Open ends and unserved terminals are listed"]},
            {"id":"PHASE","text":"existing and proposed construction states may be mixed","step":"Check phase filters, demolition status and element creation/removal sequence.","checks":["Phase assignment matches the approved programme","Existing assets are not accidentally deleted"]},
            {"id":"IFC_SCHEMA","text":"the receiving workflow requires a specific IFC schema and exchange view","step":"Check entity mapping and required relationships against the declared exchange specification.","checks":["Schema-specific mapping is recorded","Unsupported entities or properties are disclosed"]},
        ],
        "input_quality": [
            {"id":"CONFIRMED","text":"project coordinates, levels, exchange requirements and information needs are confirmed","blocked":False,"step":"Proceed using the approved coordinate, information and model-scope references.","check":"All model changes are linked to approved project inputs."},
            {"id":"MISSING","text":"the coordinate reference, host intent or required property definition is missing","blocked":True,"step":"Request the missing project datum or information requirement and keep the native write plan empty.","check":"No coordinate, host or property value is fabricated."},
            {"id":"CONFLICT","text":"the architectural, structural or services requirements disagree","blocked":True,"step":"Record the conflicting revisions and ask the responsible discipline to resolve them before changing the model.","check":"No discipline requirement is silently overridden."},
            {"id":"UNVERIFIED","text":"the imported IFC or survey source has not been checked for units and revision","blocked":True,"step":"Preserve the source and verify schema, units, coordinate system and provenance before editing.","check":"Unverified IFC relationships are not treated as authoritative."},
        ],
        "deliverables": [
            {"id":"MODEL","text":"a native coordinated BIM model and issue register","step":"Report model hierarchy, affected elements, coordination checks and unresolved issues.","check":"Model objects and issue evidence identify the same revision."},
            {"id":"IFC","text":"an IFC exchange package with schema and relationship validation","step":"Record schema, model view, entity counts and relationship exceptions.","check":"Export is independently reopened and audited."},
            {"id":"SCHEDULE","text":"a quantity and asset-information schedule","step":"Include element IDs, types, storeys, units, source properties and exception rows.","check":"Schedule totals reconcile to the selected native model objects."},
            {"id":"PHASING","text":"a phased model for existing, demolition and proposed work","step":"Summarize phase assignments, demolition status and temporary works assumptions.","check":"Phase filters reproduce the intended project states."},
            {"id":"COORDINATION","text":"a clash/coordination report with owners and evidence","step":"List element IDs, clash class, location, responsible discipline and resolution status.","check":"Every resolved issue has a model revision and rerun-check reference."},
            {"id":"HANDOVER","text":"an auditable asset and information handover package","step":"List required asset data, document references, open issues and validation status.","check":"Missing asset data is disclosed and not inferred."},
        ],
    },
    "Engineering disciplines": {
        "contexts": [
            "a reinforced-concrete residential frame with beams, slabs and columns",
            "a shallow foundation system on a layered compressible soil profile",
            "a road corridor with cut/fill transitions and surface drainage",
            "an urban stormwater network with channels, inlets and outfalls",
            "a water distribution system with storage, pumping and pipe branches",
            "a retaining structure next to an existing building and road",
            "a bridge approach and culvert system crossing a seasonal watercourse",
            "a construction site with survey control, earthworks and quality records",
        ],
        "objectives": [
            "identify the governing engineering model and its assumptions",
            "check units, sign conventions and dimensional consistency",
            "compare plausible alternatives without inventing missing design inputs",
            "trace how a changed parameter affects downstream calculations",
            "identify the investigation data needed before selecting a design approach",
            "separate preliminary sizing from code-based verification",
            "diagnose an implausible result using independent checks",
            "prepare a clear calculation and decision record for independent review",
        ],
        "operations": [
            {"id":"INTERPRET","title":"interpret the engineering brief","steps":["Classify the discipline, limit state or physical process involved.","List known inputs, required outputs, units and governing assumptions.","Identify missing site, material, load or boundary data before calculating."],"checks":["Inputs and units are explicit","The selected model matches the stated physical problem"]},
            {"id":"CALCULATE","title":"perform a bounded educational calculation","steps":["Select a formula only when its applicability and assumptions match the case.","Convert inputs consistently and retain intermediate values with units.","Check dimensions, limiting cases and physical reasonableness independently."],"checks":["Equations, inputs and intermediate units are shown","Result is labelled preliminary and not an approval"]},
            {"id":"ASSESS","title":"assess a preliminary engineering option","steps":["Define the performance objective and applicable failure modes.","Compare candidate options against confirmed parameters and constraints.","List the checks, standards and independent review still required."],"checks":["No unsupported code-compliance claim is made","Unverified safety-critical inputs remain open"]},
            {"id":"DIAGNOSE","title":"diagnose an unexpected calculation or site observation","steps":["Recheck source measurements, units, datum, sign convention and calculation sequence.","Test the result against an independent estimate or limiting case.","Separate data error, model limitation and possible physical behaviour."],"checks":["The original result is preserved for comparison","The cause is not asserted without supporting evidence"]},
            {"id":"INVESTIGATE","title":"plan the next investigation or field measurement","steps":["Identify the uncertainty that controls the engineering decision.","Select a proportionate field or laboratory observation and required accuracy.","Explain how the result changes the next analysis or design step."],"checks":["Investigation scope answers a specific engineering uncertainty","No ground or site condition is assumed without evidence"]},
            {"id":"CHANGE","title":"assess a design or construction change","steps":["Record the approved change and identify affected calculations and interfaces.","Recompute dependent values using the revised inputs and consistent assumptions.","Compare the revised result with the prior state and required acceptance checks."],"checks":["The change is traceable","Unaffected assumptions and results are not silently reused"]},
            {"id":"COORDINATE","title":"coordinate with another engineering discipline","steps":["Identify shared interfaces, loads, levels, flows or geometric boundaries.","Check that both disciplines use compatible units, revisions and design assumptions.","Record unresolved interfaces and the responsible reviewer."],"checks":["Interface assumptions are explicit","No discipline-specific approval is inferred from coordination alone"]},
            {"id":"REPORT","title":"prepare a calculation and review report","steps":["State the problem, source inputs, selected method and assumptions.","Present equations, intermediate values, result units and limitations.","List independent checks, required standards and unresolved decisions."],"checks":["A reviewer can reproduce the calculation","Limitations and approval boundaries are visible"]},
        ],
        "states": [
            {"id":"BRIEF","text":"only a short design brief is available and no verified site data is attached","steps":["Separate confirmed requirements from assumptions and request the missing investigation data."]},
            {"id":"CALC","text":"a preliminary calculation exists but its model and units are not documented","steps":["Reconstruct the input table and verify each equation and unit conversion before reusing the result."]},
            {"id":"FIELD","text":"site measurements and laboratory results are available with different dates and reference systems","steps":["Check datum, sampling location, test method and date before combining the records."]},
            {"id":"REVISION","text":"the design has changed after a previous calculation or drawing was issued","steps":["Identify which loads, dimensions, soil parameters and interfaces have changed since the prior revision."]},
            {"id":"FAILURE","text":"an independent check has produced a materially different result","steps":["Keep both calculations, compare assumptions and identify the exact source of divergence."]},
            {"id":"CONSTRUCTION","text":"construction observations reveal a possible departure from the design assumptions","steps":["Record the observation and preserve the issued design; do not approve a site change from incomplete evidence."]},
        ],
        "constraints": [
            {"id":"SOIL","text":"soil stratigraphy, groundwater or compressibility is uncertain","step":"Identify the ground model uncertainty and request investigation data appropriate to the foundation or slope mechanism.","checks":["Soil parameters are traceable to test or investigation evidence","Groundwater conditions are not guessed"]},
            {"id":"LOAD","text":"load combinations, support conditions or imposed actions are incomplete","step":"List missing actions and boundary conditions before selecting an analysis model.","checks":["Loads and support assumptions are explicit","No unprovided load is silently omitted or invented"]},
            {"id":"CODE","text":"the governing design standard or project jurisdiction is unspecified","step":"Ask which applicable standard, edition and project design basis governs before checking compliance.","checks":["No clause or factor is invented","Preliminary calculation is separated from code verification"]},
            {"id":"HYDRAULIC","text":"flow regime, roughness, tailwater or network operating condition is uncertain","step":"Identify the flow assumptions and boundary conditions required for the chosen hydraulic model.","checks":["Flow model matches the stated regime","Boundary conditions are sourced"]},
            {"id":"SURVEY","text":"survey coordinates, benchmark or setting-out reference may be inconsistent","step":"Verify control points, coordinate system, benchmark and closure before deriving levels or setting-out coordinates.","checks":["Survey reference is stated","Closure and tolerance are checked"]},
            {"id":"MATERIAL","text":"material properties or construction workmanship data are incomplete","step":"Request the specified material grade and verified test/quality records before using strength properties.","checks":["Material properties have an identified source","Construction quality is not assumed from drawings"]},
            {"id":"CONSTRUCTION","text":"the design must be built in stages with temporary conditions","step":"Check construction sequence, temporary stability and stage-specific load paths as separate cases.","checks":["Temporary works assumptions are listed","Final-state checks are not substituted for construction-stage checks"]},
            {"id":"INTERFACE","text":"a change in one discipline may affect a connected structure, road, drain or service","step":"Map the physical interface and identify calculations that must be repeated in adjacent disciplines.","checks":["Interface revisions are coordinated","Dependent checks are not omitted"]},
        ],
        "input_quality": [
            {"id":"CONFIRMED","text":"the required dimensions, loads, material data, units and design basis are confirmed","blocked":False,"step":"Use the confirmed inputs and state their source, units and applicable assumptions.","check":"Every material result is reproducible from the confirmed inputs."},
            {"id":"MISSING","text":"one or more safety-critical loads, soil parameters, material strengths or boundary conditions are absent","blocked":True,"step":"Identify the exact missing engineering input and request verified data; do not provide a final design value.","check":"No safety-critical value is invented or silently substituted."},
            {"id":"CONFLICT","text":"site records, drawings or discipline inputs contain contradictory values","blocked":True,"step":"List the conflicting source revisions and request an authorized resolution before calculating or approving the change.","check":"Conflicts are not resolved by arbitrary averaging or selection."},
            {"id":"UNVERIFIED","text":"the available data have no traceable test method, benchmark or approved revision","blocked":True,"step":"Quarantine the unverified inputs and specify the investigation or document check needed to admit them.","check":"Unverified evidence is not presented as measured or approved data."},
        ],
        "deliverables": [
            {"id":"CALC_NOTE","text":"a reproducible calculation note with equations and units","step":"Include input provenance, method, intermediate values, result, assumptions and independent check.","check":"Calculation is reproducible but is not labelled as professional approval."},
            {"id":"INVESTIGATION","text":"an investigation plan linked to the controlling uncertainty","step":"Specify location, method, sampling or measurement needs, accuracy and decision affected.","check":"Each proposed test addresses an identified uncertainty."},
            {"id":"OPTION","text":"a comparison of engineering options and unresolved design risks","step":"Compare options using only confirmed criteria and list data needed before selection.","check":"No preferred option is presented as safe without verification."},
            {"id":"REVIEW","text":"an independent engineering review checklist","step":"List governing standard, inputs, failure modes, calculations and independent sign-offs required.","check":"Every unverified or untested item remains visible."},
            {"id":"CHANGE_NOTE","text":"a revision impact note for a design or construction change","step":"Show old and new inputs, affected calculations and checks that must be repeated.","check":"The revision lineage is traceable."},
            {"id":"FIELD_REPORT","text":"a field observation and quality record","step":"Record location, date, method, reference, observed condition and required disposition.","check":"Observation is not mistaken for a design approval."},
        ],
    },
    "Complex engineering projects": {
        "contexts": [
            "a two-storey bungalow with coordinated architecture, structure and drainage",
            "a four-storey apartment building with repeated units and shared services",
            "a ten-storey office building with core, frame, facade and MEP interfaces",
            "a healthcare clinic with specialist rooms and controlled service zones",
            "a road and drainage corridor passing through an existing settlement",
            "a bridge approach with culvert, retaining works and road tie-ins",
            "an elevated water tower with foundation, access and pipework interfaces",
            "a pumping station with building, wet well, mechanical and electrical systems",
        ],
        "objectives": [
            "preserve design intent while coordinating all affected disciplines",
            "identify decisions that must be resolved before downstream work proceeds",
            "trace design changes through geometry, calculations, schedules and drawings",
            "minimize rework by resolving interfaces in a safe sequence",
            "maintain consistent levels, datums, units and model revisions",
            "distinguish concept proposals from verified engineering outputs",
            "prepare staged deliverables with clear owners and dependencies",
            "deliver a coordinated package with open risks and evidence visible",
        ],
        "operations": [
            {"id":"BRIEF","title":"decompose the project brief into discipline work packages","steps":["Extract deliverables, constraints, stakeholders and acceptance criteria.","Map architecture, civil, structural, geotechnical, MEP and documentation dependencies.","Identify blocking unknowns and assign each to a responsible discipline."],"checks":["Every package has inputs, outputs and dependencies","Critical unknowns are raised before downstream commitment"]},
            {"id":"CONCEPT","title":"develop and compare coordinated concept options","steps":["Define comparable options against the same confirmed project criteria.","Check site, spatial, structural and service interfaces for each option.","Record the trade-offs and identify which option needs further verification."],"checks":["Options use consistent assumptions","Concept geometry is not represented as a checked design"]},
            {"id":"INTEGRATE","title":"integrate discipline models and engineering records","steps":["Confirm each discipline's approved revision, coordinate frame and design basis.","Align interfaces and identify missing cross-discipline data.","Create a dependency map and coordinate controlled revisions."],"checks":["Model and calculation revisions are consistent","Interface ownership is recorded"]},
            {"id":"CHANGE","title":"manage a late project change","steps":["Record the change request and affected scope, requirements and approvals.","Trace impacts into geometry, calculations, quantities, services and documents.","Reissue only affected deliverables and record unaffected checks."],"checks":["Impact analysis precedes modification","Affected deliverables carry a consistent revision"]},
            {"id":"RISK","title":"resolve a high-priority coordination or engineering risk","steps":["Describe the physical risk, affected elements and evidence available.","Compare safe alternatives and identify required specialist review.","Track an approved resolution and repeat the relevant checks."],"checks":["Risk owner and acceptance authority are explicit","No safety-critical change is made without required review"]},
            {"id":"STAGE","title":"plan staged design and construction information","steps":["Separate design, procurement, temporary works and construction-stage deliverables.","Identify stage-specific constraints, approvals and dependencies.","Define what evidence is needed to close each stage."],"checks":["Construction sequence is not inferred from design geometry","Temporary and permanent conditions are distinguished"]},
            {"id":"AUDIT","title":"perform an integrated independent project review","steps":["Derive review criteria from the brief and approved project design basis.","Check consistency across models, calculations, schedules and drawings.","List pass, fail, missing and untested requirements by discipline."],"checks":["Review evidence spans all required disciplines","Open issues are not omitted from the summary"]},
            {"id":"HANDOVER","title":"prepare the coordinated project handover","steps":["Confirm approved deliverable revisions and required information formats.","Reconcile model, drawing, schedule, asset and issue-register contents.","Disclose unresolved decisions, deviations and lost exchange information."],"checks":["All deliverables identify the same approved revision","Handover gaps and open issues are explicit"]},
        ],
        "states": [
            {"id":"EARLY","text":"the project is at concept stage and discipline inputs are incomplete","steps":["Separate confirmed project constraints from provisional assumptions and hold downstream decisions that depend on missing inputs."]},
            {"id":"DESIGN","text":"several discipline models and preliminary calculations are in progress","steps":["Create a revision and dependency register before coordinating interfaces."]},
            {"id":"CLASH","text":"the coordinated model contains multiple unresolved cross-discipline conflicts","steps":["Classify issues by severity, owner and downstream effect before revising any model."]},
            {"id":"CHANGE","text":"the client has requested a late change after drawings and quantities were prepared","steps":["Freeze the current approved baseline and trace the change into every affected deliverable."]},
            {"id":"CONSTRUCTION","text":"construction-stage observations may differ from the issued design information","steps":["Preserve the issued baseline and distinguish verified site observations from proposed deviations."]},
            {"id":"HANDOVER","text":"the project is approaching handover with outstanding information and review actions","steps":["Audit completeness and keep open issues separate from accepted deliverables."]},
        ],
        "constraints": [
            {"id":"SCOPE","text":"the requested scope spans disciplines but the responsibility boundary is not explicit","step":"Identify discipline ownership, design responsibility and approval authority before assigning work.","checks":["Work packages have clear owners","No approval responsibility is assumed"]},
            {"id":"DATUM","text":"architectural, structural and civil models may use different datums or levels","step":"Reconcile survey origin, north rotation, project levels and units across the project.","checks":["Shared reference points agree","Coordinate transformations are recorded"]},
            {"id":"SAFETY","text":"a proposed change may affect a load path, ground condition or safety-critical service","step":"Stop the affected design action and request specialist review using confirmed evidence.","checks":["Safety-critical review is explicitly assigned","No unverified structural or service change is accepted"]},
            {"id":"PROGRAMME","text":"the project must be delivered in phases with dependencies and temporary conditions","step":"Map predecessor tasks and distinguish permanent works from temporary stages.","checks":["Stage dependencies are valid","Temporary works are not omitted"]},
            {"id":"BUDGET","text":"the client has a cost constraint but quantities and rates are incomplete","step":"Identify quantity sources and unresolved rate assumptions before comparing cost options.","checks":["Quantities are traceable","No unsupported cost certainty is claimed"]},
            {"id":"EXISTING","text":"the work must interface with existing assets whose condition is partly unknown","step":"Separate verified existing information from assumptions and specify necessary surveys or opening-up inspections.","checks":["Existing asset provenance is recorded","Unknown conditions remain visible"]},
            {"id":"REGULATORY","text":"the project approval basis or applicable jurisdiction is not yet confirmed","step":"Request the governing approval criteria and applicable standard before compliance checks.","checks":["No regulatory compliance is claimed prematurely","Approval path is recorded"]},
            {"id":"REVISION","text":"different deliverables may have been produced from different model revisions","step":"Establish one approved baseline and reconcile all downstream documents before issue.","checks":["Cross-discipline revision consistency is confirmed","Superseded outputs are identified"]},
        ],
        "input_quality": [
            {"id":"CONFIRMED","text":"the project brief, scope, discipline revisions and design basis are approved","blocked":False,"step":"Proceed only within the approved scope and preserve discipline ownership and revision lineage.","check":"Each coordinated decision has a traceable input and owner."},
            {"id":"MISSING","text":"a critical site, design-basis or discipline input is absent","blocked":True,"step":"List the blocking input, responsible discipline and decision it affects; hold dependent work until confirmed.","check":"No missing scope or safety-critical input is fabricated."},
            {"id":"CONFLICT","text":"two discipline deliverables or project requirements disagree","blocked":True,"step":"Record both source revisions and request resolution by the authorized design lead before modifying linked deliverables.","check":"Conflicting design instructions are not silently reconciled."},
            {"id":"UNVERIFIED","text":"an existing asset or construction observation has not been independently verified","blocked":True,"step":"Quarantine the observation as unverified and specify the survey or inspection needed before design reliance.","check":"Unverified site information is not represented as as-built truth."},
        ],
        "deliverables": [
            {"id":"WORKPACKAGES","text":"a coordinated discipline work-package and dependency register","step":"List package scope, input, output, owner, predecessor and acceptance evidence.","check":"No critical dependency is left without an owner."},
            {"id":"COORDINATED","text":"a coordinated multidisciplinary model and issue register","step":"Summarize model revisions, shared datums, interface checks and unresolved issues.","check":"Each issue links to the exact affected model revision."},
            {"id":"DESIGN_REPORT","text":"an integrated design decision report","step":"Compare confirmed options, assumptions, design checks and specialist reviews required.","check":"Concept proposals and verified calculations remain distinct."},
            {"id":"CHANGE_CONTROL","text":"a project change-impact and revision-control record","step":"Show affected disciplines, drawings, quantities, model objects and required rechecks.","check":"All affected deliverables share a controlled revision."},
            {"id":"STAGE_PLAN","text":"a staged delivery and construction information plan","step":"Identify stage gates, temporary conditions, approvals and evidence required for closure.","check":"Planned activities are not reported as completed construction."},
            {"id":"HANDOVER","text":"a coordinated handover package with exception register","step":"Reconcile the approved models, drawings, schedules, asset information and open actions.","check":"Open items and deviations are explicitly disclosed."},
        ],
    },
    "Native operator, tool selection and recovery": {
        "contexts": [
            "a user asks NextAI to create or revise a component inside NextCAD",
            "a user asks NextAI to create or revise an information model inside Next BIM",
            "a user opens a legacy CAD document with unfamiliar feature history",
            "a user opens an IFC project with unfamiliar entities and relationships",
            "a multi-step request spans CAD geometry, BIM objects and engineering calculations",
            "a previous tool transaction failed and the model state is uncertain",
            "a project has changed since the last tool discovery and schema capture",
            "a user asks for a deliverable that the installed native tools may not support",
        ],
        "objectives": [
            "discover the available capability before selecting a native operation",
            "select exact tools and typed arguments without inventing command schemas",
            "decompose a large request into reversible, inspectable actions",
            "preserve object identity and dependencies during revision",
            "stop safely when required information or permission is missing",
            "diagnose failure from the actual application state rather than guessing",
            "verify persistence through save, close and reopen evidence",
            "report completed, failed, skipped and untested work honestly",
        ],
        "operations": [
            {"id":"INTAKE","title":"conduct a design-intake conversation","steps":["Extract requested outcome, scope, units, constraints and acceptance criteria.","Ask concise questions only for information that blocks a safe next action.","Record confirmed and unresolved inputs separately."],"checks":["Critical ambiguity is resolved before a write","User intent and constraints remain traceable"]},
            {"id":"DISCOVER","title":"discover a native capability and its schema","steps":["Inspect the live application identity, version and registered capability catalogue.","Read the exact command schema, required fields, defaults and permission boundary.","Reject guessed aliases or stale command assumptions."],"checks":["Selected operation exists in the current live schema","Arguments match declared types and required fields"]},
            {"id":"PLAN","title":"decompose the request into a tool plan","steps":["Break the outcome into ordered preconditions, reads, writes and validations.","Identify reversible checkpoints and dependencies between operations.","Expose the proposed plan and required approvals before executing writes."],"checks":["Every write has a known precondition and postcondition","Plan has rollback or recovery behaviour"]},
            {"id":"EXECUTE","title":"execute a bounded native tool sequence","steps":["Read the current state and confirm the target object identity.","Execute one coherent operation using exact typed arguments.","Inspect the returned state before continuing to the next dependent operation."],"checks":["Each operation has an observed result","No later step assumes an uninspected state"]},
            {"id":"RECOVER","title":"recover from a failed operation","steps":["Capture error text, tool response and current application state.","Determine whether the operation partially changed the document.","Use a verified rollback or preserve the state for user intervention."],"checks":["Failure is not hidden or retried blindly","Recovery preserves the last known-good artifact"]},
            {"id":"REVISE","title":"revise a model without replacing unrelated objects","steps":["Resolve the target object using stable IDs and inspect its dependency graph.","Modify the smallest approved set of parameters or relationships.","Compare identities and dependent state before and after the revision."],"checks":["Object identity persists","Unrelated elements remain unchanged"]},
            {"id":"VERIFY","title":"verify a saved native result","steps":["Check application success, object state and required geometric or semantic properties.","Save to a controlled revision and close the document.","Reopen the saved artifact and repeat the acceptance checks."],"checks":["Save and reopen succeed","Verified state matches the required postconditions"]},
            {"id":"DECLINE","title":"handle an unsupported or unauthorized operation","steps":["Check the live capability catalogue and permission state.","Explain the specific unsupported or blocked requirement and its consequence.","Offer a safe read-only inspection or ask for the needed capability/approval."],"checks":["No substitute command is guessed","Unsupported work is reported as not performed"]},
        ],
        "states": [
            {"id":"KNOWN","text":"the application and current document are open and their state can be inspected","steps":["Record application version, document identity and the current state before planning a write."]},
            {"id":"STALE","text":"a cached tool list may not match the current application version","steps":["Refresh capability discovery and invalidate stale schemas before selecting any tool."]},
            {"id":"PARTIAL","text":"the document may contain unsaved changes from an earlier session","steps":["Identify dirty state and create a recoverable checkpoint before continuing."]},
            {"id":"UNCERTAIN","text":"the previous write may have partially succeeded despite an error response","steps":["Read the actual post-error document state and compare it with the last known-good snapshot."]},
            {"id":"CLOSED","text":"the user has closed or switched away from the target document","steps":["Reacquire the intended document and confirm its stable identity before acting."]},
            {"id":"REOPENED","text":"the document has been reopened and must be checked for persistence","steps":["Verify persisted object identities, properties and relationships rather than trusting the prior save message."]},
        ],
        "constraints": [
            {"id":"SCHEMA","text":"the proposed command may have changed or may not be registered","step":"Refresh the live registry and reject a command whose current schema is unavailable.","checks":["Command name and version are observed","Unknown fields are not passed"]},
            {"id":"PERMISSION","text":"the operation may require user approval or a write permission","step":"Inspect permission state and request explicit approval before any protected mutation.","checks":["No write bypasses the permission boundary","Approval is tied to the specific action"]},
            {"id":"PRECONDITION","text":"the target object or required reference may not exist in the current document","step":"Read the document and verify each precondition before invoking a dependent tool.","checks":["Missing targets are reported","A guessed object identity is never used"]},
            {"id":"PARTIAL_WRITE","text":"a tool may have partially modified the document before returning an error","step":"Inspect actual document state and compare object counts, IDs and relevant properties before retrying.","checks":["Retry occurs only after state inspection","Partial changes are preserved or safely rolled back"]},
            {"id":"DEPENDENCY","text":"a requested edit may break dependent objects, drawings or IFC relationships","step":"Inspect the dependency graph and define preservation checks before modifying the target.","checks":["Downstream references are included in acceptance checks","Unrelated objects are protected"]},
            {"id":"SAVE","text":"the result may be visible in memory but not persisted to the native file","step":"Use the application's verified save operation and independently reopen the artifact.","checks":["Persistence is checked after reopen","An in-memory state is not reported as saved"]},
            {"id":"UNSUPPORTED","text":"the requested operation is absent from the installed capability catalogue","step":"State the exact capability gap and do not substitute a similar command without user approval.","checks":["Unsupported capability is reported honestly","No fabricated command execution is claimed"]},
            {"id":"CANCEL","text":"the user may cancel or revise the request during a multi-step operation","step":"Check the current authorization and stop at a safe checkpoint when the scope changes or is withdrawn.","checks":["Cancelled writes do not continue","Current user intent is reconfirmed for changed scope"]},
        ],
        "input_quality": [
            {"id":"CONFIRMED","text":"the request, target document, required values and action permission are confirmed","blocked":False,"step":"Proceed through the inspected plan one bounded operation at a time.","check":"Each write is authorized and its post-state is inspected."},
            {"id":"MISSING","text":"the request lacks a required target, dimension, schema field or approval","blocked":True,"step":"Ask for the missing information or permission and keep the native write plan empty.","check":"No tool is called with an invented argument or implicit approval."},
            {"id":"CONFLICT","text":"the user request conflicts with the current model state or a prior constraint","blocked":True,"step":"Describe the conflict and ask which state or requirement should govern before writing.","check":"The agent does not silently choose between incompatible instructions."},
            {"id":"UNVERIFIED","text":"the live application state or tool catalogue cannot currently be read","blocked":True,"step":"Stop writes and explain which live state or schema must be reacquired first.","check":"Cached or guessed state is not represented as live evidence."},
        ],
        "deliverables": [
            {"id":"PLAN","text":"a validated operation plan with preconditions and postconditions","step":"Return ordered reads, proposed writes, validations, rollback points and unresolved prerequisites.","check":"No action is represented as executed merely because it was planned."},
            {"id":"TRACE","text":"an auditable native operation trace","step":"Record tool IDs, typed arguments, timestamps, responses and state fingerprints with secrets redacted.","check":"Trace fields correspond to observed tool calls."},
            {"id":"RECOVERY","text":"a recovery report preserving the last known-good state","step":"List the failure, observed post-error state, safe recovery taken and remaining risks.","check":"No destructive retry occurs without a verified recovery path."},
            {"id":"VERIFICATION","text":"a save/reopen verification report","step":"Show the saved artifact identity, reopen result and repeated acceptance checks.","check":"Persistence evidence is separate from in-memory success."},
            {"id":"GAP","text":"an unsupported-capability or permission-gap report","step":"Identify the missing command, schema, permission or user decision and the safe next step.","check":"The report does not claim the unavailable operation was completed."},
            {"id":"HANDOFF","text":"a user-facing completion and exception summary","step":"Separate completed, failed, blocked, skipped and untested actions with artifact references.","check":"Every completion claim has matching observed evidence."},
        ],
    },
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _subject_target_counts() -> dict[str, int]:
    by_collection: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in SPECS:
        by_collection[COLLECTION_BY_APPLICATION[spec["application"]]].append(spec)
    counts: dict[str, int] = {}
    for collection, specs in by_collection.items():
        quotient, remainder = divmod(TARGET_PER_COLLECTION, len(specs))
        for index, spec in enumerate(sorted(specs, key=lambda item: item["id"])):
            counts[spec["id"]] = quotient + (1 if index < remainder else 0)
    return counts


def _draw_scenarios(
    spec_id: str,
    profile: dict[str, list[Any]],
    count: int,
    input_count: int,
) -> list[tuple[int, ...]]:
    lengths = [len(profile[key]) for key in (
        "contexts", "objectives", "operations", "states", "constraints",
        "input_quality", "deliverables",
    )] + [input_count]
    capacity = 1
    for length in lengths:
        capacity *= length
    if count > capacity:
        raise ValueError(f"{spec_id} needs {count} distinct scenarios but its matrix has only {capacity}")
    seed = SEED + int(_digest(spec_id)[:8], 16)
    rng = random.Random(seed)
    selected: set[tuple[int, ...]] = set()
    # Keep useful, executable work as the majority of the curriculum.
    # Missing/conflicting/unverified briefs remain important but must not swamp
    # positive examples. The 70/10/10/10 mix is exact per subject expansion.
    quality_quotas = [
        count * 7 // 10,
        count // 10,
        count // 10,
        count - (count * 7 // 10) - (count // 10) - (count // 10),
    ]
    for quality_index, quota in enumerate(quality_quotas):
        quality_selected = 0
        attempts = 0
        max_attempts = max(10_000, quota * 100)
        while quality_selected < quota:
            attempts += 1
            if attempts > max_attempts:
                raise ValueError(
                    f"Could not draw {quota} distinct scenarios for input-quality stratum "
                    f"{quality_index} in {spec_id}"
                )
            values = [rng.randrange(length) for length in lengths]
            values[5] = quality_index
            vector = tuple(values)
            if vector in selected:
                continue
            selected.add(vector)
            quality_selected += 1
    result = list(selected)
    rng.shuffle(result)
    return result


def _build_prompt(spec: dict[str, Any], scenario: dict[str, Any]) -> str:
    lines = [
        "Original learning objective: " + spec["prompt"],
        "Scenario specialization (answer this case, not a generic paraphrase):",
        "Project context: " + scenario["context"],
        "Primary objective: " + scenario["objective"],
        "Requested operation: " + scenario["operation"]["title"],
        "Starting state: " + scenario["state"]["text"],
        "Constraint or issue: " + scenario["constraint"]["text"],
        "Input status: " + scenario["input_quality"]["text"],
        "Specific input/reference under review: " + scenario["affected_input"],
        "Required deliverable: " + scenario["deliverable"]["text"],
        "Give an ordered, reversible workflow. Identify the live native capabilities and exact schemas that must be inspected; do not invent command names or arguments.",
        "If information quality blocks safe action, ask for the missing resolution and return an empty native write plan.",
        "Separate authored planning knowledge from actual native execution and professional engineering verification.",
    ]
    return "\n".join(lines)


def _build_completion(spec: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    operation = scenario["operation"]
    state = scenario["state"]
    constraint = scenario["constraint"]
    input_quality = scenario["input_quality"]
    deliverable = scenario["deliverable"]
    blocked = bool(input_quality["blocked"])
    workflow: list[str]
    if blocked:
        workflow = [
            "Stop before any native write and preserve the current document/model state.",
            input_quality["step"],
            "Record the unresolved decision, its source and the action that remains blocked.",
        ]
    else:
        workflow = (
            list(spec["workflow"][:3])
            + list(operation["steps"])
            + list(state["steps"])
            + [constraint["step"], deliverable["step"]]
        )
    return {
        "schema": "nextai.scaled_practical_response.v1",
        "curriculum_version": VERSION,
        "scenario_id": spec["id"],
        "collection": COLLECTION_BY_APPLICATION[spec["application"]],
        "application_scope": spec["application"],
        "stage": spec["stage"],
        "task_type": spec["task_type"],
        "scenario_axes": {
            "project_context": scenario["context"],
            "primary_objective": scenario["objective"],
            "operation": operation["id"],
            "starting_state": state["id"],
            "constraint": constraint["id"],
            "input_quality": input_quality["id"],
            "deliverable": deliverable["id"],
            "affected_input": scenario["affected_input"],
        },
        "confirmed_inputs": (
            list(spec["inputs"])
            if not blocked
            else [item for item in spec["inputs"] if item != scenario["affected_input"]]
        ),
        "unresolved_inputs": (
            [] if not blocked else [{
                "input": scenario["affected_input"],
                "status": input_quality["id"],
                "required_resolution": input_quality["step"],
            }]
        ),
        "workflow": [{"sequence": index + 1, "objective": item} for index, item in enumerate(workflow)],
        "acceptance_checks": (
            list(spec["checks"][:3])
            + list(operation["checks"])
            + list(constraint["checks"])
            + [input_quality["check"], deliverable["check"]]
        ),
        "failure_modes_to_watch": list(spec["failures"][:3]),
        "limitations_and_non_claims": list(spec["limits"]) + [
            "This generated scenario is L0 authored learning material, not evidence of native application execution.",
            "A geometry or information-model check does not establish professional engineering adequacy or statutory compliance.",
            "Use only the live application's declared tools and schemas; report unsupported capabilities explicitly.",
        ],
        "evidence_level": "L0_authored_learning_example",
        "execution_status": "not_executed_by_this_example",
        "execution_blocked_until_clarification": blocked,
        "native_write_plan": [] if blocked else "requires live state, declared tool schemas and action-specific authorization",
        "blocking_reason": (
            f"{scenario['affected_input']}: {input_quality['text']}" if blocked else None
        ),
        "deliverable": deliverable["text"],
        "training_note": "Distinct structured scenario from the authored practical curriculum; not a native success trace.",
    }


def make_scaled_curriculum_expansion() -> list[dict[str, Any]]:
    """Return the 99,380 new rows needed to bring every collection to 20,000."""
    baseline = make_master_project_curriculum()
    subject_targets = _subject_target_counts()
    baseline_per_subject = Counter(row["curriculum_subject_id"] for row in baseline)
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for spec in SPECS:
        collection = COLLECTION_BY_APPLICATION[spec["application"]]
        target = subject_targets[spec["id"]]
        current = baseline_per_subject[spec["id"]]
        if current != 10 or target < current:
            raise ValueError(f"Unexpected baseline/target count for {spec['id']}: {current}/{target}")
        profile = PROFILES[collection]
        vectors = _draw_scenarios(spec["id"], profile, target - current, len(spec["inputs"]))
        for number, vector in enumerate(vectors, start=1):
            scenario = {
                "context": profile["contexts"][vector[0]],
                "objective": profile["objectives"][vector[1]],
                "operation": profile["operations"][vector[2]],
                "state": profile["states"][vector[3]],
                "constraint": profile["constraints"][vector[4]],
                "input_quality": profile["input_quality"][vector[5]],
                "deliverable": profile["deliverables"][vector[6]],
                "affected_input": spec["inputs"][vector[7]],
            }
            scenario_payload = {
                "subject": spec["id"],
                "axes": [
                    scenario["context"], scenario["objective"],
                    scenario["operation"]["id"], scenario["state"]["id"],
                    scenario["constraint"]["id"], scenario["input_quality"]["id"],
                    scenario["deliverable"]["id"], scenario["affected_input"],
                ],
            }
            scenario_hash = _digest(json.dumps(scenario_payload, sort_keys=True, ensure_ascii=False))
            record_id = f"{VERSION}-{spec['id']}-{scenario_hash[:20]}"
            target_payload = _build_completion(spec, scenario)
            row = {
                "record_id": record_id,
                "domain": spec["domain"],
                "system": (
                    "You are NextAI, a careful engineering design-and-build operator. "
                    "Use only confirmed inputs and live declared capabilities. Inspect state after each action. "
                    "Never invent engineering values, native commands, execution results or professional approvals."
                ),
                "prompt": _build_prompt(spec, scenario),
                "completion": json.dumps(target_payload, ensure_ascii=False, sort_keys=True),
                "images": [],
                "source": "Next3D scaled practical curriculum v1",
                "license": "project-authored",
                "split_group": "scaled-curriculum-" + scenario_hash,
                "stage": spec["stage"],
                "curriculum_version": VERSION,
                "curriculum_item_id": record_id,
                "curriculum_subject_id": spec["id"],
                "curriculum_collection": collection,
                "curriculum_variant_id": "SCENARIO_MATRIX",
                "application": spec["application"],
                "evidence_level": "L0_authored_learning_example",
                "scenario_hash": scenario_hash,
                "scenario_axes": target_payload["scenario_axes"],
                "_collection": collection,
            }
            pools[collection].append(row)

    # Split each collection as a unit so the complete practical curriculum is
    # exactly 80/10/10 after adding the original v2 rows.
    baseline_by_collection_split = Counter(
        (row["curriculum_collection"], row["curriculum_split"]) for row in baseline
    )
    output: list[dict[str, Any]] = []
    for collection in COLLECTIONS:
        rows = pools[collection]
        rng = random.Random(SEED + int(_digest(collection)[:8], 16))
        rng.shuffle(rows)
        target_train = int(TARGET_PER_COLLECTION * TARGET_SPLITS["train"])
        target_validation = int(TARGET_PER_COLLECTION * TARGET_SPLITS["validation"])
        target_test = TARGET_PER_COLLECTION - target_train - target_validation
        needs = {
            "train": target_train - baseline_by_collection_split[(collection, "train")],
            "validation": target_validation - baseline_by_collection_split[(collection, "validation")],
            "test": target_test - baseline_by_collection_split[(collection, "test")],
        }
        if sum(needs.values()) != len(rows) or min(needs.values()) < 0:
            raise ValueError(f"Split target does not reconcile for {collection}: {needs}, rows={len(rows)}")
        cursor = 0
        for split in ("train", "validation", "test"):
            count = needs[split]
            for row in rows[cursor:cursor + count]:
                row["curriculum_split"] = split
                # The supervised target carries the same explicit split label.
                completion = json.loads(row["completion"])
                completion["data_split"] = split
                row["completion"] = json.dumps(completion, ensure_ascii=False, sort_keys=True)
                row.pop("_collection", None)
                output.append(row)
            cursor += count
        if cursor != len(rows):
            raise ValueError(f"Unassigned examples remain for {collection}")
    if len(output) != TARGET_PER_COLLECTION * len(COLLECTIONS) - len(baseline):
        raise ValueError("Scaled practical expansion did not meet the exact 100k collection targets")
    ids = [row["record_id"] for row in output]
    prompts = [" ".join(row["prompt"].lower().split()) for row in output]
    if len(ids) != len(set(ids)) or len(prompts) != len(set(prompts)):
        raise ValueError("Scaled practical expansion contains duplicate IDs or normalized prompts")
    return output


def separate_scaled_curriculum_splits(
    splits: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    scaled = {name: [] for name in ("train", "validation", "test")}
    remainder = {name: [] for name in ("train", "validation", "test")}
    for split in ("train", "validation", "test"):
        for row in splits.get(split, []):
            target = scaled if row.get("curriculum_version") == VERSION else remainder
            target[split].append(row)
    for split, rows in scaled.items():
        if any(row.get("curriculum_split") != split for row in rows):
            raise ValueError(f"Scaled curriculum has a {split} row with a conflicting split label")
    return scaled, remainder


def summarize_scaled_curriculum(
    expansion_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    baseline = baseline_rows if baseline_rows is not None else make_master_project_curriculum()
    all_rows = list(baseline) + list(expansion_rows)
    by_collection = Counter(row["curriculum_collection"] for row in all_rows)
    by_split = Counter(row.get("curriculum_split") for row in baseline)
    by_split.update(row.get("curriculum_split") for row in expansion_rows)
    by_subject = Counter(row["curriculum_subject_id"] for row in all_rows)
    expected = {name: TARGET_PER_COLLECTION for name in COLLECTIONS}
    actual = {name: by_collection[name] for name in COLLECTIONS}
    if actual != expected:
        raise ValueError(f"Practical curriculum collection counts differ from target: {actual}")
    expected_splits = {
        "train": TARGET_PER_COLLECTION * len(COLLECTIONS) * 80 // 100,
        "validation": TARGET_PER_COLLECTION * len(COLLECTIONS) * 10 // 100,
        "test": TARGET_PER_COLLECTION * len(COLLECTIONS) * 10 // 100,
    }
    actual_splits = {name: by_split[name] for name in ("train", "validation", "test")}
    if actual_splits != expected_splits:
        raise ValueError(f"Practical curriculum split counts differ from 80/10/10: {actual_splits}")
    if len({row["record_id"] for row in all_rows}) != len(all_rows):
        raise ValueError("Practical curriculum record IDs are not globally unique")
    if len({" ".join(row["prompt"].lower().split()) for row in all_rows}) != len(all_rows):
        raise ValueError("Practical curriculum normalized prompts are not globally unique")
    if len(by_subject) != len(SPECS):
        raise ValueError("Practical curriculum subject coverage is incomplete")
    if any(count != 0 for count in Counter(row.get("curriculum_split") for row in all_rows if row.get("curriculum_split") not in {"train","validation","test"}).values()):
        raise ValueError("Practical curriculum contains an invalid split label")
    blocked = 0
    for row in expansion_rows:
        target = json.loads(row["completion"])
        if target.get("evidence_level") != "L0_authored_learning_example":
            raise ValueError(f"{row['record_id']} has a false evidence level")
        if target.get("execution_status") != "not_executed_by_this_example":
            raise ValueError(f"{row['record_id']} claims native execution")
        if target.get("execution_blocked_until_clarification"):
            blocked += 1
            if target.get("native_write_plan") != []:
                raise ValueError(f"{row['record_id']} must have an empty native write plan")
    return {
        "version": VERSION,
        "target_per_collection": TARGET_PER_COLLECTION,
        "collection_count": len(COLLECTIONS),
        "total_examples_including_v2_baseline": len(all_rows),
        "new_expansion_examples": len(expansion_rows),
        "by_collection": actual,
        "by_split": actual_splits,
        "by_subject": dict(sorted(by_subject.items())),
        "blocked_until_clarification_examples_in_expansion": blocked,
        "unique_record_ids": len({row["record_id"] for row in all_rows}),
        "unique_normalized_prompts": len({" ".join(row["prompt"].lower().split()) for row in all_rows}),
        "scenario_dimensions": [
            "project_context", "primary_objective", "operation", "starting_state",
            "constraint", "input_quality", "deliverable", "affected_input",
        ],
        "evidence_level": "L0_authored_learning_example",
        "native_execution_claimed": False,
        "split_policy": "Exact 80% train, 10% validation, 10% held-out test per collection; unique scenario groups do not cross splits.",
    }
