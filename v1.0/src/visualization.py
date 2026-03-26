from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from deconfliction import _sample_path, check_mission
from models import Mission
from scenarios import basic_conflict_case, conflict_free_case, time_shifted_crossing_case, timed_waypoint_case


def _plot_mission_2d(fig: go.Figure, mission: Mission, label: str, color: str) -> None:
    xs = [w.x for w in mission.waypoints]
    ys = [w.y for w in mission.waypoints]
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name=label,
            line={"color": color, "width": 3},
            marker={"size": 8},
        )
    )


def _plot_mission_3d(fig: go.Figure, mission: Mission, label: str, color: str, opacity: float = 1.0) -> None:
    xs = [w.as_vector()[0] for w in mission.waypoints]
    ys = [w.as_vector()[1] for w in mission.waypoints]
    zs = [w.as_vector()[2] for w in mission.waypoints]
    fig.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="lines+markers",
            name=label,
            line={"color": color, "width": 5},
            marker={"size": 4},
            opacity=opacity,
        )
    )


def _current_sample(samples: list[tuple[float, float, float, float]], time_s: float) -> tuple[float, float, float, float]:
    visible = [sample for sample in samples if sample[3] <= time_s]
    return visible[-1] if visible else samples[0]


def _active_conflicts(conflicts, frame_time: float, highlight_window_s: float) -> list:
    return [
        conflict
        for conflict in conflicts
        if abs(conflict.conflict_time_s - frame_time) <= highlight_window_s
    ]


