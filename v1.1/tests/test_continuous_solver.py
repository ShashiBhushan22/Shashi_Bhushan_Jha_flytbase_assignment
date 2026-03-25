from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Mission
from solver import analyze_mission, has_conflict


def test_crossing_same_time_conflict() -> None:
    a = Mission("a", [(0.0, 0.0), (100.0, 100.0)], 10.0, 0.0)
    b = Mission("b", [(100.0, 0.0), (0.0, 100.0)], 10.0, 0.0)
    assert has_conflict(a, b, buffer_m=5.0)
    report = analyze_mission(a, [b], buffer_m=5.0)
    assert report.status == "conflict detected"
    assert len(report.conflicts) == 1
    assert report.conflicts[0].minimum_distance_m <= 5.0


def test_crossing_different_time_no_conflict() -> None:
    a = Mission("a", [(0.0, 0.0), (100.0, 100.0)], 10.0, 0.0)
    b = Mission("b", [(100.0, 0.0), (0.0, 100.0)], 10.0, 20.0)
    assert not has_conflict(a, b, buffer_m=5.0)


def test_mixed_speed_case_produces_valid_report() -> None:
    primary = Mission("p", [(0.0, 0.0), (50.0, 60.0), (120.0, 120.0)], 12.0, 0.0)
    intruder = Mission("q", [(130.0, 20.0), (50.0, 70.0), (0.0, 130.0)], 9.0, 2.0)
    report = analyze_mission(primary, [intruder], buffer_m=15.0)
    assert report.status in {"clear", "conflict detected"}
    for conflict in report.conflicts:
        assert conflict.drone_a == "p"
        assert conflict.drone_b == "q"
