from __future__ import annotations

from math import dist

from models import Mission, Segment


def build_segments(mission: Mission) -> list[Segment]:
    if len(mission.waypoints) < 2:
        raise ValueError("Need at least two waypoints")
    if mission.speed_mps <= 0:
        raise ValueError("Speed must be positive")

    legs = [dist(mission.waypoints[i], mission.waypoints[i + 1]) for i in range(len(mission.waypoints) - 1)]
    total = sum(legs)
    if total <= 0:
        raise ValueError("Path length must be positive")

    t = mission.departure_time_s
    segments: list[Segment] = []
    for i, leg in enumerate(legs):
        dt = leg / mission.speed_mps
        segments.append(Segment(i, t, t + dt, mission.waypoints[i], mission.waypoints[i + 1]))
        t = t + dt
    return segments
