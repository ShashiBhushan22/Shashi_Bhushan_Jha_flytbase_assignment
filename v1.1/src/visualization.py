from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from models import Mission
from scenarios import crossing_conflict_case, crossing_no_conflict_time_shift_case, mixed_speed_case
from solver import analyze_mission
from trajectory import build_segments, normalize_waypoint


def _plot_mission_2d(fig: go.Figure, mission: Mission, color: str, label: str) -> None:
    xs = [normalize_waypoint(point)[0] for point in mission.waypoints]
    ys = [normalize_waypoint(point)[1] for point in mission.waypoints]
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


def _plot_mission_3d(fig: go.Figure, mission: Mission, color: str, label: str, opacity: float = 1.0) -> None:
    xs = [normalize_waypoint(point)[0] for point in mission.waypoints]
    ys = [normalize_waypoint(point)[1] for point in mission.waypoints]
    zs = [normalize_waypoint(point)[2] for point in mission.waypoints]
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


def _sample_path(mission: Mission, samples_per_segment: int = 24) -> list[tuple[float, float, float, float]]:
    samples: list[tuple[float, float, float, float]] = []
    segments = build_segments(mission)
    for segment in segments:
        for index in range(samples_per_segment):
            ratio = index / samples_per_segment
            timestamp_s = segment.t0 + ratio * (segment.t1 - segment.t0)
            samples.append(
                (
                    segment.p0[0] + ratio * (segment.p1[0] - segment.p0[0]),
                    segment.p0[1] + ratio * (segment.p1[1] - segment.p0[1]),
                    segment.p0[2] + ratio * (segment.p1[2] - segment.p0[2]),
                    timestamp_s,
                )
            )
    end = segments[-1]
    samples.append((end.p1[0], end.p1[1], end.p1[2], end.t1))
    return samples


def _current_sample(samples: list[tuple[float, float, float, float]], time_s: float) -> tuple[float, float, float, float]:
    visible = [sample for sample in samples if sample[3] <= time_s]
    return visible[-1] if visible else samples[0]


def _active_conflicts(conflicts, frame_time: float, highlight_window_s: float) -> list:
    return [
        conflict
        for conflict in conflicts
        if abs(conflict.time_s - frame_time) <= highlight_window_s
    ]


def _render_2d(name: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    report = analyze_mission(primary, others, buffer_m=10.0)

    fig = go.Figure()
    _plot_mission_2d(fig, primary, "#0a9396", f"{primary.drone_id} (primary)")
    palette = ["#bb3e03", "#6d597a", "#588157"]
    for idx, other in enumerate(others):
        _plot_mission_2d(fig, other, palette[idx % len(palette)], other.drone_id)

    for conflict in report.conflicts:
        fig.add_trace(
            go.Scatter(
                x=[conflict.location[0]],
                y=[conflict.location[1]],
                mode="markers+text",
                marker={"symbol": "x", "size": 12, "color": "#ff006e"},
                text=[f"t={conflict.time_s:.2f}s"],
                textposition="top right",
                name="conflict",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"{name} | status={report.status}",
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        template="plotly_white",
        width=950,
        height=620,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_dir / f"{name.lower().replace(' ', '_')}.html", include_plotlyjs="cdn")


def _render_3d(name: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    report = analyze_mission(primary, others, buffer_m=10.0)
    fig = go.Figure()
    _plot_mission_3d(fig, primary, "#0a9396", f"{primary.drone_id} (primary)")
    palette = ["#bb3e03", "#6d597a", "#588157"]
    for idx, other in enumerate(others):
        _plot_mission_3d(fig, other, palette[idx % len(palette)], other.drone_id)

    for conflict in report.conflicts:
        fig.add_trace(
            go.Scatter3d(
                x=[conflict.location[0]],
                y=[conflict.location[1]],
                z=[conflict.location[2]],
                mode="markers+text",
                marker={"symbol": "x", "size": 7, "color": "#ff006e"},
                text=[f"t={conflict.time_s:.2f}s"],
                textposition="top center",
                name="conflict",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"{name} | 3D continuous view | status={report.status}",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)", aspectmode="data"),
        template="plotly_white",
        width=980,
        height=680,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_dir / f"{name.lower().replace(' ', '_')}_3d.html", include_plotlyjs="cdn")


def _render_4d(name: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    missions = [primary, *others]
    palette = {
        primary.drone_id: "#0a9396",
        **{mission.drone_id: color for mission, color in zip(others, ["#bb3e03", "#6d597a", "#588157"])},
    }
    sample_cache = {mission.drone_id: _sample_path(mission) for mission in missions}
    report = analyze_mission(primary, others, buffer_m=10.0)
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
                    showlegend=False,
                )
            )

        for conflict in _active_conflicts(report.conflicts, frame_time, highlight_window_s):
            traces.append(
                go.Scatter3d(
                    x=[conflict.location[0]],
                    y=[conflict.location[1]],
                    z=[conflict.location[2]],
                    mode="markers+text",
                    marker={"symbol": "x", "size": 7, "color": "#ff006e"},
                    text=[f"conflict @ t={conflict.time_s:.1f}s"],
                    textposition="top center",
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
        title=f"{name} | 4D replay (solid=history, dashed=remaining path, X=active conflict) | status={report.status}",
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
    fig.write_html(output_dir / f"{name.lower().replace(' ', '_')}_4d.html", include_plotlyjs="cdn")


def render_demo_plots(output_dir: str = "plots") -> None:
    root = Path(output_dir)
    p1, o1 = crossing_conflict_case()
    p2, o2 = crossing_no_conflict_time_shift_case()
    p3, o3 = mixed_speed_case()
    cases = [
        ("Crossing Conflict", p1, o1),
        ("Crossing Time Shift", p2, o2),
        ("Mixed Speed", p3, o3),
    ]
    for name, primary, others in cases:
        _render_2d(name, primary, others, root)
        _render_3d(name, primary, others, root)
        _render_4d(name, primary, others, root)


if __name__ == "__main__":
    render_demo_plots()
