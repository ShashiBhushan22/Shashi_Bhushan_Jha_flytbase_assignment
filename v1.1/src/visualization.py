from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from models import Mission
from scenarios import crossing_conflict_case, crossing_no_conflict_time_shift_case, mixed_speed_case
from solver import analyze_mission


def _plot_mission(fig: go.Figure, mission: Mission, color: str, label: str) -> None:
    xs = [point[0] for point in mission.waypoints]
    ys = [point[1] for point in mission.waypoints]
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


def _render(name: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    report = analyze_mission(primary, others, buffer_m=10.0)

    fig = go.Figure()
    _plot_mission(fig, primary, "#0a9396", f"{primary.drone_id} (primary)")
    palette = ["#bb3e03", "#6d597a", "#588157"]
    for idx, other in enumerate(others):
        _plot_mission(fig, other, palette[idx % len(palette)], other.drone_id)

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


def render_demo_plots(output_dir: str = "plots") -> None:
    root = Path(output_dir)
    p1, o1 = crossing_conflict_case()
    p2, o2 = crossing_no_conflict_time_shift_case()
    p3, o3 = mixed_speed_case()
    _render("Crossing Conflict", p1, o1, root)
    _render("Crossing Time Shift", p2, o2, root)
    _render("Mixed Speed", p3, o3, root)


if __name__ == "__main__":
    render_demo_plots()
