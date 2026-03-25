"""Performance sweep helpers for assignment measurements."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .deconfliction import build_system_health_snapshot
from .scenarios import build_dense_airspace_scenario


@dataclass(frozen=True)
class PerformanceMeasurement:
    """A single telemetry/conflict-prediction benchmark result."""

    drone_count: int
    average_latency_ms: float
    worst_latency_ms: float
    pair_checks: int
    alert_count: int
    health_status: str


def benchmark_prediction_load(
    drone_counts: list[int],
    repeats: int = 3,
    lookahead_s: float = 20.0,
    buffer_m: float = 10.0,
    timestamp_s: float = 10.0,
    seed: int = 7,
) -> list[PerformanceMeasurement]:
    """Measure conflict-prediction cost as airspace density grows."""

    measurements: list[PerformanceMeasurement] = []
    for drone_count in drone_counts:
        latencies: list[float] = []
        pair_checks = 0
        alert_count = 0
        status = "healthy"

        for offset in range(max(1, repeats)):
            primary, others = build_dense_airspace_scenario(drone_count, seed=seed + offset)
            plans = [primary, *others]
            health, alerts = build_system_health_snapshot(
                plans,
                timestamp_s=timestamp_s,
                lookahead_s=lookahead_s,
                buffer_m=buffer_m,
            )
            latencies.append(health.compute_latency_ms)
            pair_checks = health.pair_checks
            alert_count = max(alert_count, len(alerts))
            if health.status == "degraded":
                status = "degraded"

        measurements.append(
            PerformanceMeasurement(
                drone_count=drone_count,
                average_latency_ms=round(mean(latencies), 2),
                worst_latency_ms=round(max(latencies), 2),
                pair_checks=pair_checks,
                alert_count=alert_count,
                health_status=status,
            )
        )

    return measurements


def find_breaking_point(measurements: list[PerformanceMeasurement]) -> int | None:
    """Return the first drone count where the system reports a degraded state."""

    for measurement in measurements:
        if measurement.health_status == "degraded":
            return measurement.drone_count
    return None
