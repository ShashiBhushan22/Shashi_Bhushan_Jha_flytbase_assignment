from __future__ import annotations

from dataclasses import dataclass, field


WaypointLike = tuple[float, float] | tuple[float, float, float]
Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class Mission:
    drone_id: str
    waypoints: list[WaypointLike]
    speed_mps: float
    departure_time_s: float
    mission_window_s: tuple[float, float] | None = None


@dataclass(frozen=True)
class Segment:
    index: int
    t0: float
    t1: float
    p0: Vector3
    p1: Vector3


@dataclass(frozen=True)
class ConflictDetail:
    drone_a: str
    drone_b: str
    time_s: float
    location: Vector3
    minimum_distance_m: float
    reason: str


@dataclass(frozen=True)
class ConflictReport:
    status: str
    conflicts: list[ConflictDetail]
    warnings: list[str] = field(default_factory=list)
