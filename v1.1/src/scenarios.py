from __future__ import annotations

from models import Mission


def crossing_conflict_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [(0.0, 0.0), (100.0, 100.0)], 10.0, 0.0)
    intruder = Mission("intruder", [(100.0, 0.0), (0.0, 100.0)], 10.0, 0.0)
    return primary, [intruder]


def crossing_no_conflict_time_shift_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [(0.0, 0.0), (100.0, 100.0)], 10.0, 0.0)
    intruder = Mission("intruder", [(100.0, 0.0), (0.0, 100.0)], 10.0, 20.0)
    return primary, [intruder]


def mixed_speed_case() -> tuple[Mission, list[Mission]]:
    primary = Mission("primary", [(0.0, 0.0), (50.0, 60.0), (120.0, 120.0)], 12.0, 0.0)
    intruder = Mission("intruder", [(130.0, 20.0), (50.0, 70.0), (0.0, 130.0)], 9.0, 2.0)
    return primary, [intruder]
