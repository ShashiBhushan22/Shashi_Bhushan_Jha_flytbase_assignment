# Reflection and Justification (V2)

## Design decisions

The system is split into five layers:

1. Domain models for waypoints, mission plans, trajectories, and conflict events.
2. Geometry utilities that convert waypoints into continuous motion over time.
3. A conflict engine that evaluates segment-to-segment separation analytically.
4. A simulator layer for telemetry generation, pause/resume control, and replay windows.
5. An ATC workflow layer (queue review, alert grouping, and health signals) exposed in the dashboard.

This separation keeps the code easier to test and reduces the chance that UI changes will break the conflict logic.

## Spatial and temporal checks

Each mission is converted into line segments with timestamps derived from total path length and constant speed. For overlapping segments, relative position is linear in time and squared distance is quadratic. Solving the quadratic gives exact minimum separation and conflict windows without timeline sampling.

That is the main reason this design is safer than a step-based approximation: it does not miss short conflicts between sample points.

## Real-time workflow support

The V2 implementation adds operator-first behaviors required by the assignment:

- grouped, prioritized simultaneous alerts to reduce noise,
- consolidation of multiple simultaneous conflicts around the same controllable drone,
- actionable flags when at least one controlled drone is involved,
- pre-flight batch review with risk scoring and delay suggestions,
- queue filtering by operator and urgency in the primary dashboard,
- pause/resume controls with paused-duration warnings,
- safe-resume preview showing short-horizon projected motion,
- incident replay for last 10-20 seconds,
- latency/load health indicators with degraded-state notes.

## AI usage

AI tools were used to accelerate architecture iteration, scenario synthesis, test generation, and documentation drafting. Outputs were validated by:

- keeping the core logic small and testable,
- adding deterministic tests for clear and conflicting paths,
- keeping the simulator deterministic by seed,
- separating the math layer from the dashboard so conflict math is independently testable.

## Testing strategy

Automated tests cover:

- crossing trajectories with simultaneous timing,
- horizon-based prediction filters,
- grouped alert actionability,
- multi-alert grouping around a single controlled drone,
- queue review and risk ordering,
- telemetry-rate behavior (0.5-2 Hz),
- paused-drone resume previews,
- trajectory construction and clear/no-conflict paths.

Remaining test gaps include richer unknown-drone behavior, probabilistic confidence calibration, and stress-test automation at 100+ drones.

## Measured performance and limits

I added a repeatable benchmark sweep (`python scripts/benchmark_load.py`) to measure prediction cost as drone count increases. On March 25, 2026 in this workspace, the measured results were:

| Drone count | Avg latency (ms) | Worst latency (ms) | Pair checks | Alert groups | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| 30 | 1.81 | 1.93 | 465 | 3 | healthy |
| 60 | 6.61 | 7.47 | 1830 | 11 | healthy |
| 80 | 12.01 | 13.27 | 3240 | 16 | degraded |
| 100 | 16.95 | 17.54 | 5050 | 23 | degraded |

Latency varies slightly between runs, but the first sampled breaking point remained 80 drones during verification. The dashboard intentionally marks that state as degraded so the ATC gets a visible trust signal before latency becomes operationally uncomfortable.

## Edge cases

Important edge cases handled or identified:

- two drones sharing the same path in opposite directions,
- one drone arriving before the other enters the area,
- exact tangency to the safety buffer,
- stationary or zero-length paths,
- paths in 2D and 3D mixed together,
- telemetry dropout, delayed packets, and stale samples.

## Scaling to 1000+ and beyond

A production deployment would need:

- distributed telemetry ingestion and mission-event streams,
- spatial-temporal indexing (tiles + horizon buckets) to avoid all-pairs checks,
- partitioned conflict workers with bounded-latency SLAs,
- probabilistic tracking for unknown drones and confidence-aware alerts,
- backpressure, retries, and fault-tolerant queueing,
- replay/event storage optimized for 10-20 second forensic windows,
- control-plane observability (latency, dropped packets, stale data, worker lag).

At high scale, the continuous-time conflict kernel remains useful, but it must run in distributed workers fed by streaming data rather than inside a single dashboard process.
