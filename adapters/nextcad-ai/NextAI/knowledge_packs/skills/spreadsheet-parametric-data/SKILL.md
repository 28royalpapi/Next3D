---
name: spreadsheet-parametric-data
description: Use native FreeCAD spreadsheets for named parameters, expressions, schedules, quantities and traceable model data.
tags: [freecad, nextcad, spreadsheet, variables, expressions, parameters, schedule, bill-of-materials, quantities]
aliases: [Spreadsheet workbench, parameter table, bill of materials, BOM, component schedule, variable set]
---

# Spreadsheet and parametric data

## Choose the spreadsheet purpose

Clarify whether the sheet is a design-parameter table driving model geometry, a quantity/schedule report extracted from the model, an engineering calculation, or a general project data register. These are different purposes and should be labelled distinctly.

## Model-driving variables

- Use a dedicated parameter namespace/VarSet or spreadsheet aliases to avoid ambiguous cell references.
- Give each parameter a stable name, value, unit, source and status.
- Bind native object properties or named constraints to explicit expressions.
- Inspect expression resolution and recompute after changing a value.
- Test critical parameter changes to confirm intended dependencies and feature history remain valid.
- Avoid circular dependencies and silently changing a property's type.

## Model-derived schedules

- Read native object IDs, labels, types and measured geometry/properties.
- Record units and source object IDs so users can trace each row to the model.
- Separate user-confirmed, proposed, derived, modelled and measured values.
- Leave a value blank/TBD if the native model does not expose it. Never infer wall thickness, material density, steel section, rating, load, cost or specification from a visual label.
- Do not treat a quantity as verified unless its extraction method and unit are clear.

## Calculation sheets

For an engineering calculation, expose the formula, input values, units, assumptions, reference and result. Guard against unit mismatch and circular expressions. A spreadsheet formula is not a validated engineering code check; compare important calculations with independent methods and applicable standards.

## Deliverables

Depending on the task, prepare named parameter cells, component/room/wall/equipment schedules, quantity sheets and references to drawings or model views. Recompute the native model and reopen the file to ensure expressions and links remain intact.
