"""Plotly figure helpers for the Streamlit dashboard."""

from __future__ import annotations

import plotly.graph_objects as go

from .deconfliction import predict_conflicts
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
        color = "#1f77b4" if plan.controlled else "#7f8c8d"
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
        current_position = simulator.position_at(plan.drone_id, timestamp_s)
        paused = plan.controlled and simulator.is_paused(plan.drone_id, timestamp_s)
        marker_color = "#f59e0b" if paused else "#e74c3c" if plan.controlled else "#95a5a6"
        marker_symbol = "diamond" if paused else "circle" if plan.controlled else "square"
        figures.add_trace(
            go.Scatter3d(
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
        )

    for conflict in predicted_conflicts:
        point = conflict.midpoint
        hover = (
            f"{conflict.drone_a} vs {conflict.drone_b}<br>"
            f"severity={conflict.severity}<br>"
            f"closest approach t={conflict.closest_approach_time_s:.1f}s"
        )
        figures.add_trace(
            go.Scatter3d(
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
        )

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