def _render_2d_case(title: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    status, conflicts = check_mission(primary, others, safety_buffer_m=10.0)

    fig = go.Figure()
    _plot_mission_2d(fig, primary, f"{primary.drone_id} (primary)", "#005f73")
    palette = ["#ae2012", "#9b2226", "#6a4c93", "#2a9d8f"]

    for idx, other in enumerate(others):
        _plot_mission_2d(fig, other, other.drone_id, palette[idx % len(palette)])

    for conflict in conflicts:
        fig.add_trace(
            go.Scatter(
                x=[conflict.location[0]],
                y=[conflict.location[1]],
                mode="markers+text",
                marker={"symbol": "x", "size": 12, "color": "#ff006e"},
                text=[f"t={conflict.conflict_time_s:.1f}s"],
                textposition="top right",
                name="conflict",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"{title} | status={status}",
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        template="plotly_white",
        width=950,
        height=620,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_dir / f"{title.lower().replace(' ', '_')}.html", include_plotlyjs="cdn")


def _render_3d_case(title: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    status, conflicts = check_mission(primary, others, safety_buffer_m=10.0)
    fig = go.Figure()
    _plot_mission_3d(fig, primary, f"{primary.drone_id} (primary)", "#005f73")
    palette = ["#ae2012", "#9b2226", "#6a4c93", "#2a9d8f"]

    for idx, other in enumerate(others):
        _plot_mission_3d(fig, other, other.drone_id, palette[idx % len(palette)])

    for conflict in conflicts:
        fig.add_trace(
            go.Scatter3d(
                x=[conflict.location[0]],
                y=[conflict.location[1]],
                z=[conflict.location[2]],
                mode="markers+text",
                marker={"symbol": "x", "size": 7, "color": "#ff006e"},
                text=[f"t={conflict.conflict_time_s:.1f}s"],
                textposition="top center",
                name="conflict",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"{title} | 3D airspace view | status={status}",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)", aspectmode="data"),
        template="plotly_white",
        width=980,
        height=680,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_dir / f"{title.lower().replace(' ', '_')}_3d.html", include_plotlyjs="cdn")


def _render_4d_case(title: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    missions = [primary, *others]
    palette = {
        primary.drone_id: "#005f73",
        **{mission.drone_id: color for mission, color in zip(others, ["#ae2012", "#9b2226", "#6a4c93", "#2a9d8f"])},
    }
    sample_cache = {mission.drone_id: _sample_path(mission, samples_per_leg=24) for mission in missions}
    status, conflicts = check_mission(primary, others, safety_buffer_m=10.0)

    max_time = max(samples[-1][3] for samples in sample_cache.values())
    frame_count = 18
    frame_times = [round(max_time * index / max(frame_count - 1, 1), 2) for index in range(frame_count)]
    highlight_window_s = max(0.8, max_time / max(frame_count * 2, 1))

    frames: list[go.Frame] = []
    for frame_time in frame_times:
        traces: list[go.Scatter3d] = []
        for mission in missions:
            samples = sample_cache[mission.drone_id]
            traveled = [sample for sample in samples if sample[3] <= frame_time]
            remaining = [sample for sample in samples if sample[3] >= frame_time]
            current = _current_sample(samples, frame_time)
            future_path = [current, *remaining] if remaining else [current]
            traces.append(
                go.Scatter3d(
                    x=[sample[0] for sample in future_path],
                    y=[sample[1] for sample in future_path],
                    z=[sample[2] for sample in future_path],
                    mode="lines",
                    line={"color": palette[mission.drone_id], "width": 4, "dash": "dot"},
                    name=f"{mission.drone_id} remaining route",
                    opacity=0.18,
                    showlegend=False,
                )
            )
            traces.append(
                go.Scatter3d(
                    x=[sample[0] for sample in traveled] or [samples[0][0]],
                    y=[sample[1] for sample in traveled] or [samples[0][1]],
                    z=[sample[2] for sample in traveled] or [samples[0][2]],
                    mode="lines",
                    line={"color": palette[mission.drone_id], "width": 6},
                    name=mission.drone_id,
                    showlegend=False,
                )
            )
            traces.append(
                go.Scatter3d(
                    x=[current[0]],
                    y=[current[1]],
                    z=[current[2]],
                    mode="markers+text",
                    marker={"size": 6, "color": palette[mission.drone_id]},
                    text=[mission.drone_id],
                    textposition="top center",
                    name=f"{mission.drone_id} now",
                    showlegend=False,
                )
            )

        for conflict in _active_conflicts(conflicts, frame_time, highlight_window_s):
            traces.append(
                go.Scatter3d(
                    x=[conflict.location[0]],
                    y=[conflict.location[1]],
                    z=[conflict.location[2]],
                    mode="markers+text",
                    marker={"symbol": "x", "size": 7, "color": "#ff006e"},
                    text=[f"conflict @ t={conflict.conflict_time_s:.1f}s"],
                    textposition="top center",
                    name="conflict",
                    showlegend=False,
                )
            )

        frames.append(go.Frame(data=traces, name=f"{frame_time:.1f}s"))

    slider_steps = [
        {
            "args": [[frame.name], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
            "label": frame.name,
            "method": "animate",
        }
        for frame in frames
    ]

    fig = go.Figure(data=frames[0].data if frames else [], frames=frames)
    fig.update_layout(
        title=f"{title} | 4D replay (solid=history, dashed=remaining path, X=active conflict) | status={status}",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)", aspectmode="data"),
        template="plotly_white",
        width=980,
        height=700,
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
                        "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                    },
                ],
            }
        ],
        sliders=[{"currentvalue": {"prefix": "Time: "}, "steps": slider_steps}],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_dir / f"{title.lower().replace(' ', '_')}_4d.html", include_plotlyjs="cdn")


def render_demo_plots(output_dir: str = "plots") -> None:
    root = Path(output_dir)
    p1, o1 = basic_conflict_case()
    p2, o2 = conflict_free_case()
    p3, o3 = time_shifted_crossing_case()
    p4, o4 = timed_waypoint_case()
    cases = [
        ("Conflict Case", p1, o1),
        ("Conflict Free Case", p2, o2),
        ("Time Shifted Crossing", p3, o3),
        ("Timed Waypoint Case", p4, o4),
    ]
    for title, primary, others in cases:
        _render_2d_case(title, primary, others, root)
        _render_3d_case(title, primary, others, root)
        _render_4d_case(title, primary, others, root)


if __name__ == "__main__":
    render_demo_plots()
