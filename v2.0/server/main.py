from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from flytbase_atc.deconfliction import build_system_health_snapshot, review_incoming_plans
from flytbase_atc.models import MissionPlan, Waypoint
from flytbase_atc.scenarios import build_conflict_free_scenario, build_conflict_scenario, build_dense_airspace_scenario
from flytbase_atc.simulator import AirspaceSimulator


class WaypointPayload(BaseModel):
    x: float
    y: float
    z: float | None = None


class MissionPayload(BaseModel):
    drone_id: str
    waypoints: list[WaypointPayload]
    speed_mps: float = Field(gt=0)
    departure_time_s: float = 0.0
    mission_window_s: tuple[float, float] | None = None
    controlled: bool = True


class QueueReviewPayload(BaseModel):
    missions: list[MissionPayload]
    buffer_m: float = 10.0


class ControlPayload(BaseModel):
    drone_id: str
    timestamp_s: float


app = FastAPI(title="FlytBase ATC API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RuntimeState:
    def __init__(self) -> None:
        primary, others = build_dense_airspace_scenario(30)
        self.plans = [primary, *others]
        self.simulator = AirspaceSimulator(self.plans)
        self.current_time_s = 0.0


state = RuntimeState()


def _from_payload(payload: MissionPayload) -> MissionPlan:
    return MissionPlan(
        drone_id=payload.drone_id,
        waypoints=[Waypoint(item.x, item.y, item.z) for item in payload.waypoints],
        speed_mps=payload.speed_mps,
        departure_time_s=payload.departure_time_s,
        mission_window_s=payload.mission_window_s,
        controlled=payload.controlled,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scenario/load")
def load_scenario(name: str = "dense", dense_count: int = 30) -> dict[str, Any]:
    if name == "conflict":
        primary, others = build_conflict_scenario()
    elif name == "clear":
        primary, others = build_conflict_free_scenario()
    else:
        primary, others = build_dense_airspace_scenario(dense_count)

    state.plans = [primary, *others]
    state.simulator = AirspaceSimulator(state.plans)
    state.current_time_s = 0.0
    return {"ok": True, "drone_count": len(state.plans)}


@app.get("/state")
def get_state(timestamp_s: float = 10.0, buffer_m: float = 10.0, lookahead_s: float = 20.0) -> dict[str, Any]:
    state.current_time_s = timestamp_s
    packets = [asdict(sample) for sample in state.simulator.snapshot_full(timestamp_s)]
    health_snapshot, alerts = build_system_health_snapshot(state.plans, timestamp_s, lookahead_s, buffer_m)
    return {
        "time_s": timestamp_s,
        "drone_count": len(state.plans),
        "plans": [
            {
                "drone_id": plan.drone_id,
                "controlled": plan.controlled,
                "waypoints": [{"x": w.x, "y": w.y, "z": w.z} for w in plan.waypoints],
            }
            for plan in state.plans
        ],
        "telemetry": packets,
        "health": asdict(health_snapshot),
        "alerts": [asdict(alert) for alert in alerts],
        "paused": state.simulator.paused_status(timestamp_s),
    }


@app.post("/preflight/review")
def preflight_review(payload: QueueReviewPayload) -> dict[str, Any]:
    incoming = [_from_payload(item) for item in payload.missions]
    decisions = review_incoming_plans(incoming, state.plans, buffer_m=payload.buffer_m)
    return {"decisions": [asdict(item) for item in decisions]}


@app.post("/control/pause")
def pause_drone(payload: ControlPayload) -> dict[str, Any]:
    state.simulator.pause_drone(payload.drone_id, payload.timestamp_s)
    return {"ok": True}


@app.post("/control/resume")
def resume_drone(payload: ControlPayload) -> dict[str, Any]:
    state.simulator.resume_drone(payload.drone_id, payload.timestamp_s)
    return {"ok": True}


@app.get("/replay")
def replay(drone_ids: str, center_time_s: float, window_s: float = 15.0) -> dict[str, Any]:
    ids = [item.strip() for item in drone_ids.split(",") if item.strip()]
    frames = state.simulator.replay_window(ids, center_time_s=center_time_s, window_s=window_s)
    return {"frames": frames}


@app.websocket("/ws/telemetry")
async def ws_telemetry(socket: WebSocket) -> None:
    await socket.accept()
    t = state.current_time_s
    try:
        while True:
            t += 1.0
            packets = [asdict(sample) for sample in state.simulator.snapshot_full(t)]
            health_snapshot, alerts = build_system_health_snapshot(state.plans, t, 20.0, 10.0)
            await socket.send_json(
                {
                    "time_s": t,
                    "drone_count": len(state.plans),
                    "plans": [
                        {
                            "drone_id": plan.drone_id,
                            "controlled": plan.controlled,
                            "waypoints": [{"x": w.x, "y": w.y, "z": w.z} for w in plan.waypoints],
                        }
                        for plan in state.plans
                    ],
                    "telemetry": packets,
                    "health": asdict(health_snapshot),
                    "alerts": [asdict(alert) for alert in alerts],
                    "paused": state.simulator.paused_status(t),
                }
            )
            await asyncio.sleep(1.0)
    except Exception:
        await socket.close()
