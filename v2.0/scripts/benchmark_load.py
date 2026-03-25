from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flytbase_atc.performance import benchmark_prediction_load, find_breaking_point


def main() -> None:
    counts = [30, 60, 80, 100]
    measurements = benchmark_prediction_load(counts, repeats=3)
    print("drone_count,avg_latency_ms,worst_latency_ms,pair_checks,alert_count,status")
    for item in measurements:
        print(
            f"{item.drone_count},{item.average_latency_ms:.2f},{item.worst_latency_ms:.2f},"
            f"{item.pair_checks},{item.alert_count},{item.health_status}"
        )

    breaking_point = find_breaking_point(measurements)
    if breaking_point is None:
        print("breaking_point,none")
    else:
        print(f"breaking_point,{breaking_point}")


if __name__ == "__main__":
    main()
