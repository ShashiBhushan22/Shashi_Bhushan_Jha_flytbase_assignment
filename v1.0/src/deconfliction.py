from __future__ import annotations

from math import dist

from models import Conflict, Mission


def _sample_path(mission: Mission, samples_per_leg: int = 30) -> list[tuple[float, float, float, float]]:
    """Interpolate mission path into time-stamped points for v1.0 checks."""

    if len(mission.waypoints) < 2:
        return []
    if mission.end_time_s <= mission.start_time_s:
        raise ValueError(f"Mission {mission.drone_id} must end after start")

    if mission.waypoint_times_s is not None:
        if len(mission.waypoint_times_s) != len(mission.waypoints):
            raise ValueError(f"Mission {mission.drone_id} has invalid waypoint timing metadata")
        if any(
            mission.waypoint_times_s[i] > mission.waypoint_times_s[i + 1]
            for i in range(len(mission.waypoint_times_s) - 1)
        ):
            raise ValueError(f"Mission {mission.drone_id} waypoint times must be monotonic")
        if mission.waypoint_times_s[0] < mission.start_time_s or mission.waypoint_times_s[-1] > mission.end_time_s:
            raise ValueError(f"Mission {mission.drone_id} waypoint times must lie within mission window")
        timeline = mission.waypoint_times_s
    else:
        total_time = mission.end_time_s - mission.start_time_s
        timeline = [
            mission.start_time_s + total_time * i / (len(mission.waypoints) - 1)
            for i in range(len(mission.waypoints))
        ]

    points: list[tuple[float, float, float, float]] = []
    for i in range(len(mission.waypoints) - 1):
        a = mission.waypoints[i]
        b = mission.waypoints[i + 1]
        ax, ay, az = a.as_vector()
        bx, by, bz = b.as_vector()
        leg_t0 = timeline[i]
        leg_t1 = timeline[i + 1]
        for sample in range(samples_per_leg):
            ratio = sample / float(samples_per_leg)
            t = leg_t0 + ratio * (leg_t1 - leg_t0)
            points.append(
                (
                    ax + ratio * (bx - ax),
                    ay + ratio * (by - ay),
                    az + ratio * (bz - az),
                    t,
                )
            )
    end_x, end_y, end_z = mission.waypoints[-1].as_vector()
    points.append((end_x, end_y, end_z, timeline[-1]))
    return points


def check_mission(
    primary: Mission,
    others: list[Mission],
    safety_buffer_m: float = 10.0,
    temporal_tolerance_s: float = 0.5,
) -> tuple[str, list[Conflict]]:
    """Return clear/conflict detected with explanatory conflict records."""

    primary_samples = _sample_path(primary)
    conflicts: list[Conflict] = []
    for other in others:
        other_samples = _sample_path(other)
        for px, py, pz, pt in primary_samples:
            for ox, oy, oz, ot in other_samples:
                if abs(pt - ot) > temporal_tolerance_s:
                    continue
                d = dist((px, py, pz), (ox, oy, oz))
                if d <= safety_buffer_m:
                    conflicts.append(
                        Conflict(
                            with_drone=other.drone_id,
                            own_drone=primary.drone_id,
                            conflict_time_s=pt,
                            location=((px + ox) / 2.0, (py + oy) / 2.0, (pz + oz) / 2.0),
                            minimum_distance_m=d,
                            reason="Temporal overlap with spatial separation below safety buffer.",
                        )
                    )
                    break
            if conflicts and conflicts[-1].with_drone == other.drone_id:
                break
    return ("clear" if not conflicts else "conflict detected", conflicts)
