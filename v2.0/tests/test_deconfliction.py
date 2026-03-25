from __future__ import annotations

from flytbase_atc.deconfliction import (
    analyze_all_conflicts,
    analyze_conflicts,
    build_system_health_snapshot,
    group_alerts,
    predict_conflicts,
    review_incoming_plans,
    review_mission,
)
from flytbase_atc.geometry import build_trajectory_profile
from flytbase_atc.models import MissionPlan, Waypoint
from flytbase_atc.simulator import AirspaceSimulator


def test_conflict_detected_for_crossing_paths() -> None:
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(100, 100)],
        speed_mps=10.0,
        departure_time_s=0.0,
    )
    intruder = MissionPlan(
        drone_id="intruder",
        waypoints=[Waypoint(100, 0), Waypoint(0, 100)],
        speed_mps=10.0,
        departure_time_s=0.0,
        controlled=False,
    )
    report = analyze_conflicts(primary, [intruder], buffer_m=5.0)
    assert report.status == "conflict detected"
    assert len(report.conflicts) == 1
    assert report.conflicts[0].minimum_distance_m <= 5.0


def test_time_shift_can_clear_conflict() -> None:
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(100, 100)],
        speed_mps=10.0,
        departure_time_s=0.0,
    )
    intruder = MissionPlan(
        drone_id="intruder",
        waypoints=[Waypoint(100, 0), Waypoint(0, 100)],
        speed_mps=10.0,
        departure_time_s=0.0,
        controlled=False,
    )
    decision = review_mission(primary, [intruder], buffer_m=5.0)
    assert decision.decision in {"delay", "reject"}


def test_trajectory_profile_times_are_monotonic() -> None:
    plan = MissionPlan(
        drone_id="demo",
        waypoints=[Waypoint(0, 0), Waypoint(30, 0), Waypoint(30, 40)],
        speed_mps=10.0,
        departure_time_s=5.0,
    )
    profile = build_trajectory_profile(plan)
    assert profile.start_time_s == 5.0
    assert profile.end_time_s > profile.start_time_s
    assert profile.segments[0].start_time_s == 5.0
    assert profile.segments[-1].end_time_s == profile.end_time_s


def test_clear_scenario_reports_no_conflict() -> None:
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(100, 0)],
        speed_mps=10.0,
        departure_time_s=0.0,
    )
    other = MissionPlan(
        drone_id="other",
        waypoints=[Waypoint(0, 20), Waypoint(100, 20)],
        speed_mps=10.0,
        departure_time_s=0.0,
        controlled=False,
    )
    report = analyze_conflicts(primary, [other], buffer_m=5.0)
    assert report.status == "clear"
    assert report.conflicts == []


def test_predict_conflicts_respects_time_horizon() -> None:
    primary = MissionPlan("a", [Waypoint(0, 0), Waypoint(100, 100)], 10.0, departure_time_s=0.0)
    intruder = MissionPlan("b", [Waypoint(100, 0), Waypoint(0, 100)], 10.0, departure_time_s=0.0, controlled=False)

    all_events = analyze_all_conflicts([primary, intruder], buffer_m=5.0)
    near_term = predict_conflicts([primary, intruder], now_s=0.0, lookahead_s=3.0, buffer_m=5.0)

    assert len(all_events) == 1
    assert near_term == []


def test_group_alerts_marks_actionable_conflicts() -> None:
    controlled = MissionPlan("ctrl", [Waypoint(0, 0), Waypoint(100, 100)], 10.0, departure_time_s=0.0)
    unknown = MissionPlan("unk", [Waypoint(100, 0), Waypoint(0, 100)], 10.0, departure_time_s=0.0, controlled=False)
    conflicts = analyze_all_conflicts([controlled, unknown], buffer_m=5.0)

    groups = group_alerts(conflicts, controlled_ids={"ctrl"})

    assert len(groups) == 1
    assert groups[0].actionable is True
    assert groups[0].highest_severity in {"low", "medium", "high"}


def test_group_alerts_collapses_multiple_conflicts_around_one_controlled_drone() -> None:
    controlled = MissionPlan("ctrl", [Waypoint(0, 0), Waypoint(100, 100)], 10.0, departure_time_s=0.0)
    unknown_a = MissionPlan("unk_a", [Waypoint(100, 0), Waypoint(0, 100)], 10.0, departure_time_s=0.0, controlled=False)
    unknown_b = MissionPlan("unk_b", [Waypoint(50, -50), Waypoint(50, 150)], 14.142, departure_time_s=0.0, controlled=False)
    conflicts = analyze_all_conflicts([controlled, unknown_a, unknown_b], buffer_m=5.0)

    groups = group_alerts(conflicts, controlled_ids={"ctrl"})
    actionable_groups = [group for group in groups if group.actionable]

    assert len(actionable_groups) == 1
    assert actionable_groups[0].drone_ids == ("ctrl", "unk_a", "unk_b")
    assert len(actionable_groups[0].conflicts) == 2


def test_review_incoming_plans_returns_ranked_decisions() -> None:
    active = [MissionPlan("active", [Waypoint(0, 0), Waypoint(80, 80)], 8.0, departure_time_s=0.0)]
    incoming = [
        MissionPlan("incoming_risky", [Waypoint(80, 0), Waypoint(0, 80)], 8.0, departure_time_s=0.0),
        MissionPlan("incoming_safe", [Waypoint(0, 120), Waypoint(80, 120)], 8.0, departure_time_s=0.0),
    ]

    decisions = review_incoming_plans(incoming, active, buffer_m=5.0)

    assert len(decisions) == 2
    assert decisions[0].risk_score >= decisions[1].risk_score


def test_health_snapshot_includes_pair_count_and_status() -> None:
    plans = [
        MissionPlan("a", [Waypoint(0, 0), Waypoint(100, 0)], 10.0),
        MissionPlan("b", [Waypoint(0, 5), Waypoint(100, 5)], 10.0, controlled=False),
        MissionPlan("c", [Waypoint(0, 20), Waypoint(100, 20)], 10.0),
    ]
    health, alerts = build_system_health_snapshot(plans, timestamp_s=0.0, lookahead_s=20.0, buffer_m=6.0)

    assert health.drone_count == 3
    assert health.pair_checks == 3
    assert health.status in {"healthy", "degraded"}
    assert isinstance(alerts, list)


def test_simulator_snapshot_honors_telemetry_rate() -> None:
    fast = MissionPlan("fast", [Waypoint(0, 0), Waypoint(100, 0)], 10.0, telemetry_hz=2.0)
    slow = MissionPlan("slow", [Waypoint(0, 10), Waypoint(100, 10)], 10.0, telemetry_hz=0.5)
    sim = AirspaceSimulator([fast, slow])

    first = sim.snapshot(0.0)
    second = sim.snapshot(0.4)
    third = sim.snapshot(0.6)
    late = sim.snapshot(2.1)

    assert len(first) == 2
    assert all(sample.drone_id != "slow" for sample in second)
    assert any(sample.drone_id == "fast" for sample in third)
    assert any(sample.drone_id == "slow" for sample in late)


def test_preview_resume_projects_forward_motion_for_paused_drone() -> None:
    mission = MissionPlan("ctrl", [Waypoint(0, 0), Waypoint(100, 0)], 10.0)
    sim = AirspaceSimulator([mission])
    sim.pause_drone("ctrl", 3.0)

    preview = sim.preview_resume("ctrl", timestamp_s=10.0, horizon_s=3.0, step_s=1.0)

    assert len(preview) == 4
    first_x = preview[0]["ctrl"][0]
    last_x = preview[-1]["ctrl"][0]
    assert last_x > first_x
