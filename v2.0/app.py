from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from flytbase_atc.dashboard import build_airspace_figure_with_simulator
from flytbase_atc.deconfliction import (
    analyze_conflicts,
    build_system_health_snapshot,
    review_incoming_plans,
    review_mission,
)
from flytbase_atc.models import MissionPlan, Waypoint
from flytbase_atc.performance import benchmark_prediction_load, find_breaking_point
from flytbase_atc.scenarios import build_conflict_free_scenario, build_conflict_scenario, build_dense_airspace_scenario
from flytbase_atc.simulator import AirspaceSimulator


st.set_page_config(page_title="FlytBase ATC Deconfliction", layout="wide")

st.title("FlytBase ATC Dashboard")
st.caption("Pre-flight review, in-air conflict prediction, pause/resume control, and incident replay.")

scenario_name = st.sidebar.selectbox(
    "Scenario",
    ["Conflict scenario", "Conflict-free scenario", "Dense airspace"],
)
buffer_m = st.sidebar.slider("Safety buffer (m)", 2.0, 30.0, 10.0, 0.5)
timestamp_s = st.sidebar.slider("Dashboard time (s)", 0.0, 120.0, 10.0, 0.5)
dense_count = st.sidebar.slider("Dense airspace drone count", 5, 60, 30, 1)
lookahead_s = st.sidebar.slider("Prediction lookahead (s)", 5.0, 60.0, 20.0, 1.0)
paused_warning_s = st.sidebar.slider("Paused warning threshold (s)", 5.0, 60.0, 20.0, 1.0)
replay_window_s = st.sidebar.slider("Replay window (s)", 10.0, 20.0, 15.0, 1.0)


@st.cache_data(show_spinner=False)
def cached_performance_sweep(
    drone_counts: tuple[int, ...],
    repeats: int,
    lookahead: float,
    buffer: float,
) -> tuple[list[dict[str, object]], int | None]:
    measurements = benchmark_prediction_load(
        list(drone_counts),
        repeats=repeats,
        lookahead_s=lookahead,
        buffer_m=buffer,
    )
    rows = [
        {
            "drone_count": item.drone_count,
            "avg_latency_ms": item.average_latency_ms,
            "worst_latency_ms": item.worst_latency_ms,
            "pair_checks": item.pair_checks,
            "alert_count": item.alert_count,
            "status": item.health_status,
        }
        for item in measurements
    ]
    return rows, find_breaking_point(measurements)


def load_scenario(name: str, count: int) -> tuple[MissionPlan, list[MissionPlan]]:
    if name == "Conflict-free scenario":
        return build_conflict_free_scenario()
    if name == "Dense airspace":
        return build_dense_airspace_scenario(count)
    return build_conflict_scenario()


def incoming_plan_queue() -> list[MissionPlan]:
    return [
        MissionPlan(
            drone_id="incoming_fast",
            waypoints=[Waypoint(-20, 20), Waypoint(120, 80), Waypoint(220, 60)],
            speed_mps=18.0,
            departure_time_s=5.0,
            mission_window_s=(0.0, 45.0),
            controlled=True,
            metadata={"operator": "Ops Alpha", "urgency": "high"},
        ),
        MissionPlan(
            drone_id="incoming_delayed",
            waypoints=[Waypoint(30, -30), Waypoint(150, 40), Waypoint(210, 90)],
            speed_mps=12.0,
            departure_time_s=12.0,
            mission_window_s=(10.0, 70.0),
            controlled=True,
            metadata={"operator": "Ops Bravo", "urgency": "medium"},
        ),
        MissionPlan(
            drone_id="incoming_low_risk",
            waypoints=[Waypoint(-40, -80), Waypoint(10, -90), Waypoint(220, -70)],
            speed_mps=9.0,
            departure_time_s=0.0,
            mission_window_s=(0.0, 90.0),
            controlled=True,
            metadata={"operator": "Ops Alpha", "urgency": "low"},
        ),
    ]


scenario_key = f"{scenario_name}:{dense_count}"
if st.session_state.get("scenario_key") != scenario_key:
    primary, others = load_scenario(scenario_name, dense_count)
    plans = [primary, *others]
    st.session_state["scenario_key"] = scenario_key
    st.session_state["plans"] = plans
    st.session_state["simulator"] = AirspaceSimulator(plans)

plans = st.session_state["plans"]
simulator: AirspaceSimulator = st.session_state["simulator"]
primary = plans[0]
others = plans[1:]
incoming_queue = incoming_plan_queue()
queue_metadata_by_id = {mission.drone_id: mission.metadata for mission in incoming_queue}

figure = build_airspace_figure_with_simulator(
    plans,
    simulator=simulator,
    timestamp_s=timestamp_s,
    buffer_m=buffer_m,
    lookahead_s=lookahead_s,
)
report = analyze_conflicts(primary, others, buffer_m=buffer_m)
decision = review_mission(primary, others, buffer_m=buffer_m)
health, alerts = build_system_health_snapshot(plans, timestamp_s=timestamp_s, lookahead_s=lookahead_s, buffer_m=buffer_m)
packets = simulator.snapshot(timestamp_s)
stale_packets = sum(1 for packet in packets if packet.stale)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Mission status", report.status)
col2.metric("Conflicts", len(report.conflicts))
col3.metric("Decision", decision.decision)
col4.metric("Drones", len(plans))
col5.metric("System health", health.status)

