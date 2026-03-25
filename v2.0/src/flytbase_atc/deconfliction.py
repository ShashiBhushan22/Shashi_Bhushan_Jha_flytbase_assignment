"""Continuous conflict analysis and pre-flight review logic."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from .geometry import build_trajectory_profile, profile_is_within_window, segment_conflict_window
from .models import (
    AlertGroup,
    BatchMissionDecision,
    ConflictEvent,
    ConflictReport,
    FlightDecision,
    MissionPlan,
    SystemHealthSnapshot,
    TrajectoryProfile,
)


def _severity(distance_m: float, buffer_m: float, conflict_duration_s: float) -> str:
    ratio = distance_m / max(buffer_m, 1e-9)
    if ratio <= 0.35 or conflict_duration_s >= 20.0:
        return "high"
    if ratio <= 0.75 or conflict_duration_s >= 8.0:
        return "medium"
    return "low"


def _make_event(profile_a: TrajectoryProfile, profile_b: TrajectoryProfile, window, buffer_m: float) -> ConflictEvent:
    conflict_duration = max(0.0, window.end_time_s - window.start_time_s)
    severity = _severity(window.minimum_distance_m, buffer_m, conflict_duration)
    explanation = (
        f"{profile_a.drone_id} and {profile_b.drone_id} come within {window.minimum_distance_m:.2f} m "
        f"between t={window.start_time_s:.2f}s and t={window.end_time_s:.2f}s."
    )
    return ConflictEvent(
        drone_a=profile_a.drone_id,
        drone_b=profile_b.drone_id,
        segment_a_index=window.segment_a_index,
        segment_b_index=window.segment_b_index,
        start_time_s=window.start_time_s,
        end_time_s=window.end_time_s,
        closest_approach_time_s=window.closest_approach_time_s,
        position_a=window.point_a,
        position_b=window.point_b,
        minimum_distance_m=window.minimum_distance_m,
        buffer_m=buffer_m,
        severity=severity,
        explanation=explanation,
    )


def analyze_conflicts(primary: MissionPlan, others: list[MissionPlan], buffer_m: float = 10.0) -> ConflictReport:
    """Analyze the primary mission against all other missions using continuous time math."""

    primary_profile = build_trajectory_profile(primary)
    conflicts: list[ConflictEvent] = []
    warnings: list[str] = []

    if not profile_is_within_window(primary_profile):
        warnings.append(
            f"Primary mission ends at t={primary_profile.end_time_s:.2f}s which exceeds its mission window."
        )

    for other in others:
        other_profile = build_trajectory_profile(other)
        for segment_a in primary_profile.segments:
            for segment_b in other_profile.segments:
                window = segment_conflict_window(segment_a, segment_b, buffer_m)
                if window is None:
                    continue
                conflicts.append(_make_event(primary_profile, other_profile, window, buffer_m))

    conflicts.sort(key=lambda item: (item.start_time_s, item.minimum_distance_m, item.drone_b))
    status = "clear" if not conflicts else "conflict detected"
    return ConflictReport(status=status, conflicts=conflicts, warnings=warnings)


def analyze_all_conflicts(plans: list[MissionPlan], buffer_m: float = 10.0) -> list[ConflictEvent]:
    """Analyze all pairwise conflicts across a mixed airspace."""

    conflicts: list[ConflictEvent] = []
    profiles = {plan.drone_id: build_trajectory_profile(plan) for plan in plans}
    plan_by_id = {plan.drone_id: plan for plan in plans}
    drone_ids = list(profiles)

    for left_index in range(len(drone_ids)):
        for right_index in range(left_index + 1, len(drone_ids)):
            left_id = drone_ids[left_index]
            right_id = drone_ids[right_index]
            left_profile = profiles[left_id]
            right_profile = profiles[right_id]
            for segment_a in left_profile.segments:
                for segment_b in right_profile.segments:
                    window = segment_conflict_window(segment_a, segment_b, buffer_m)
                    if window is None:
                        continue
                    conflicts.append(_make_event(left_profile, right_profile, window, buffer_m))

    conflicts.sort(key=lambda item: (item.start_time_s, item.minimum_distance_m, item.drone_a, item.drone_b))

    filtered_conflicts: list[ConflictEvent] = []
    for conflict in conflicts:
        left_plan = plan_by_id[conflict.drone_a]
        right_plan = plan_by_id[conflict.drone_b]
        if left_plan.mission_window_s is not None:
            start, end = left_plan.mission_window_s
            if conflict.end_time_s < start or conflict.start_time_s > end:
                continue
        if right_plan.mission_window_s is not None:
            start, end = right_plan.mission_window_s
            if conflict.end_time_s < start or conflict.start_time_s > end:
                continue
        filtered_conflicts.append(conflict)

    return filtered_conflicts


def predict_conflicts(plans: list[MissionPlan], now_s: float, lookahead_s: float, buffer_m: float = 10.0) -> list[ConflictEvent]:
    """Return conflicts predicted in a forward-looking horizon."""

    horizon_end = now_s + max(0.0, lookahead_s)
    events = analyze_all_conflicts(plans, buffer_m=buffer_m)
    return [event for event in events if event.end_time_s >= now_s and event.start_time_s <= horizon_end]


def _alert_group_key(conflict: ConflictEvent, controlled_ids: set[str], time_bucket_s: float) -> tuple[str, ...]:
    participants = tuple(sorted((conflict.drone_a, conflict.drone_b)))
    controlled = tuple(drone_id for drone_id in participants if drone_id in controlled_ids)
    bucket_index = int(conflict.start_time_s // max(time_bucket_s, 1.0))
    if len(controlled) == 1:
        return ("controlled", controlled[0], str(bucket_index))
    return ("pair", *participants, str(bucket_index))


def group_alerts(
    conflicts: list[ConflictEvent],
    controlled_ids: set[str],
    time_bucket_s: float = 10.0,
) -> list[AlertGroup]:
    """Group multiple simultaneous alerts into a smaller operator-focused list."""

    grouped: dict[tuple[str, ...], list[ConflictEvent]] = defaultdict(list)
    for conflict in conflicts:
        key = _alert_group_key(conflict, controlled_ids=controlled_ids, time_bucket_s=time_bucket_s)
        grouped[key].append(conflict)

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    alert_groups: list[AlertGroup] = []

    for group_key, group_conflicts in grouped.items():
        group_conflicts.sort(key=lambda item: item.start_time_s)
        highest = max(group_conflicts, key=lambda item: severity_rank.get(item.severity, 0)).severity
        earliest = group_conflicts[0].start_time_s
        drone_ids = sorted(
            {drone_id for conflict in group_conflicts for drone_id in (conflict.drone_a, conflict.drone_b)},
            key=lambda drone_id: (drone_id not in controlled_ids, drone_id),
        )
        actionable = any(drone_id in controlled_ids for drone_id in drone_ids)
        confidence = 0.5
        confidence += 0.2 if highest == "high" else 0.1 if highest == "medium" else 0.0
        confidence += 0.2 if len(group_conflicts) >= 2 else 0.0
        confidence = min(0.99, confidence)

        suggested_actions: list[str] = []
        if actionable:
            controlled_involved = [drone_id for drone_id in drone_ids if drone_id in controlled_ids]
            uncontrolled_involved = [drone_id for drone_id in drone_ids if drone_id not in controlled_ids]
            suggested_actions.append(f"Pause one of: {', '.join(controlled_involved)}")
            if uncontrolled_involved:
                suggested_actions.append(
                    f"Re-check {', '.join(controlled_involved)} against {', '.join(uncontrolled_involved)} before resume"
                )
            suggested_actions.append("Delay newly submitted plans that intersect this window")
        else:
            suggested_actions.append("Monitor only: both drones are currently uncontrolled")

        alert_groups.append(
            AlertGroup(
                group_id=f"{'_'.join(drone_ids)}_{group_key[-1]}_{int(earliest)}",
                drone_ids=tuple(drone_ids),
                conflicts=group_conflicts,
                highest_severity=highest,
                earliest_time_s=earliest,
                actionable=actionable,
                confidence=confidence,
                suggested_actions=suggested_actions,
            )
        )

    alert_groups.sort(
        key=lambda group: (
            -severity_rank.get(group.highest_severity, 0),
            not group.actionable,
            group.earliest_time_s,
        )
    )
    return alert_groups


def review_incoming_plans(
    incoming: list[MissionPlan],
    flying_or_approved: list[MissionPlan],
    buffer_m: float = 10.0,
) -> list[BatchMissionDecision]:
    """Review a queue of incoming plans and return sorted decisions by risk."""

    decisions: list[BatchMissionDecision] = []
    for mission in incoming:
        decision = review_mission(mission, flying_or_approved, buffer_m=buffer_m)
        risk_score = 0.0
        if decision.conflicts:
            for conflict in decision.conflicts:
                severity_weight = {"high": 1.0, "medium": 0.6, "low": 0.3}.get(conflict.severity, 0.2)
                risk_score += severity_weight * (1.0 + max(0.0, buffer_m - conflict.minimum_distance_m) / max(buffer_m, 1e-9))

        decisions.append(
            BatchMissionDecision(
                mission_id=mission.drone_id,
                decision=decision.decision,
                reason=decision.reason,
                risk_score=round(risk_score, 3),
                conflicts=decision.conflicts,
                suggested_delays_s=decision.suggested_delays_s,
            )
        )

    decisions.sort(key=lambda item: (-item.risk_score, item.mission_id))
    return decisions


def build_system_health_snapshot(
    plans: list[MissionPlan],
    timestamp_s: float,
    lookahead_s: float,
    buffer_m: float = 10.0,
) -> tuple[SystemHealthSnapshot, list[AlertGroup]]:
    """Compute operator health metrics and grouped alerts for the current horizon."""

    start = perf_counter()
    predicted = predict_conflicts(plans, now_s=timestamp_s, lookahead_s=lookahead_s, buffer_m=buffer_m)
    controlled_ids = {plan.drone_id for plan in plans if plan.controlled}
    alerts = group_alerts(predicted, controlled_ids=controlled_ids)
    elapsed_ms = (perf_counter() - start) * 1000.0

    drone_count = len(plans)
    pair_checks = drone_count * max(0, drone_count - 1) // 2
    checks_per_second = 0.0 if elapsed_ms <= 1e-9 else pair_checks / (elapsed_ms / 1000.0)

    status = "healthy"
    notes: list[str] = []
    if elapsed_ms > 400.0:
        status = "degraded"
        notes.append("Conflict prediction latency above 400 ms")
    if drone_count >= 80:
        status = "degraded"
        notes.append("High drone count may reduce UI responsiveness")
    if any(alert.highest_severity == "high" for alert in alerts):
        notes.append("High-severity alerts active")

    snapshot = SystemHealthSnapshot(
        timestamp_s=timestamp_s,
        drone_count=drone_count,
        pair_checks=pair_checks,
        compute_latency_ms=round(elapsed_ms, 2),
        checks_per_second=round(checks_per_second, 2),
        status=status,
        notes=notes,
    )
    return snapshot, alerts


def _search_delay_s(primary: MissionPlan, others: list[MissionPlan], buffer_m: float, delay_s: float) -> bool:
    shifted = MissionPlan(
        drone_id=primary.drone_id,
        waypoints=primary.waypoints,
        speed_mps=primary.speed_mps,
        departure_time_s=primary.departure_time_s + delay_s,
        mission_window_s=primary.mission_window_s,
        controlled=primary.controlled,
        telemetry_hz=primary.telemetry_hz,
        telemetry_dropout_prob=primary.telemetry_dropout_prob,
        telemetry_noise_m=primary.telemetry_noise_m,
        telemetry_delay_s=primary.telemetry_delay_s,
        metadata=primary.metadata,
    )
    return analyze_conflicts(shifted, others, buffer_m=buffer_m).status == "clear"


def suggest_delays(primary: MissionPlan, others: list[MissionPlan], buffer_m: float = 10.0) -> list[float]:
    """Return a small list of delay values that make the mission conflict-free."""

    suggestions: list[float] = []
    for delay_s in range(0, 121, 5):
        if _search_delay_s(primary, others, buffer_m, float(delay_s)):
            suggestions.append(float(delay_s))
        if len(suggestions) == 3:
            break
    return suggestions


def review_mission(primary: MissionPlan, others: list[MissionPlan], buffer_m: float = 10.0) -> FlightDecision:
    """Operator-facing decision for a flight plan."""

    report = analyze_conflicts(primary, others, buffer_m=buffer_m)
    if report.status == "clear":
        return FlightDecision(
            decision="approve",
            reason="No predicted conflicts within the safety buffer.",
            conflicts=report.conflicts,
            feasible=True,
        )

    delay_options = suggest_delays(primary, others, buffer_m=buffer_m)
    if delay_options:
        return FlightDecision(
            decision="delay",
            reason="Conflicts were detected, but a later launch time appears safe.",
            conflicts=report.conflicts,
            suggested_delays_s=delay_options,
            feasible=True,
        )

    return FlightDecision(
        decision="reject",
        reason="The mission conflicts with one or more active trajectories and no safe delay was found.",
        conflicts=report.conflicts,
        feasible=False,
    )
