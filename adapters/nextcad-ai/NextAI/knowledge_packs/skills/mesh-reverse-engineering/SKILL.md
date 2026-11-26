---
name: mesh-reverse-engineering
description: Inspect, repair, measure and reconstruct mesh, point-cloud and scanned geometry without confusing tessellations with editable BRep solids.
tags: [freecad, nextcad, mesh, stl, obj, point-cloud, scan, reverse-engineering, tessellation, reconstruction]
aliases: [Mesh workbench, point cloud, scan to CAD, reverse engineering, mesh repair]
---

# Mesh, point cloud and reverse engineering

## Identify the source representation

Clarify whether the input is a triangle mesh, point cloud, tessellated surface, BRep solid, scan or a mixed dataset. Establish units, coordinate frame, scale reference, scan accuracy, registration/alignment and the required downstream result.

A mesh is not automatically a solid and a shaded render is not a measured surface. Point clouds may be incomplete, noisy or non-uniformly sampled.

## Workflow

1. Inspect file type, units, bounds, point/triangle counts, normals, connected components and source provenance.
2. Confirm scale and alignment using known reference dimensions or registration targets.
3. Diagnose holes, disconnected islands, duplicate faces, flipped normals, self-intersections, non-manifold edges and noise.
4. Repair only with a clear record of changed topology and tolerances.
5. Decide whether a cleaned mesh is sufficient or whether a BRep/NURBS reconstruction is actually required.
6. For reverse engineering, identify geometric primitives/features (planes, cylinders, cones, spheres, profiles) from measured data and fit them within declared tolerances.
7. Preserve the original scan; create a separate aligned/cleaned/reconstructed document.
8. Compare reconstructed geometry against the source using deviation maps or sampled distances when tools are available.
9. Save source and derived data with coordinate transform and provenance.

## Native capability rules

Discover Mesh, MeshPart, Points and ReverseEngineering tools, plus the exact import/repair/measurement APIs. Do not claim a scan has become editable native CAD merely because an STL imports. If reconstruction/fit operations are not available through a reviewed adapter, state that limitation.
