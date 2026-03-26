"""Plotly figure helpers for the Streamlit dashboard."""

from __future__ import annotations

import plotly.graph_objects as go

from .deconfliction import analyze_all_conflicts, predict_conflicts
from .models import MissionPlan, TrajectoryProfile
from .simulator import AirspaceSimulator


def path_coordinates(profile: TrajectoryProfile) -> tuple[list[float], list[float], list[float]]:
    xs = [segment.start_point[0] for segment in profile.segments]
    ys = [segment.start_point[1] for segment in profile.segments]
    zs = [segment.start_point[2] for segment in profile.segments]
    xs.append(profile.segments[-1].end_point[0])
    ys.append(profile.segments[-1].end_point[1])
    zs.append(profile.segments[-1].end_point[2])
    return xs, ys, zs


def _plan_color(plan: MissionPlan) -> str:
    return "#1f77b4" if plan.controlled else "#7f8c8d"


def _position_trace(plan: MissionPlan, simulator: AirspaceSimulator, timestamp_s: float) -> go.Scatter3d:
    current_position = simulator.position_at(plan.drone_id, timestamp_s)
    paused = plan.controlled and simulator.is_paused(plan.drone_id, timestamp_s)
    marker_color = "#f59e0b" if paused else "#e74c3c" if plan.controlled else "#95a5a6"
    marker_symbol = "diamond" if paused else "circle" if plan.controlled else "square"
    return go.Scatter3d(
        x=[current_position[0]],
        y=[current_position[1]],
        z=[current_position[2]],
        mode="markers",
        name=f"{plan.drone_id} now",
        marker=dict(size=9, color=marker_color, symbol=marker_symbol),
        hovertext=f"{plan.drone_id} | {'paused' if paused else 'active'}",
        hoverinfo="text",
        showlegend=False,
    )


def _conflict_trace(conflict) -> go.Scatter3d:
    point = conflict.midpoint
    hover = (
        f"{conflict.drone_a} vs {conflict.drone_b}<br>"
        f"severity={conflict.severity}<br>"
        f"closest approach t={conflict.closest_approach_time_s:.1f}s"
    )
    return go.Scatter3d(
        x=[point[0]],
        y=[point[1]],
        z=[point[2]],
        mode="markers",
        marker=dict(size=10, color="#ff4d4f", symbol="x"),
        name="predicted conflict",
        hovertext=hover,
        hoverinfo="text",
        showlegend=False,
    )


def _active_conflicts(conflicts: list, frame_time_s: float, highlight_window_s: float) -> list:
    return [
        conflict
        for conflict in conflicts
        if conflict.start_time_s - highlight_window_s <= frame_time_s <= conflict.end_time_s + highlight_window_s
    ]


def _trail_trace(plan: MissionPlan, simulator: AirspaceSimulator, start_time_s: float, end_time_s: float, step_s: float) -> go.Scatter3d:
    timestamps: list[float] = []
    current = start_time_s
    while current <= end_time_s + 1e-9:
        timestamps.append(round(current, 2))
        current += max(step_s, 0.5)

    if not timestamps:
        timestamps.append(round(end_time_s, 2))

    points = [simulator.position_at(plan.drone_id, timestamp_s) for timestamp_s in timestamps]
    return go.Scatter3d(
        x=[point[0] for point in points],
        y=[point[1] for point in points],
        z=[point[2] for point in points],
        mode="lines",
        line=dict(width=6, color=_plan_color(plan)),
        name=f"{plan.drone_id} history",
        showlegend=False,
    )


def build_airspace_figure(
    plans: list[MissionPlan],
    timestamp_s: float,
    buffer_m: float = 10.0,
    lookahead_s: float = 20.0,
) -> go.Figure:
    simulator = AirspaceSimulator(plans)
    return build_airspace_figure_with_simulator(
        plans,
        simulator=simulator,
        timestamp_s=timestamp_s,
        buffer_m=buffer_m,
        lookahead_s=lookahead_s,
    )


