---
name: vehicle-package-design
description: Interview and decompose vehicle design requests into editable body, chassis, wheel, powertrain, cabin, suspension, interface and documentation stages.
tags: [vehicle, car, automotive, chassis, body, wheel, packaging, mechanical, assembly]
aliases: [car design, automobile, SUV, sedan, pickup, minibus, vehicle CAD, automotive body]
---

# Vehicle concept and packaging

## Clarify the intended result

Ask the user:
- vehicle class and intended use (sedan, SUV, pickup, bus, van, off-road, racing, etc.);
- occupants and seating rows;
- body/door/boot or cargo arrangement;
- target length, width, height, wheelbase, track widths and ground clearance, or permission to use named concept parameters;
- wheel/tyre envelope and steering arrangement;
- powertrain type and layout (electric, hybrid, combustion; front/rear/all-wheel drive) where relevant;
- major interfaces (battery, engine, transmission, cooling, suspension, steering, brakes);
- target level: exterior styling concept, interior package, editable assembly, engineering layout or manufacturing drawings.

Do not silently select dimensions or powertrain details. A user may approve editable concept parameters, but the model must label them proposed.

## Decompose the vehicle

Depending on requested scope, organise the model into:
- chassis/frame or skateboard/platform;
- body shell, roof, bonnet/hood, doors and glazing envelopes;
- wheel/tyre assemblies, hubs and axles;
- suspension and steering component envelopes;
- powertrain, battery/fuel tank and cooling package;
- seats, dashboard, interior and luggage/cargo envelope;
- lighting, bumpers and other exterior parts.

Use a stable origin, coordinate system and vehicle datums. Keep major components separate and consistently marked. Establish wheelbase, track width, axle centres and ground plane before making body components.

## Native build sequence

1. Establish global coordinate system and approved packaging envelope.
2. Create chassis rails/crossmembers or a platform envelope as individual editable members.
3. Place wheel and tyre envelopes using correctly oriented cylindrical native geometry where suitable.
4. Add suspension, powertrain and cabin/body envelopes in dependency order.
5. Inspect component clearances, ground clearance, axle alignment and overall bounds.
6. Build subassemblies or joints only where the native installed toolset supports them.
7. Produce component, envelope and dimension schedules and relevant drawing views.

A box is only an envelope; a cylinder is only a wheel/shaft envelope. Do not represent primitive placeholders as detailed suspension, functional steering, brakes, crash structures or production body panels.

## Documentation

A package schedule can include component mark, object ID, subsystem, modelled dimensions, location/placement, bounding-box dimensions, interface notes and status. Make sure every measured value comes from the native model and every proposal is identified.

## Boundaries

A visual/packaging model does not prove roadworthiness, crashworthiness, restraint adequacy, braking/steering performance, fatigue life, electrical safety, battery thermal safety or regulatory compliance. These require discipline-specific inputs, simulation, tests and qualified reviews.
