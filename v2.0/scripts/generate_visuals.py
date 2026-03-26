from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flytbase_atc.dashboard import build_airspace_figure, build_replay_animation_figure
from flytbase_atc.scenarios import build_conflict_scenario, build_dense_airspace_scenario


def main() -> None:
    output_dir = ROOT / "docs" / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    primary, others = build_conflict_scenario()
    conflict_plans = [primary, *others]
    conflict_figure = build_airspace_figure(conflict_plans, timestamp_s=10.0, buffer_m=10.0, lookahead_s=20.0)
    conflict_figure.write_html(output_dir / "atc_conflict_overview_3d.html", include_plotlyjs="cdn")

    primary_dense, others_dense = build_dense_airspace_scenario(30)
    dense_plans = [primary_dense, *others_dense]
    replay_figure = build_replay_animation_figure(
        dense_plans,
        start_time_s=0.0,
        end_time_s=20.0,
        buffer_m=10.0,
        lookahead_s=20.0,
        step_s=1.0,
    )
    replay_figure.write_html(output_dir / "atc_dense_replay_4d.html", include_plotlyjs="cdn")


if __name__ == "__main__":
    main()
