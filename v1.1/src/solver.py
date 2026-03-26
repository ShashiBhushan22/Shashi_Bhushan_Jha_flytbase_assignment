from __future__ import annotations

from math import sqrt

from models import ConflictDetail, ConflictReport, Mission
from trajectory import build_segments


def _vel(seg) -> tuple[float, float, float]:
    dt = seg.t1 - seg.t0
    return (
        (seg.p1[0] - seg.p0[0]) / dt,
        (seg.p1[1] - seg.p0[1]) / dt,
        (seg.p1[2] - seg.p0[2]) / dt,
    )


def _pos(seg, t: float) -> tuple[float, float, float]:
    ratio = (t - seg.t0) / (seg.t1 - seg.t0)
    return (
        seg.p0[0] + ratio * (seg.p1[0] - seg.p0[0]),
        seg.p0[1] + ratio * (seg.p1[1] - seg.p0[1]),
        seg.p0[2] + ratio * (seg.p1[2] - seg.p0[2]),
    )


def _within_window(mission: Mission, time_s: float) -> bool:
    if mission.mission_window_s is None:
        return True
    start_s, end_s = mission.mission_window_s
    return start_s <= time_s <= end_s


def _pair_conflicts(primary: Mission, other: Mission, buffer_m: float = 10.0) -> list[ConflictDetail]:
    conflicts: list[ConflictDetail] = []
    for a in build_segments(primary):
        for b in build_segments(other):
            lo = max(a.t0, b.t0)
            hi = min(a.t1, b.t1)
            if lo >= hi:
                continue

            va = _vel(a)
            vb = _vel(b)
            ca = (a.p0[0] - va[0] * a.t0, a.p0[1] - va[1] * a.t0, a.p0[2] - va[2] * a.t0)
            cb = (b.p0[0] - vb[0] * b.t0, b.p0[1] - vb[1] * b.t0, b.p0[2] - vb[2] * b.t0)
            cx = ca[0] - cb[0]
            cy = ca[1] - cb[1]
            cz = ca[2] - cb[2]
            vx = va[0] - vb[0]
            vy = va[1] - vb[1]
            vz = va[2] - vb[2]

            qa = vx * vx + vy * vy + vz * vz
            qb = 2.0 * (cx * vx + cy * vy + cz * vz)
            t_star = lo if qa == 0 else max(lo, min(hi, -qb / (2.0 * qa)))

            pa = _pos(a, t_star)
            pb = _pos(b, t_star)
            d = sqrt((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2 + (pa[2] - pb[2]) ** 2)
            if d <= buffer_m:
                if not _within_window(primary, t_star) or not _within_window(other, t_star):
                    continue
                conflicts.append(
                    ConflictDetail(
                        drone_a=primary.drone_id,
                        drone_b=other.drone_id,
                        time_s=t_star,
                        location=((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, (pa[2] + pb[2]) / 2.0),
                        minimum_distance_m=d,
                        reason="Continuous-time minimum separation is below safety buffer",
                    )
                )
                return conflicts
    return conflicts


def analyze_mission(primary: Mission, others: list[Mission], buffer_m: float = 10.0) -> ConflictReport:
    conflicts: list[ConflictDetail] = []
    warnings: list[str] = []
    primary_segments = build_segments(primary)
    if primary.mission_window_s is not None:
        window_start_s, window_end_s = primary.mission_window_s
        if primary.departure_time_s < window_start_s or primary_segments[-1].t1 > window_end_s:
            warnings.append(
                f"{primary.drone_id} trajectory extends beyond mission window [{window_start_s:.1f}, {window_end_s:.1f}]s."
            )
    for other in others:
        conflicts.extend(_pair_conflicts(primary, other, buffer_m=buffer_m))
    conflicts.sort(key=lambda item: (item.time_s, item.minimum_distance_m, item.drone_b))
    return ConflictReport(status="clear" if not conflicts else "conflict detected", conflicts=conflicts, warnings=warnings)


def has_conflict(primary: Mission, other: Mission, buffer_m: float = 10.0) -> bool:
    return bool(_pair_conflicts(primary, other, buffer_m=buffer_m))
