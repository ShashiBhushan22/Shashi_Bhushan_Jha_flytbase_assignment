from __future__ import annotations

from dataclasses import dataclass


Vec2 = tuple[float, float]


@dataclass(frozen=True)
class Mission:
    drone_id: str
    waypoints: list[Vec2]
    speed_mps: float
    departure_time_s: float


@dataclass(frozen=True)
class Segment:
    index: int
    t0: float
    t1: float
    p0: Vec2
    p1: Vec2


@dataclass(frozen=True)
class ConflictDetail:
    drone_a: str
    drone_b: str
    time_s: float
    location: Vec2
    minimum_distance_m: float
    reason: str


@dataclass(frozen=True)
class ConflictReport:
    status: str
    conflicts: list[ConflictDetail]
