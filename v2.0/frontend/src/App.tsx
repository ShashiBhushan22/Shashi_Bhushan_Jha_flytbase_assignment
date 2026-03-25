import { useEffect, useMemo, useState } from "react";

type TelemetrySample = {
  drone_id: string;
  timestamp_s: number;
  position: [number, number, number];
  controlled: boolean;
  stale: boolean;
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

type ApiState = {
  time_s: number;
  drone_count: number;
  telemetry: TelemetrySample[];
  alerts: AlertGroup[];
  health: Health;
  paused: Array<Record<string, unknown>>;
};

const API_BASE = "http://127.0.0.1:8000";

async function fetchState(timeS: number): Promise<ApiState> {
  const response = await fetch(`${API_BASE}/state?timestamp_s=${timeS}&buffer_m=10&lookahead_s=20`);
  if (!response.ok) {
    throw new Error(`State fetch failed: ${response.status}`);
  }
  return response.json();
}

export default function App() {
  const [timeS, setTimeS] = useState(10);
  const [state, setState] = useState<ApiState | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    fetchState(timeS)
      .then((data) => {
        setState(data);
        setError("");
      })
      .catch((e: Error) => setError(e.message));
  }, [timeS]);

  useEffect(() => {
    const socket = new WebSocket("ws://127.0.0.1:8000/ws/telemetry");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as Partial<ApiState>;
      setState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          ...payload,
          telemetry: payload.telemetry ?? prev.telemetry,
          alerts: payload.alerts ?? prev.alerts,
          health: payload.health ?? prev.health,
          paused: payload.paused ?? prev.paused,
        } as ApiState;
      });
    };
    socket.onerror = () => setError("WebSocket disconnected; using on-demand refresh only.");
    return () => socket.close();
  }, []);

  const controlledCount = useMemo(() => {
    if (!state) return 0;
    return state.telemetry.filter((sample) => sample.controlled).length;
  }, [state]);

  return (
    <main className="shell">
      <header className="header-card">
        <h1>FlytBase ATC Console</h1>
        <p>Real-time strategic + in-air deconfliction operator dashboard</p>
        <div className="controls">
          <label htmlFor="time">Time: {timeS.toFixed(1)}s</label>
          <input
            id="time"
            type="range"
            min={0}
            max={120}
            step={1}
            value={timeS}
            onChange={(event) => setTimeS(Number(event.target.value))}
          />
        </div>
      </header>

      {error && <section className="panel error">{error}</section>}

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
          <h2>Pair Checks</h2>
          <strong>{state?.health.pair_checks ?? 0}</strong>
          <span>{state?.health.checks_per_second ?? 0}/s</span>
        </article>
      </section>

      <section className="content-grid">
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
                  t={alert.earliest_time_s.toFixed(1)}s | confidence={alert.confidence.toFixed(2)} | actionable={String(alert.actionable)}
                </div>
              </li>
            ))}
          </ul>
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
                {(state?.telemetry ?? []).slice(0, 30).map((sample) => (
                  <tr key={`${sample.drone_id}-${sample.timestamp_s}`}>
                    <td>{sample.drone_id}</td>
                    <td>{sample.position[0].toFixed(1)}</td>
                    <td>{sample.position[1].toFixed(1)}</td>
                    <td>{sample.position[2].toFixed(1)}</td>
                    <td>{String(sample.controlled)}</td>
                    <td>{String(sample.stale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
  );
}
