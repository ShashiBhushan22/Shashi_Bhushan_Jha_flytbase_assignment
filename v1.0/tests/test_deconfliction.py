from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deconfliction import check_mission
from scenarios import basic_conflict_case, conflict_free_case, timed_waypoint_case


def test_v1_conflict_case() -> None:
    primary, others = basic_conflict_case()
    status, conflicts = check_mission(primary, others, safety_buffer_m=8.0)
    assert status == "conflict detected"
    assert len(conflicts) >= 1
    assert conflicts[0].own_drone == "primary"
    assert conflicts[0].minimum_distance_m <= 8.0


def test_v1_clear_case() -> None:
    primary, others = conflict_free_case()
    status, conflicts = check_mission(primary, others, safety_buffer_m=8.0)
    assert status == "clear"
    assert conflicts == []


def test_v1_timed_waypoints_still_detect_overlap() -> None:
    primary, others = timed_waypoint_case()
    status, conflicts = check_mission(primary, others, safety_buffer_m=12.0)
    assert status == "conflict detected"
    assert len(conflicts) >= 1
