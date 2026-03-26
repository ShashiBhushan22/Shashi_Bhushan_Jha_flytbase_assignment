from __future__ import annotations

from models import Mission, Waypoint


def basic_conflict_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [Waypoint(0, 0, 20), Waypoint(100, 100, 60)], 0.0, 20.0)
    other = Mission("drone_a", [Waypoint(100, 0, 60), Waypoint(0, 100, 20)], 0.0, 20.0)
    return primary, [other]


def conflict_free_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [Waypoint(0, 0, 20), Waypoint(100, 0, 20)], 0.0, 20.0)
    other = Mission("drone_b", [Waypoint(0, 50, 80), Waypoint(100, 50, 80)], 0.0, 20.0)
    return primary, [other]


def time_shifted_crossing_case() -> tuple[Mission, list[Mission]]:
    primary = Mission(
        "primary",
        [Waypoint(0, 0, 30), Waypoint(100, 100, 30)],
        0.0,
        20.0,
        waypoint_times_s=[0.0, 20.0],
    )
    other = Mission(
        "drone_time_shifted",
        [Waypoint(100, 0, 30), Waypoint(0, 100, 30)],
        15.0,
        35.0,
        waypoint_times_s=[15.0, 35.0],
    )
    return primary, [other]


def timed_waypoint_case() -> tuple[Mission, list[Mission]]:
    primary = Mission(
        "primary",
        [Waypoint(0, 0, 20), Waypoint(50, 50, 40), Waypoint(100, 100, 60)],
        0.0,
        30.0,
        waypoint_times_s=[0.0, 10.0, 30.0],
    )
    other = Mission(
        "drone_c",
        [Waypoint(100, 0, 60), Waypoint(50, 50, 40), Waypoint(0, 100, 20)],
        0.0,
        30.0,
        waypoint_times_s=[0.0, 10.0, 30.0],
    )
    return primary, [other]
