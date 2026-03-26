import { useEffect, useMemo, useRef, useState } from "react";

type TelemetrySample = {
  drone_id: string;
  timestamp_s: number;
  position: [number, number, number];
  controlled: boolean;
  stale: boolean;
};

type WaypointSummary = {
  x: number;
  y: number;
  z: number | null;
};

type PlanSummary = {
  drone_id: string;
  controlled: boolean;
  waypoints: WaypointSummary[];
};

type AlertGroup = {
  group_id: string;
  drone_ids: [string, string] | string[];
  highest_severity: string;
  earliest_time_s: number;
  actionable: boolean;
  confidence: number;
  suggested_actions: string[];
};

type Health = {
  status: string;
  compute_latency_ms: number;
  pair_checks: number;
  checks_per_second: number;
};

type PausedStatus = {
  drone_id: string;
  controlled: boolean;
  paused: boolean;
  paused_duration_s: number;
  warning: boolean;
};

type ApiState = {
  time_s: number;
  drone_count: number;
  plans: PlanSummary[];
  telemetry: TelemetrySample[];
  alerts: AlertGroup[];
  health: Health;
  paused: PausedStatus[];
};

type ProjectedPoint = {
  x: number;
  y: number;
};

const API_BASE = "http://127.0.0.1:8000";
const MAP_SIZE_PX = 520;
const MAP_PADDING_PX = 40;
const TIMELINE_MIN_S = 0;
const TIMELINE_MAX_S = 120;
const TIMELINE_STEP_S = 1;

async function fetchState(timeS: number): Promise<ApiState> {
  const response = await fetch(`${API_BASE}/state?timestamp_s=${timeS}&buffer_m=10&lookahead_s=20`);
  if (!response.ok) {
    throw new Error(`State fetch failed: ${response.status}`);
  }
  return response.json();
}

