"""Geometry helpers for trajectory generation and conflict checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .models import MissionPlan, TrajectoryProfile, TrajectorySegment, Vector3

EPSILON = 1e-9


def vector_add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vector_sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vector_scale(v: Vector3, scalar: float) -> Vector3:
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)


def dot(a: Vector3, b: Vector3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(v: Vector3) -> float:
    return sqrt(dot(v, v))


def distance(a: Vector3, b: Vector3) -> float:
    return norm(vector_sub(a, b))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def normalize_waypoints(plan: MissionPlan) -> list[Vector3]:
    return [waypoint.as_vector() for waypoint in plan.waypoints]


def build_trajectory_profile(plan: MissionPlan) -> TrajectoryProfile:
    points = normalize_waypoints(plan)
    segment_lengths = [distance(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total_length = sum(segment_lengths)
    if total_length <= EPSILON:
        raise ValueError(f"MissionPlan {plan.drone_id} has zero-length path")

    total_duration = total_length / plan.speed_mps
    current_time = plan.departure_time_s
    segments: list[TrajectorySegment] = []

    for index, segment_length in enumerate(segment_lengths):
        segment_duration = total_duration * (segment_length / total_length)
        next_time = current_time + segment_duration
        segments.append(
            TrajectorySegment(
                index=index,
                start_time_s=current_time,
                end_time_s=next_time,
                start_point=points[index],
                end_point=points[index + 1],
            )
        )
        current_time = next_time

    return TrajectoryProfile(
        drone_id=plan.drone_id,
        segments=segments,
        path_length_m=total_length,
        duration_s=total_duration,
        start_time_s=plan.departure_time_s,
        end_time_s=current_time,
        mission_window_s=plan.mission_window_s,
    )


def profile_is_within_window(profile: TrajectoryProfile) -> bool:
    if profile.mission_window_s is None:
        return True
    window_start, window_end = profile.mission_window_s
    return profile.start_time_s >= window_start - EPSILON and profile.end_time_s <= window_end + EPSILON


@dataclass(frozen=True)
class SegmentConflict:
    segment_a_index: int
    segment_b_index: int
    start_time_s: float
    end_time_s: float
    closest_approach_time_s: float
    point_a: Vector3
    point_b: Vector3
    minimum_distance_m: float


def segment_conflict_window(segment_a: TrajectorySegment, segment_b: TrajectorySegment, buffer_m: float) -> SegmentConflict | None:
    overlap_start = max(segment_a.start_time_s, segment_b.start_time_s)
    overlap_end = min(segment_a.end_time_s, segment_b.end_time_s)
    if overlap_start >= overlap_end:
        return None

    velocity_a = segment_a.velocity_vector
    velocity_b = segment_b.velocity_vector

    coeff_a = vector_sub(segment_a.start_point, vector_scale(velocity_a, segment_a.start_time_s))
    coeff_b = vector_sub(segment_b.start_point, vector_scale(velocity_b, segment_b.start_time_s))
    relative_coeff = vector_sub(coeff_a, coeff_b)
    relative_velocity = vector_sub(velocity_a, velocity_b)

    a = dot(relative_velocity, relative_velocity)
    b = 2.0 * dot(relative_coeff, relative_velocity)
    c = dot(relative_coeff, relative_coeff) - buffer_m * buffer_m

    if a <= EPSILON:
        distance_now = sqrt(dot(relative_coeff, relative_coeff))
        if distance_now <= buffer_m + EPSILON:
            return SegmentConflict(
                segment_a_index=segment_a.index,
                segment_b_index=segment_b.index,
                start_time_s=overlap_start,
                end_time_s=overlap_end,
                closest_approach_time_s=overlap_start,
                point_a=segment_a.position_at(overlap_start),
                point_b=segment_b.position_at(overlap_start),
                minimum_distance_m=distance_now,
            )
        return None

    discriminant = b * b - 4.0 * a * c
    if discriminant < -EPSILON:
        closest_time = clamp(-b / (2.0 * a), overlap_start, overlap_end)
        delta = vector_add(relative_coeff, vector_scale(relative_velocity, closest_time))
        minimum_distance = norm(delta)
        if minimum_distance <= buffer_m + EPSILON:
            return SegmentConflict(
                segment_a_index=segment_a.index,
                segment_b_index=segment_b.index,
                start_time_s=closest_time,
                end_time_s=closest_time,
                closest_approach_time_s=closest_time,
                point_a=segment_a.position_at(closest_time),
                point_b=segment_b.position_at(closest_time),
                minimum_distance_m=minimum_distance,
            )
        return None

    discriminant = max(0.0, discriminant)
    root_distance = sqrt(discriminant)
    root_one = (-b - root_distance) / (2.0 * a)
    root_two = (-b + root_distance) / (2.0 * a)
    conflict_start = max(overlap_start, min(root_one, root_two))
    conflict_end = min(overlap_end, max(root_one, root_two))

    if conflict_start > conflict_end + EPSILON:
        closest_time = clamp(-b / (2.0 * a), overlap_start, overlap_end)
        delta = vector_add(relative_coeff, vector_scale(relative_velocity, closest_time))
        minimum_distance = norm(delta)
        if minimum_distance <= buffer_m + EPSILON:
            return SegmentConflict(
                segment_a_index=segment_a.index,
                segment_b_index=segment_b.index,
                start_time_s=closest_time,
                end_time_s=closest_time,
                closest_approach_time_s=closest_time,
                point_a=segment_a.position_at(closest_time),
                point_b=segment_b.position_at(closest_time),
                minimum_distance_m=minimum_distance,
            )
        return None

    closest_time = clamp(-b / (2.0 * a), overlap_start, overlap_end)
    delta = vector_add(relative_coeff, vector_scale(relative_velocity, closest_time))
    minimum_distance = norm(delta)

    return SegmentConflict(
        segment_a_index=segment_a.index,
        segment_b_index=segment_b.index,
        start_time_s=conflict_start,
        end_time_s=conflict_end,
        closest_approach_time_s=closest_time,
        point_a=segment_a.position_at(closest_time),
        point_b=segment_b.position_at(closest_time),
        minimum_distance_m=minimum_distance,
    )
