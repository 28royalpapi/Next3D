---
name: civil-road-drainage
description: Plan and model civil site, road, earthworks, stormwater drainage and utility coordination tasks with survey, levels and engineering inputs.
tags: [civil, road, highway, drainage, stormwater, culvert, earthworks, site, grading, water-network]
aliases: [road design, drainage design, storm water, stormwater, culvert, site grading, pavement]
---

# Civil site, road and drainage modelling

## Intake and design basis

Ask what is being designed: site grading, road alignment, junction, pavement, stormwater drainage, culvert, retaining structure, water network or coordinated infrastructure model.

Collect relevant inputs rather than asking a generic long questionnaire:
- survey/topographic source, coordinate reference system, units, vertical datum and existing levels;
- alignment, chainage, road reserve/ROW, access points, design speed and cross-section needs;
- terrain, boundaries, tie-in points, utilities and existing assets;
- rainfall/runoff basis, catchment area, return period and applicable hydrology method for drainage;
- flow direction, outfall level, invert levels, pipe/channel sizes and allowable cover where known;
- soil/geotechnical data, groundwater, pavement traffic/loading basis and material properties where relevant;
- jurisdiction, standard edition, deliverable level and whether the model is schematic or engineered.

Do not invent a topographic survey, storm event, runoff coefficient, friction coefficient, soil value, road design speed or design standard.

## Model structure

Separate:
- site boundary and existing terrain;
- road centreline/alignment and stationing;
- horizontal/vertical profile and cross-section references;
- pavement layers, shoulders, kerbs and junction geometry;
- earthworks cut/fill surfaces;
- drainage catchments, inlets, manholes, pipes/channels, culverts and outfalls;
- existing/proposed utilities and coordination clearances.

Use actual survey coordinates and consistent units/datum. A polyline drawn in plan is not a road corridor; a cylinder is not proof of a hydraulically connected pipe network. Use specialist native tools only if they exist and are verified in the installed build.

## Work sequence

1. Inspect the survey and establish coordinate/datum integrity.
2. Build the site boundary, control points and terrain representation.
3. Create and inspect road alignment, profile and design cross-section.
4. Add pavement and earthworks components as editable objects/surfaces.
5. Establish drainage catchments and levels before routing pipes/channels.
6. Model inlets, manholes, culverts, pipes and outfalls with explicit invert/elevation data.
7. Check gradients, cover, conflicts and continuity using native measurement/network tools if available.
8. Produce plan/profile/section views, quantities and asset schedules.
9. Save/reopen and perform appropriate exchange checks.

## Deliverables and boundaries

Schedules should include chainage, coordinates, levels, alignment or asset mark, dimensions, material (when assigned), quantity, source and verification status. Distinguish existing survey facts from proposed design geometry.

A model does not prove drainage capacity, flood safety, pavement life, road safety, slope stability, geotechnical adequacy or code compliance. These require verified survey/design inputs, engineering calculations, suitable analysis and independent review.
