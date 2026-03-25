"""Ready-made scenarios for demos, testing, and dashboard previews."""

from __future__ import annotations

import random

from .models import MissionPlan, Waypoint


def build_conflict_free_scenario() -> tuple[MissionPlan, list[MissionPlan]]:
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(120, 0), Waypoint(180, 60)],
        speed_mps=12.0,
        departure_time_s=0.0,
        mission_window_s=(0.0, 40.0),
    )
    others = [
        MissionPlan("drone_a", [Waypoint(0, 40), Waypoint(160, 40)], 10.0, departure_time_s=30.0, controlled=False),
        MissionPlan("drone_b", [Waypoint(200, -30), Waypoint(220, 80)], 14.0, departure_time_s=10.0, controlled=False),
    ]
    return primary, others


def build_conflict_scenario() -> tuple[MissionPlan, list[MissionPlan]]:
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(100, 100)],
        speed_mps=10.0,
        departure_time_s=0.0,
        mission_window_s=(0.0, 20.0),
    )
    others = [
        MissionPlan(
            drone_id="intruder",
            waypoints=[Waypoint(100, 0), Waypoint(0, 100)],
            speed_mps=10.0,
            departure_time_s=0.0,
            controlled=False,
        )
    ]
    return primary, others


def build_dense_airspace_scenario(count: int = 30, seed: int = 7) -> tuple[MissionPlan, list[MissionPlan]]:
    rng = random.Random(seed)
    primary = MissionPlan(
        drone_id="primary",
        waypoints=[Waypoint(0, 0), Waypoint(120, 30), Waypoint(220, 20)],
        speed_mps=15.0,
        departure_time_s=0.0,
        mission_window_s=(0.0, 40.0),
    )
    others: list[MissionPlan] = []
    for index in range(count):
        start_x = rng.uniform(-40, 260)
        start_y = rng.uniform(-60, 160)
        end_x = rng.uniform(-40, 260)
        end_y = rng.uniform(-60, 160)
        speed = rng.uniform(8.0, 18.0)
        departure = rng.uniform(0.0, 35.0)
        altitude = rng.choice([None, 20.0, 40.0])
        waypoints = [Waypoint(start_x, start_y, altitude), Waypoint(end_x, end_y, altitude)]
        others.append(
            MissionPlan(
                drone_id=f"drone_{index + 1}",
                waypoints=waypoints,
                speed_mps=speed,
                departure_time_s=departure,
                controlled=index % 3 != 0,
                telemetry_hz=rng.uniform(0.5, 2.0),
                telemetry_dropout_prob=rng.uniform(0.0, 0.15),
                telemetry_noise_m=rng.uniform(0.0, 1.5),
                telemetry_delay_s=rng.uniform(0.0, 0.5),
            )
        )
    return primary, others


def build_demo_scenario() -> tuple[MissionPlan, list[MissionPlan]]:
    """Default scenario used by the dashboard and CLI preview."""

    return build_conflict_scenario()
