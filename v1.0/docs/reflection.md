# Reflection and Justification (V1.0)

## Design decisions

V1.0 focuses on strategic pre-flight checks before launch:

- mission windows are modeled with start and end time,
- waypoints define intended spatial path,
- conflict checks combine time overlap and minimum separation.

The implementation intentionally remains compact and readable, with a single query interface: `check_mission`.

## Spatial and temporal checks

The solver samples each mission trajectory across segment intervals and compares candidate points only when timestamps are close enough (`temporal_tolerance_s`). A conflict is reported when:

- temporal overlap exists, and
- Euclidean separation is below the safety buffer.

Each conflict record includes:

- conflicting drone id,
- conflict timestamp,
- midpoint location,
- minimum observed distance.

## Visualization approach

A lightweight Plotly utility renders:

- conflict scenario,
- conflict-free scenario,
- timed-waypoint scenario.

Detected conflicts are highlighted with markers and time labels for quick demonstration screenshots/video.

## Testing strategy

Automated tests verify:

- conflict detection for crossing missions,
- no-conflict behavior for spatially separated missions,
- timed waypoint case with overlap and conflict details.

## Edge cases considered

- non-positive mission time windows,
- invalid waypoint timing metadata,
- non-monotonic waypoint timing,
- missions with insufficient waypoints.

## Scaling direction

For larger traffic volumes, this baseline would evolve by:

- switching from sampled checks to exact continuous-time segment math,
- indexing flights spatially and temporally before pair checks,
- running checks in parallel workers,
- ingesting telemetry from streaming pipelines.

## AI usage notes

AI-assisted coding was used for scaffolding tests, structure refinement, and documentation drafting, followed by manual validation of outputs and behavior via tests.
