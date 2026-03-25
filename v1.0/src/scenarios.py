from __future__ import annotations

from models import Mission, Waypoint


def basic_conflict_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [Waypoint(0, 0), Waypoint(100, 100)], 0.0, 20.0)
    other = Mission("drone_a", [Waypoint(100, 0), Waypoint(0, 100)], 0.0, 20.0)
    return primary, [other]


def conflict_free_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [Waypoint(0, 0), Waypoint(100, 0)], 0.0, 20.0)
    other = Mission("drone_b", [Waypoint(0, 50), Waypoint(100, 50)], 0.0, 20.0)
    return primary, [other]


def timed_waypoint_case() -> tuple[Mission, list[Mission]]:
    primary = Mission(
        "primary",
        [Waypoint(0, 0), Waypoint(50, 50), Waypoint(100, 100)],
        0.0,
        30.0,
        waypoint_times_s=[0.0, 10.0, 30.0],
    )
    other = Mission(
        "drone_c",
        [Waypoint(100, 0), Waypoint(50, 50), Waypoint(0, 100)],
        0.0,
        30.0,
        waypoint_times_s=[0.0, 10.0, 30.0],
    )
    return primary, [other]
