# FlytBase Robotics Assignment V2

This repository implements a real-time ATC-focused extension of strategic deconfliction, including pre-flight mission review, continuous conflict prediction, telemetry simulation, operator controls, and replay.

## What is included

- Exact spatio-temporal conflict detection using continuously parameterized path segments.
- Pre-flight review queue with approve, delay, reject outputs and delay suggestions.
- Real-time alert prediction with grouped and prioritized conflict alerts.
- Controlled vs unknown drone simulation with configurable telemetry rate, delay, noise, and dropout.
- Pause/resume controls, paused-duration warnings, and safe-resume preview.
- Incident replay window for selected alerts.
- System health indicators (latency, pair checks, degraded-state signals).
- Pytest coverage for geometry, prediction, simulator, and ATC workflow logic.

## Recommended workflow

1. Validate conflict math and simulator behavior with tests.
2. Launch the dashboard and inspect conflict and non-conflict scenarios.
3. Exercise operator actions: pause/resume, queue filtering, and replay.
4. Increase drone count (30+) to observe health/load behavior.

## Project structure

- `app.py`: Streamlit dashboard entrypoint.
- `server/main.py`: FastAPI backend with REST and WebSocket endpoints.
- `frontend/`: React + Vite operator dashboard.
- `src/flytbase_atc/models.py`: Core data structures.
- `src/flytbase_atc/geometry.py`: Trajectory construction and continuous conflict math.
- `src/flytbase_atc/deconfliction.py`: Conflict analysis, prediction, alert grouping, queue review, and health snapshots.
- `src/flytbase_atc/simulator.py`: Telemetry simulator with configurable rates/dropouts/noise and pause/resume support.
- `src/flytbase_atc/scenarios.py`: Demo scenarios.
- `tests/`: Automated tests.
- `docs/reflection.md`: Short justification and scalability notes.

## Setup

Use Python 3.10 or newer.

```bash
cd /home/bhushan-arc/flytbase/v2.0
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

Install frontend dependencies:

```bash
cd /home/bhushan-arc/flytbase/v2.0/frontend
npm install
```

## Run tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

## Run the primary assignment dashboard

```bash
streamlit run app.py
```

This Streamlit app is the main assignment-facing dashboard. It exposes the full operator workflow: pre-flight review, grouped in-air alerts, pause/resume controls, safe-resume preview, replay, and a performance sweep panel.

## Run the API and React console

Backend API:

```bash
cd /home/bhushan-arc/flytbase/v2.0
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Frontend UI:

```bash
cd /home/bhushan-arc/flytbase/v2.0/frontend
npm run dev
```

Build frontend for production verification:

```bash
cd /home/bhushan-arc/flytbase/v2.0/frontend
npm run build
```

## Backend endpoints used by the React UI

- `GET /health`
- `GET /state`
- `POST /scenario/load`
- `POST /preflight/review`
- `POST /control/pause`
- `POST /control/resume`
- `GET /replay`
- `WS /ws/telemetry`

## Assignment mapping

- Pre-flight deconfliction: `review_mission` and `review_incoming_plans`.
- Real-time telemetry simulation (30+ drones): `build_dense_airspace_scenario` + `AirspaceSimulator`.
- Early conflict warnings: `predict_conflicts` + `group_alerts`.
- Simultaneous alert handling: grouped, prioritized alert list.
- Multiple paused drones: pause status table and warning threshold.
- Safe resumption preview: `preview_resume` projection.
- Airspace/system health: latency, load, and degradation notes.
- Incident replay: rolling replay window for selected conflicts.

## Implementation notes

The conflict engine models each path segment as a linear function of time and checks minimum separation over overlapping time intervals. This gives continuous-time detection rather than a sampled approximation.

## Performance sweep

Run the load benchmark:

```bash
cd /home/bhushan-arc/flytbase/v2.0
python scripts/benchmark_load.py
```

Sample output captured on March 25, 2026 in this workspace:

| Drone count | Avg latency (ms) | Worst latency (ms) | Pair checks | Alert groups | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| 30 | 1.81 | 1.93 | 465 | 3 | healthy |
| 60 | 6.61 | 7.47 | 1830 | 11 | healthy |
| 80 | 12.01 | 13.27 | 3240 | 16 | degraded |
| 100 | 16.95 | 17.54 | 5050 | 23 | degraded |

Latency values vary slightly from run to run based on host load, but the first observed degraded point remained 80 drones during verification. The ATC is notified through the dashboard health panel and the performance sweep table.

For the assignment write-up, explain:

- why the conflict engine is continuous,
- how the simulator supports controlled and unknown drones,
- how the dashboard helps an operator decide quickly,
- how the system would scale with real telemetry pipelines and distributed conflict checks.

## Next improvements

- Move telemetry ingestion to async workers and stream to dashboard over WebSockets.
- Add uncertainty-aware prediction for unknown drones using probabilistic tracks.
- Add dedicated load-test harness and automatic threshold tuning.
- Persist replay events to a time-series store for post-incident analytics.
