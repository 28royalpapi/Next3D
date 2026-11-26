---
name: fem-analysis-preparation
description: Prepare finite-element analyses with material, mesh, support, load, solver and convergence evidence.
tags: [freecad, nextcad, fem, finite-element, analysis, mesh, materials, loads, boundary-conditions, convergence]
aliases: [FEM workbench, finite element analysis, structural analysis, CAE, simulation]
---

# FEM / CAE analysis preparation

## Confirm that an analysis can be defined

Ask for analysis objective, geometry revision, material properties, load cases, supports/constraints, contact assumptions, temperature or other field conditions, solver preference, acceptance quantities and applicable design basis. Establish whether the user wants a learning example, a setup model, a preliminary simulation or a verified engineering study.

Check that the required solver, mesh tools and post-processing dependencies are actually installed and available in this build. A source workbench directory is not proof that a solver is usable.

## FEM workflow

1. Inspect the native geometry and choose the correct analysis domain (structural, thermal, modal or another supported type).
2. Remove or simplify geometry only with a documented reason; retain the original model.
3. Assign real material properties and units from a trusted source or user specification.
4. Define supports, loads, contacts, symmetry and connections consistently with physical reality.
5. Create the mesh with controlled element type, size, local refinement and quality checks.
6. Run the selected solver and capture version, settings, warnings, convergence and residual information.
7. Inspect displacement, stress, strain, reactions, energy and other requested results; check equilibrium and expected deformation modes.
8. Perform mesh-convergence/sensitivity and load-case comparisons where appropriate.
9. Compare results with hand checks, validated benchmark solutions or independent calculations.
10. Record solver files, source geometry revision, material/load assumptions and result artifacts.

## Boundaries

A solver returning a result is not proof of structural adequacy. Missing or unrealistic materials, loads, supports, contacts or mesh can produce plausible but wrong pictures. Do not claim factor of safety, code compliance or construction suitability without verified inputs, suitable design checks and qualified review.

## Current adapter coverage

The student must discover the live Fem workbench and solver state. If no FEM tool adapter or solver is present, it may explain and prepare a checklist, but it must not pretend to have executed an analysis.
