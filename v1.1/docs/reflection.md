# Reflection and Justification (V1.1)

## Design decisions

V1.1 was designed to satisfy continuous trajectory requirements:

- each mission uses constant speed,
- only departure time is required,
- segment timings are derived from path geometry.

Trajectory timing and conflict solving are split into separate modules for testability.

## Continuous trajectory analysis

For each pair of overlapping segments:

- drone positions are represented as linear functions of time,
- relative distance is minimized analytically over overlap interval,
- conflict exists when minimum distance is below safety threshold.

This avoids discretization errors from coarse simulation steps.

## Conflict explanation output

`analyze_mission` returns exact details:

- involved drones,
- closest approach time,
- midpoint location,
- minimum separation.

## Testing strategy

Tests cover:

- same-time crossing conflict,
- time-shifted crossing with no conflict,
- report integrity for mixed-speed trajectories.

## Edge cases

- invalid or zero speed,
- zero-length paths,
- non-overlapping segment windows,
- mixed multi-segment paths.

## Scalability notes

The continuous segment kernel scales better than naive sampling, but all-pairs checks still grow quadratically. Production scaling would use:

- spatial-temporal partitioning,
- candidate pruning via indexing,
- parallel segment evaluation,
- streaming conflict updates.