st.plotly_chart(figure, width="stretch")

left, right = st.columns([1.2, 1])
with left:
    st.subheader("Prioritized in-air alerts")
    if alerts:
        for group in alerts:
            st.write(
                f"- [{group.highest_severity}] {', '.join(group.drone_ids)} | "
                f"t={group.earliest_time_s:.1f}s | actionable={group.actionable} | confidence={group.confidence:.2f}"
            )
            st.write("  Actions: " + "; ".join(group.suggested_actions))
    else:
        st.success("No predicted conflicts in the selected lookahead window.")

    st.subheader("Pre-flight queue review")
    queue_decisions = review_incoming_plans(incoming_queue, plans, buffer_m=buffer_m)
    filter_mode = st.selectbox("Decision filter", ["all", "approve", "delay", "reject"])
    operators = sorted({str(metadata.get("operator", "Unknown")) for metadata in queue_metadata_by_id.values()})
    urgencies = ["high", "medium", "low"]
    operator_filter = st.selectbox("Operator filter", ["all", *operators])
    urgency_filter = st.selectbox("Urgency filter", ["all", *urgencies])
    for item in queue_decisions:
        metadata = queue_metadata_by_id[item.mission_id]
        operator = str(metadata.get("operator", "Unknown"))
        urgency = str(metadata.get("urgency", "unknown"))
        if filter_mode != "all" and item.decision != filter_mode:
            continue
        if operator_filter != "all" and operator != operator_filter:
            continue
        if urgency_filter != "all" and urgency != urgency_filter:
            continue
        st.write(
            f"- {item.mission_id}: {item.decision.upper()} | operator={operator} | urgency={urgency} | "
            f"risk={item.risk_score:.2f} | conflicts={len(item.conflicts)}"
        )
        st.write(f"  Reason: {item.reason}")
        if item.suggested_delays_s:
            st.write(f"  Delay options (s): {item.suggested_delays_s}")

with right:
    st.subheader("System health")
    st.write(f"Latency: {health.compute_latency_ms:.2f} ms")
    st.write(f"Pair checks: {health.pair_checks}")
    st.write(f"Checks/sec: {health.checks_per_second:.2f}")
    st.write(f"Telemetry packets emitted: {len(packets)} (stale={stale_packets})")
    for note in health.notes:
        st.write(f"- {note}")

    st.subheader("Paused drones")
    controlled_ids = simulator.controlled_drone_ids
    for drone_id in controlled_ids:
        paused = simulator.is_paused(drone_id, timestamp_s)
        label = "Resume" if paused else "Pause"
        key = f"pause-toggle-{drone_id}"
        if st.button(f"{label} {drone_id}", key=key):
            if paused:
                simulator.resume_drone(drone_id, timestamp_s)
            else:
                simulator.pause_drone(drone_id, timestamp_s)

    paused_rows = simulator.paused_status(timestamp_s, warning_after_s=paused_warning_s)
    st.dataframe(paused_rows, width="stretch")

    paused_ids: list[str] = [
        cast(str, row["drone_id"])
        for row in paused_rows
        if cast(bool, row["paused"])
    ]
    if paused_ids:
        st.info(f"Resume-review priority: {paused_rows[0]['drone_id']} has the highest paused-time risk.")
        st.subheader("Safe resume preview")
        selected = cast(str, st.selectbox("Paused drone", paused_ids))
        preview = simulator.preview_resume(selected, timestamp_s=timestamp_s, horizon_s=lookahead_s, step_s=1.0)
        st.dataframe(preview, width="stretch")

st.subheader("Incident replay")
if alerts:
    selected_alert = st.selectbox("Replay alert group", [group.group_id for group in alerts])
    chosen_group = next(group for group in alerts if group.group_id == selected_alert)
    replay_center_s = max(
        timestamp_s,
        min(conflict.closest_approach_time_s for conflict in chosen_group.conflicts),
    )
    st.caption(f"Replay centered at t={replay_center_s:.1f}s to capture the lead-up to the selected conflict.")
    replay = simulator.replay_window(
        drone_ids=list(chosen_group.drone_ids),
        center_time_s=replay_center_s,
        window_s=replay_window_s,
        step_s=1.0,
    )
    st.dataframe(replay, width="stretch")
else:
    st.write("No active alert to replay at this timestamp.")

with st.expander("Performance sweep and system limits"):
    benchmark_rows, breaking_point = cached_performance_sweep(
        (30, 60, 80, 100),
        repeats=3,
        lookahead=lookahead_s,
        buffer=buffer_m,
    )
    st.dataframe(benchmark_rows, width="stretch")
    if breaking_point is None:
        st.success("No degraded state detected in the sampled sweep.")
    else:
        st.warning(f"First sampled degraded point: {breaking_point} drones.")
