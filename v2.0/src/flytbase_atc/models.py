"""Core domain models for the deconfliction system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class Waypoint:
    """A waypoint in 2D or 3D space."""

    x: float
    y: float
    z: float | None = None

    def as_vector(self) -> Vector3:
        return (float(self.x), float(self.y), float(self.z if self.z is not None else 0.0))


@dataclass(frozen=True)
class MissionPlan:
    """Mission definition for a drone."""

    drone_id: str
    waypoints: list[Waypoint]
    speed_mps: float
    departure_time_s: float = 0.0
    mission_window_s: tuple[float, float] | None = None
    controlled: bool = True
    telemetry_hz: float = 1.0
    telemetry_dropout_prob: float = 0.0
    telemetry_noise_m: float = 0.0
    telemetry_delay_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.waypoints) < 2:
            raise ValueError(f"MissionPlan {self.drone_id} needs at least two waypoints")
        if self.speed_mps <= 0:
            raise ValueError(f"MissionPlan {self.drone_id} requires positive speed")
        if self.telemetry_hz <= 0:
            raise ValueError(f"MissionPlan {self.drone_id} requires positive telemetry rate")


@dataclass(frozen=True)
class TrajectorySegment:
    """A constant-velocity path segment over a time interval."""

    index: int
    start_time_s: float
    end_time_s: float
    start_point: Vector3
    end_point: Vector3

    @property
    def duration_s(self) -> float:
        return self.end_time_s - self.start_time_s

    def position_at(self, timestamp_s: float) -> Vector3:
        if self.duration_s <= 0:
            return self.start_point
        ratio = (timestamp_s - self.start_time_s) / self.duration_s
        ratio = max(0.0, min(1.0, ratio))
        return tuple(
            self.start_point[i] + ratio * (self.end_point[i] - self.start_point[i])
            for i in range(3)
        )

    @property
    def velocity_vector(self) -> Vector3:
        if self.duration_s <= 0:
            return (0.0, 0.0, 0.0)
        return tuple((self.end_point[i] - self.start_point[i]) / self.duration_s for i in range(3))


@dataclass(frozen=True)
class TrajectoryProfile:
    """The continuous time profile for a mission plan."""

    drone_id: str
    segments: list[TrajectorySegment]
    path_length_m: float
    duration_s: float
    start_time_s: float
    end_time_s: float
    mission_window_s: tuple[float, float] | None = None

    def position_at(self, timestamp_s: float) -> Vector3:
        if timestamp_s <= self.start_time_s:
            return self.segments[0].start_point
        if timestamp_s >= self.end_time_s:
            return self.segments[-1].end_point
        for segment in self.segments:
            if segment.start_time_s <= timestamp_s <= segment.end_time_s:
                return segment.position_at(timestamp_s)
        return self.segments[-1].end_point


@dataclass(frozen=True)
class ConflictEvent:
    """A predicted spatio-temporal conflict between two trajectories."""

    drone_a: str
    drone_b: str
    segment_a_index: int
    segment_b_index: int
    start_time_s: float
    end_time_s: float
    closest_approach_time_s: float
    position_a: Vector3
    position_b: Vector3
    minimum_distance_m: float
    buffer_m: float
    severity: str
    explanation: str

    @property
    def midpoint(self) -> Vector3:
        return tuple((self.position_a[i] + self.position_b[i]) / 2.0 for i in range(3))


@dataclass(frozen=True)
class ConflictReport:
    """Aggregated result from a deconfliction query."""

    status: str
    conflicts: list[ConflictEvent]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FlightDecision:
    """Operator-facing decision for pre-flight review."""

    decision: str
    reason: str
    conflicts: list[ConflictEvent]
    suggested_delays_s: list[float] = field(default_factory=list)
    feasible: bool = True


@dataclass(frozen=True)
class TelemetryConfig:
    """Noise and delivery characteristics for simulated telemetry."""

    rate_hz: float = 1.0
    dropout_prob: float = 0.0
    noise_m: float = 0.0
    delay_s: float = 0.0


@dataclass(frozen=True)
class AlertGroup:
    """A grouped operator alert, usually centered around one or two drones."""

    group_id: str
    drone_ids: tuple[str, ...]
    conflicts: list[ConflictEvent]
    highest_severity: str
    earliest_time_s: float
    actionable: bool
    confidence: float
    suggested_actions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BatchMissionDecision:
    """Decision summary for an incoming mission in a review queue."""

    mission_id: str
    decision: str
    reason: str
    risk_score: float
    conflicts: list[ConflictEvent]
    suggested_delays_s: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class SystemHealthSnapshot:
    """Health and load view used by the operator panel."""

    timestamp_s: float
    drone_count: int
    pair_checks: int
    compute_latency_ms: float
    checks_per_second: float
    status: str
    notes: list[str] = field(default_factory=list)