def build_airspace_figure_with_simulator(
    plans: list[MissionPlan],
    simulator: AirspaceSimulator,
    timestamp_s: float,
    buffer_m: float = 10.0,
    lookahead_s: float = 20.0,
) -> go.Figure:
    predicted_conflicts = predict_conflicts(plans, now_s=timestamp_s, lookahead_s=lookahead_s, buffer_m=buffer_m)
    figures = go.Figure()
    for plan in plans:
        profile = simulator.profiles[plan.drone_id]
        xs, ys, zs = path_coordinates(profile)
        color = _plan_color(plan)
        figures.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines+markers",
                name=plan.drone_id,
                line=dict(width=5, color=color),
                marker=dict(size=4),
            )
        )
        figures.add_trace(_position_trace(plan, simulator, timestamp_s))

    for conflict in predicted_conflicts:
        figures.add_trace(_conflict_trace(conflict))

    figures.update_layout(
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Airspace overview at t={timestamp_s:.1f}s | predicted alerts={len(predicted_conflicts)}",
        height=700,
    )
    return figures


def build_replay_animation_figure(
    plans: list[MissionPlan],
    start_time_s: float,
    end_time_s: float,
    buffer_m: float = 10.0,
    lookahead_s: float = 20.0,
    step_s: float = 1.0,
) -> go.Figure:
    simulator = AirspaceSimulator(plans)
    return build_replay_animation_figure_with_simulator(
        plans,
        simulator=simulator,
        start_time_s=start_time_s,
        end_time_s=end_time_s,
        buffer_m=buffer_m,
        lookahead_s=lookahead_s,
        step_s=step_s,
    )


def build_replay_animation_figure_with_simulator(
    plans: list[MissionPlan],
    simulator: AirspaceSimulator,
    start_time_s: float,
    end_time_s: float,
    buffer_m: float = 10.0,
    lookahead_s: float = 20.0,
    step_s: float = 1.0,
) -> go.Figure:
    frame_times: list[float] = []
    current_time = start_time_s
    safe_step_s = max(step_s, 0.25)
    safe_end_time_s = max(start_time_s, end_time_s)
    all_conflicts = analyze_all_conflicts(plans, buffer_m=buffer_m)

    while current_time <= safe_end_time_s + 1e-9:
        frame_times.append(round(current_time, 2))
        current_time += safe_step_s

    if not frame_times:
        frame_times.append(round(start_time_s, 2))

    highlight_window_s = max(0.8, safe_step_s)

    frames: list[go.Frame] = []
    for frame_time in frame_times:
        traces: list[go.BaseTraceType] = []
        for plan in plans:
            profile = simulator.profiles[plan.drone_id]
            xs, ys, zs = path_coordinates(profile)
            traces.append(
                go.Scatter3d(
                    x=xs,
                    y=ys,
                    z=zs,
                    mode="lines+markers",
                    name=plan.drone_id,
                    line=dict(width=5, color=_plan_color(plan)),
                    marker=dict(size=4),
                    opacity=0.35,
                    showlegend=False,
                )
            )
            traces.append(_trail_trace(plan, simulator, start_time_s, frame_time, safe_step_s))
            traces.append(_position_trace(plan, simulator, frame_time))

        for conflict in _active_conflicts(all_conflicts, frame_time, highlight_window_s):
            traces.append(_conflict_trace(conflict))

        frames.append(go.Frame(data=traces, name=f"{frame_time:.1f}s"))

    slider_steps = [
        {
            "label": frame.name,
            "method": "animate",
            "args": [[frame.name], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
        }
        for frame in frames
    ]

    figure = go.Figure(data=frames[0].data if frames else [], frames=frames)
    figure.update_layout(
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        title=(
            f"4D replay window from t={frame_times[0]:.1f}s to t={frame_times[-1]:.1f}s "
            "(solid=history, faint route=planned path, X=active conflict)"
        ),
        height=720,
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [None, {"frame": {"duration": 450, "redraw": True}, "fromcurrent": True}],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}}],
                    },
                ],
            }
        ],
        sliders=[{"currentvalue": {"prefix": "Time: "}, "steps": slider_steps}],
    )
    return figure
