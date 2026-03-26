from __future__ import annotations

from math import dist

from models import Mission, Segment, Vector3, WaypointLike


def normalize_waypoint(point: WaypointLike) -> Vector3:
    if len(point) == 2:
        return (point[0], point[1], 0.0)
    return (point[0], point[1], point[2])


def build_segments(mission: Mission) -> list[Segment]:
    if len(mission.waypoints) < 2:
        raise ValueError("Need at least two waypoints")
    if mission.speed_mps <= 0:
        raise ValueError("Speed must be positive")

    normalized_waypoints = [normalize_waypoint(point) for point in mission.waypoints]
    legs = [dist(normalized_waypoints[i], normalized_waypoints[i + 1]) for i in range(len(normalized_waypoints) - 1)]
    total = sum(legs)
    if total <= 0:
        raise ValueError("Path length must be positive")

    t = mission.departure_time_s
    segments: list[Segment] = []
    for i, leg in enumerate(legs):
        dt = leg / mission.speed_mps
        segments.append(Segment(i, t, t + dt, normalized_waypoints[i], normalized_waypoints[i + 1]))
        t = t + dt
    return segments
