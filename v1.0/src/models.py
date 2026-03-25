from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float


@dataclass(frozen=True)
class Mission:
    drone_id: str
    waypoints: list[Waypoint]
    start_time_s: float
    end_time_s: float
    waypoint_times_s: list[float] | None = None


@dataclass(frozen=True)
class Conflict:
    with_drone: str
    own_drone: str
    conflict_time_s: float
    location: tuple[float, float]
    minimum_distance_m: float
    reason: str
