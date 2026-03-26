from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    z: float | None = None

    def as_vector(self) -> tuple[float, float, float]:
        return (self.x, self.y, 0.0 if self.z is None else self.z)


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
    location: tuple[float, float, float]
    minimum_distance_m: float
    reason: str