async function sendDroneControl(action: "pause" | "resume", droneId: string, timestampS: number): Promise<void> {
  const response = await fetch(`${API_BASE}/control/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ drone_id: droneId, timestamp_s: timestampS }),
  });
  if (!response.ok) {
    throw new Error(`${action} failed for ${droneId}: ${response.status}`);
  }
}

function mergeTelemetry(previous: TelemetrySample[], incoming: TelemetrySample[]): TelemetrySample[] {
  const telemetryByDrone = new Map(previous.map((sample) => [sample.drone_id, sample]));
  for (const sample of incoming) {
    telemetryByDrone.set(sample.drone_id, sample);
  }
  return [...telemetryByDrone.values()].sort((left, right) => left.drone_id.localeCompare(right.drone_id));
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  return target.closest("button, input, textarea, select, a, summary") !== null;
}

function buildProjection(plans: PlanSummary[], telemetry: TelemetrySample[]) {
  const points = [
    ...plans.flatMap((plan) => plan.waypoints.map((waypoint) => ({ x: waypoint.x, y: waypoint.y }))),
    ...telemetry.map((sample) => ({ x: sample.position[0], y: sample.position[1] })),
  ];

  if (points.length === 0) {
    return {
      project: (x: number, y: number): ProjectedPoint => ({ x, y }),
      spanX: 0,
      spanY: 0,
    };
  }

  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const spanX = Math.max(80, maxX - minX);
  const spanY = Math.max(80, maxY - minY);
  const scale = Math.min(
    (MAP_SIZE_PX - MAP_PADDING_PX * 2) / spanX,
    (MAP_SIZE_PX - MAP_PADDING_PX * 2) / spanY,
  );
  const offsetX = (MAP_SIZE_PX - spanX * scale) / 2;
  const offsetY = (MAP_SIZE_PX - spanY * scale) / 2;

  return {
    project: (x: number, y: number): ProjectedPoint => ({
      x: offsetX + (x - minX) * scale,
      y: MAP_SIZE_PX - (offsetY + (y - minY) * scale),
    }),
    spanX,
    spanY,
  };
}

function AirspaceMap({
  telemetry,
  plans,
  pausedByDrone,
  currentTimeS,
}: {
  telemetry: TelemetrySample[];
  plans: PlanSummary[];
  pausedByDrone: Map<string, PausedStatus>;
  currentTimeS: number;
}) {
  const { project, spanX, spanY } = useMemo(() => buildProjection(plans, telemetry), [plans, telemetry]);

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span className="map-chip">Centered airspace view</span>
        <span className="map-chip">t={currentTimeS.toFixed(1)}s</span>
        <span className="map-chip">
          coverage={spanX.toFixed(0)}m x {spanY.toFixed(0)}m
        </span>
      </div>

      <div className="map-viewport">
        {telemetry.length === 0 ? (
          <div className="empty-state">
            <strong>No telemetry yet.</strong>
            <span>Start the `v2.0` API, or launch everything together with `./run_live_webapps.sh` from the repo root.</span>
          </div>
        ) : (
          <>
            <svg
              className="map-svg"
              width={MAP_SIZE_PX}
              height={MAP_SIZE_PX}
              viewBox={`0 0 ${MAP_SIZE_PX} ${MAP_SIZE_PX}`}
              role="img"
              aria-label="Centered airspace map with trajectories and telemetry"
            >
              {[1, 2, 3, 4].map((step) => {
                const ratio = step / 5;
                const axisPosition = MAP_SIZE_PX * ratio;
                return (
                  <g key={step}>
                    <line className="map-grid-line" x1={axisPosition} x2={axisPosition} y1={0} y2={MAP_SIZE_PX} />
                    <line className="map-grid-line" x1={0} x2={MAP_SIZE_PX} y1={axisPosition} y2={axisPosition} />
                  </g>
                );
              })}

              {plans.map((plan) => {
                const route = plan.waypoints.map((waypoint) => {
                  const point = project(waypoint.x, waypoint.y);
                  return `${point.x},${point.y}`;
                });
                return (
                  <polyline
                    key={`route-${plan.drone_id}`}
                    className={plan.controlled ? "map-route map-route-controlled" : "map-route map-route-unknown"}
                    points={route.join(" ")}
                  />
                );
              })}

              {telemetry.map((drone) => {
                const point = project(drone.position[0], drone.position[1]);
                const paused = pausedByDrone.get(drone.drone_id)?.paused ?? false;
                const pointClass = drone.controlled ? "map-drone-controlled" : "map-drone-unknown";
                const staleClass = drone.stale ? "map-drone-stale" : "";
                return (
                  <g key={drone.drone_id}>
                    {paused && <circle className="map-drone-halo" cx={point.x} cy={point.y} r={13} />}
                    <circle
                      className={`map-drone ${pointClass} ${staleClass}`}
                      cx={point.x}
                      cy={point.y}
                      r={drone.controlled ? 6 : 5}
                    >
                      <title>
                        {drone.drone_id} | z={drone.position[2].toFixed(1)}m | {drone.stale ? "stale telemetry" : "fresh telemetry"}
                      </title>
                    </circle>
                    <text className="map-label" x={point.x + 9} y={point.y - 9}>
                      {drone.drone_id}
                    </text>
                  </g>
                );
              })}
            </svg>

            <div className="map-legend">
              <span className="legend-item">
                <span className="legend-dot legend-dot-controlled" />
                Controlled
              </span>
              <span className="legend-item">
                <span className="legend-dot legend-dot-unknown" />
                Unknown
              </span>
              <span className="legend-item">
                <span className="legend-dot legend-dot-paused" />
                Paused
              </span>
              <span className="legend-item">
                <span className="legend-dot legend-dot-stale" />
                Stale
              </span>
            </div>
          </>
        )}
      </div>

      <p className="map-caption">
        The map auto-centers against the active routes and telemetry envelope so the airspace stays readable instead of collapsing into the top-left corner.
      </p>
    </div>
  );
}

export default function App() {
  const [timeS, setTimeS] = useState(10);
  const [state, setState] = useState<ApiState | null>(null);
  const [error, setError] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [randomControlEnabled, setRandomControlEnabled] = useState(false);
  const [controlBusyDrone, setControlBusyDrone] = useState("");
  const lastRandomActionTimeRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchState(timeS)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setState((previous) => {
          if (!previous) {
            return data;
          }
          return {
            ...data,
            telemetry:
              data.telemetry.length >= data.drone_count ? data.telemetry : mergeTelemetry(previous.telemetry, data.telemetry),
          };
        });
        setError("");
      })
      .catch((fetchError: Error) => {
        if (!cancelled) {
          setError(
            `${fetchError.message}. Start the live stack with ./run_live_webapps.sh, or run the v2.0 API and frontend separately.`,
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [timeS]);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    const timer = window.setInterval(() => {
      setTimeS((current) => Math.min(TIMELINE_MAX_S, current + TIMELINE_STEP_S));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isPlaying]);

  useEffect(() => {
    if (isPlaying && timeS >= TIMELINE_MAX_S) {
      setIsPlaying(false);
    }
  }, [isPlaying, timeS]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (isInteractiveTarget(event.target)) {
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        setIsPlaying((current) => !current);
        return;
      }
      if (event.key.toLowerCase() === "r") {
        setRandomControlEnabled((current) => !current);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const controlledCount = useMemo(() => {
    if (!state) {
      return 0;
    }
    return state.telemetry.filter((sample) => sample.controlled).length;
  }, [state]);

  const controlledStatuses = useMemo(() => {
    return (state?.paused ?? []).filter((item) => item.controlled);
  }, [state]);

  const pausedByDrone = useMemo(() => {
    return new Map(controlledStatuses.map((item) => [item.drone_id, item]));
  }, [controlledStatuses]);

  async function refreshCurrentState() {
    const data = await fetchState(timeS);
    setState((previous) => ({
      ...data,
      telemetry:
        previous && data.telemetry.length < data.drone_count
          ? mergeTelemetry(previous.telemetry, data.telemetry)
          : data.telemetry,
    }));
    setError("");
  }

  async function handleDroneControl(status: PausedStatus) {
    try {
      setControlBusyDrone(status.drone_id);
      await sendDroneControl(status.paused ? "resume" : "pause", status.drone_id, timeS);
      await refreshCurrentState();
    } catch (controlError) {
      setError(controlError instanceof Error ? controlError.message : "Unable to update drone control state.");
    } finally {
      setControlBusyDrone("");
    }
  }

  useEffect(() => {
    if (!isPlaying || !randomControlEnabled || controlledStatuses.length === 0 || controlBusyDrone) {
      return;
    }
    if (Math.round(timeS) % 3 !== 0) {
      return;
    }
    if (lastRandomActionTimeRef.current === timeS) {
      return;
    }

    lastRandomActionTimeRef.current = timeS;
    const target = controlledStatuses[Math.floor(Math.random() * controlledStatuses.length)];
    if (!target) {
      return;
    }

    void handleDroneControl(target);
  }, [controlBusyDrone, controlledStatuses, isPlaying, randomControlEnabled, timeS]);

  useEffect(() => {
    if (!randomControlEnabled) {
      lastRandomActionTimeRef.current = null;
    }
  }, [randomControlEnabled]);

  return (
    <main className="shell">
      <header className="header-card">
        <div className="panel-header">
          <div>
            <h1>FlytBase ATC Console</h1>
            <p>Real-time strategic + in-air deconfliction operator dashboard</p>
          </div>
          <div className="playback-controls">
            <button
              className="control-button"
              type="button"
              title="Toggle timeline playback (Space)"
              onClick={() => setIsPlaying((current) => !current)}
            >
              {isPlaying ? "Pause timeline" : "Play timeline"}
            </button>
            <button
              className={`control-button ${randomControlEnabled ? "random-active" : "secondary"}`}
              type="button"
              title="Toggle random drone pause/resume mode (R)"
              aria-label={
                randomControlEnabled
                  ? "Disable random drone pause and resume mode"
                  : "Enable random drone pause and resume mode"
              }
              onClick={() => setRandomControlEnabled((current) => !current)}
            >
              {randomControlEnabled ? "Random drone mode on" : "Random drone mode (R)"}
            </button>
            <button className="control-button secondary" type="button" onClick={() => void refreshCurrentState()}>
              Refresh now
            </button>
          </div>
        </div>

        <div className="controls">
          <div className="slider-row">
            <label htmlFor="time">Time: {timeS.toFixed(1)}s</label>
            <span className="muted">
              {randomControlEnabled
                ? "Random operator demo toggles a controlled drone every 3s while playback runs. Press R to stop."
                : isPlaying
                  ? "Live playback running. Press Space to pause."
                  : "Manual timeline scrub. Press Space to play or R for random drone control."}
            </span>
          </div>
          <input
            id="time"
            type="range"
            min={TIMELINE_MIN_S}
            max={TIMELINE_MAX_S}
            step={TIMELINE_STEP_S}
            value={timeS}
            onChange={(event) => setTimeS(Number(event.target.value))}
          />
        </div>
      </header>

      {error && <section className="panel error">{error}</section>}
      {!state && !error && <section className="panel">Loading live airspace state...</section>}

      <section className="metrics-grid">
        <article className="panel metric">
          <h2>Drones</h2>
          <strong>{state?.drone_count ?? 0}</strong>
          <span>{controlledCount} controlled</span>
        </article>
        <article className="panel metric">
          <h2>Alerts</h2>
          <strong>{state?.alerts.length ?? 0}</strong>
          <span>Grouped, prioritized</span>
        </article>
        <article className="panel metric">
          <h2>Health</h2>
          <strong>{state?.health.status ?? "unknown"}</strong>
          <span>{state?.health.compute_latency_ms ?? 0} ms latency</span>
        </article>
        <article className="panel metric">
          <h2>Paused</h2>
          <strong>{controlledStatuses.filter((item) => item.paused).length}</strong>
          <span>Operator-managed drones</span>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel map-panel">
          <h3>Airspace Map</h3>
          <AirspaceMap
            telemetry={state?.telemetry ?? []}
            plans={state?.plans ?? []}
            pausedByDrone={pausedByDrone}
            currentTimeS={state?.time_s ?? timeS}
          />
        </article>

        <article className="panel">
          <h3>Active Alerts</h3>
          <ul>
            {(state?.alerts ?? []).map((alert) => (
              <li key={alert.group_id}>
                <div className="row">
                  <span className={`pill ${alert.highest_severity}`}>{alert.highest_severity}</span>
                  <strong>{alert.drone_ids.join(" vs ")}</strong>
                </div>
                <div className="muted">
                  t={alert.earliest_time_s.toFixed(1)}s | confidence={alert.confidence.toFixed(2)} | actionable=
                  {String(alert.actionable)}
                </div>
                <div className="muted">{alert.suggested_actions.join(" | ")}</div>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h3>Pause / Resume Controls</h3>
          <div className="drone-control-list">
            {controlledStatuses.map((status) => (
              <div className="drone-control-row" key={status.drone_id}>
                <div>
                  <strong>{status.drone_id}</strong>
                  <div className="muted">
                    paused={String(status.paused)} | duration={status.paused_duration_s.toFixed(1)}s
                  </div>
                  {status.warning && <div className="warning-text">Paused too long, review this drone first.</div>}
                </div>
                <button
                  className={`control-button ${status.paused ? "secondary" : ""}`}
                  type="button"
                  disabled={controlBusyDrone === status.drone_id}
                  onClick={() => void handleDroneControl(status)}
                >
                  {controlBusyDrone === status.drone_id ? "Updating..." : status.paused ? "Resume drone" : "Pause drone"}
                </button>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h3>Telemetry Samples</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Drone</th>
                  <th>X</th>
                  <th>Y</th>
                  <th>Z</th>
                  <th>Controlled</th>
                  <th>Stale</th>
                </tr>
              </thead>
              <tbody>
                {(state?.telemetry ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={6}>No telemetry samples received yet. Start the live backend first.</td>
                  </tr>
                ) : (
                  (state?.telemetry ?? []).slice(0, 30).map((sample) => (
                    <tr key={`${sample.drone_id}-${sample.timestamp_s}`}>
                      <td>{sample.drone_id}</td>
                      <td>{sample.position[0].toFixed(1)}</td>
                      <td>{sample.position[1].toFixed(1)}</td>
                      <td>{sample.position[2].toFixed(1)}</td>
                      <td>{String(sample.controlled)}</td>
                      <td>{String(sample.stale)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
  );
}
