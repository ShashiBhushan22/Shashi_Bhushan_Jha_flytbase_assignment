from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from deconfliction import check_mission
from models import Mission
from scenarios import basic_conflict_case, conflict_free_case, timed_waypoint_case


def _plot_mission(fig: go.Figure, mission: Mission, label: str, color: str) -> None:
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


def _render_case(title: str, primary: Mission, others: list[Mission], output_dir: Path) -> None:
    status, conflicts = check_mission(primary, others, safety_buffer_m=10.0)

    fig = go.Figure()
    _plot_mission(fig, primary, f"{primary.drone_id} (primary)", "#005f73")
    palette = ["#ae2012", "#9b2226", "#6a4c93", "#2a9d8f"]

    for idx, other in enumerate(others):
        _plot_mission(fig, other, other.drone_id, palette[idx % len(palette)])

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


def render_demo_plots(output_dir: str = "plots") -> None:
    root = Path(output_dir)
    p1, o1 = basic_conflict_case()
    p2, o2 = conflict_free_case()
    p3, o3 = timed_waypoint_case()
    _render_case("Conflict Case", p1, o1, root)
    _render_case("Conflict Free Case", p2, o2, root)
    _render_case("Timed Waypoint Case", p3, o3, root)


if __name__ == "__main__":
    render_demo_plots()
