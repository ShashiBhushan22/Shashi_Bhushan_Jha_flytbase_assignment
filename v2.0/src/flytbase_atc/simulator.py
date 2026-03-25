"""Telemetry and operational simulator for the ATC dashboard."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import inf
import random
from typing import Deque

from .geometry import build_trajectory_profile, distance
from .models import MissionPlan, TelemetryConfig, TrajectoryProfile, Vector3


@dataclass(frozen=True)
class TelemetrySample:
    drone_id: str
    timestamp_s: float
    position: Vector3
    controlled: bool
    stale: bool = False


@dataclass
class PauseWindow:
    start_s: float
    end_s: float | None = None


@dataclass
class AirspaceSimulator:
    """Deterministic simulator for operator review and incident replay."""

    plans: list[MissionPlan]
    seed: int = 13
    telemetry_history: dict[str, Deque[TelemetrySample]] = field(default_factory=dict)
    pause_windows: dict[str, list[PauseWindow]] = field(default_factory=dict)
    profiles: dict[str, TrajectoryProfile] = field(init=False, default_factory=dict)
    plans_by_id: dict[str, MissionPlan] = field(init=False, default_factory=dict)
    last_emitted_s: dict[str, float] = field(init=False, default_factory=dict)
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.plans_by_id = {plan.drone_id: plan for plan in self.plans}
        self.profiles = {plan.drone_id: build_trajectory_profile(plan) for plan in self.plans}
        for plan in self.plans:
            self.telemetry_history.setdefault(plan.drone_id, deque(maxlen=2000))
            self.pause_windows.setdefault(plan.drone_id, [])
            self.last_emitted_s.setdefault(plan.drone_id, -inf)

    @property
    def controlled_drone_ids(self) -> list[str]:
        return [plan.drone_id for plan in self.plans if plan.controlled]

    @property
    def unknown_drone_ids(self) -> list[str]:
        return [plan.drone_id for plan in self.plans if not plan.controlled]

    def pause_drone(self, drone_id: str, timestamp_s: float) -> None:
        windows = self.pause_windows.setdefault(drone_id, [])
        if windows and windows[-1].end_s is None:
            return
        windows.append(PauseWindow(start_s=timestamp_s))

    def resume_drone(self, drone_id: str, timestamp_s: float) -> None:
        windows = self.pause_windows.setdefault(drone_id, [])
        if not windows or windows[-1].end_s is not None:
            return
        windows[-1].end_s = timestamp_s

    def is_paused(self, drone_id: str, timestamp_s: float) -> bool:
        windows = self.pause_windows.get(drone_id, [])
        if not windows:
            return False
        window = windows[-1]
        return window.end_s is None and timestamp_s >= window.start_s

    def paused_duration_before(self, drone_id: str, timestamp_s: float) -> float:
        total = 0.0
        for window in self.pause_windows.get(drone_id, []):
            if window.end_s is not None:
                if window.end_s <= timestamp_s:
                    total += window.end_s - window.start_s
            else:
                if timestamp_s >= window.start_s:
                    total += timestamp_s - window.start_s
        return total

    def effective_time(self, drone_id: str, timestamp_s: float) -> float:
        paused_windows = self.pause_windows.get(drone_id, [])
        total_paused = 0.0
        for window in paused_windows:
            if window.end_s is not None and window.end_s <= timestamp_s:
                total_paused += window.end_s - window.start_s
            elif window.end_s is None and timestamp_s >= window.start_s:
                return window.start_s - self.paused_duration_before(drone_id, window.start_s)
        return timestamp_s - total_paused

    def position_at(self, drone_id: str, timestamp_s: float) -> Vector3:
        profile = self.profiles[drone_id]
        effective_timestamp = self.effective_time(drone_id, timestamp_s)
        return profile.position_at(effective_timestamp)

    def telemetry_packet(self, drone_id: str, timestamp_s: float) -> TelemetrySample:
        plan = self.plans_by_id[drone_id]
        config = TelemetryConfig(
            rate_hz=plan.telemetry_hz,
            dropout_prob=plan.telemetry_dropout_prob,
            noise_m=plan.telemetry_noise_m,
            delay_s=plan.telemetry_delay_s,
        )
        if self.rng.random() < config.dropout_prob:
            sample = TelemetrySample(drone_id, timestamp_s, self.position_at(drone_id, timestamp_s), plan.controlled, stale=True)
            self.telemetry_history[drone_id].append(sample)
            return sample

        reported_time = max(0.0, timestamp_s - config.delay_s)
        x, y, z = self.position_at(drone_id, reported_time)
        if config.noise_m > 0.0:
            x += self.rng.uniform(-config.noise_m, config.noise_m)
            y += self.rng.uniform(-config.noise_m, config.noise_m)
            z += self.rng.uniform(-config.noise_m * 0.5, config.noise_m * 0.5)

        sample = TelemetrySample(drone_id, timestamp_s, (x, y, z), plan.controlled, stale=False)
        self.telemetry_history[drone_id].append(sample)
        return sample

    def snapshot(self, timestamp_s: float) -> list[TelemetrySample]:
        samples: list[TelemetrySample] = []
        for plan in self.plans:
            interval_s = 1.0 / plan.telemetry_hz
            if timestamp_s - self.last_emitted_s[plan.drone_id] + 1e-9 < interval_s:
                continue
            self.last_emitted_s[plan.drone_id] = timestamp_s
            samples.append(self.telemetry_packet(plan.drone_id, timestamp_s))
        return samples

    def paused_status(self, timestamp_s: float, warning_after_s: float = 20.0) -> list[dict[str, object]]:
        statuses: list[dict[str, object]] = []
        for plan in self.plans:
            paused = self.is_paused(plan.drone_id, timestamp_s)
            duration = 0.0
            if paused:
                duration = timestamp_s - self.pause_windows[plan.drone_id][-1].start_s
            statuses.append(
                {
                    "drone_id": plan.drone_id,
                    "controlled": plan.controlled,
                    "paused": paused,
                    "paused_duration_s": round(duration, 2),
                    "warning": paused and duration >= warning_after_s,
                }
            )
        statuses.sort(key=lambda item: (-int(bool(item["warning"])), -float(item["paused_duration_s"]), str(item["drone_id"])))
        return statuses

    def preview_resume(
        self,
        drone_id: str,
        timestamp_s: float,
        horizon_s: float = 20.0,
        step_s: float = 1.0,
    ) -> list[dict[str, object]]:
        """Preview short-term path if a paused drone is resumed now."""

        profile = self.profiles[drone_id]
        effective_start = self.effective_time(drone_id, timestamp_s)
        preview: list[dict[str, object]] = []
        elapsed = 0.0
        while elapsed <= horizon_s + 1e-9:
            world_t = timestamp_s + elapsed
            effective_t = effective_start + elapsed
            preview.append({"time_s": world_t, drone_id: profile.position_at(effective_t)})
            elapsed += step_s
        return preview

    def replay_window(self, drone_ids: list[str], center_time_s: float, window_s: float = 20.0, step_s: float = 1.0) -> list[dict[str, object]]:
        start = max(0.0, center_time_s - window_s)
        end = center_time_s
        timeline: list[dict[str, object]] = []
        current = start
        while current <= end + 1e-9:
            frame: dict[str, object] = {"time_s": current}
            for drone_id in drone_ids:
                frame[drone_id] = self.position_at(drone_id, current)
            timeline.append(frame)
            current += step_s
        return timeline

    def conflict_hotspots(self, timestamp_s: float, buffer_m: float = 10.0) -> list[tuple[str, str, float]]:
        hotspots: list[tuple[str, str, float]] = []
        samples = {plan.drone_id: self.position_at(plan.drone_id, timestamp_s) for plan in self.plans}
        drone_ids = list(samples)
        for left_index in range(len(drone_ids)):
            for right_index in range(left_index + 1, len(drone_ids)):
                left = drone_ids[left_index]
                right = drone_ids[right_index]
                dist = distance(samples[left], samples[right])
                if dist <= buffer_m:
                    hotspots.append((left, right, dist))
        hotspots.sort(key=lambda item: item[2])
        return hotspots
