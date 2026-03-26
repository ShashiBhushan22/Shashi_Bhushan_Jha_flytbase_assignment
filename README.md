# FlytBase Assignment Repository Layout

This folder is organized by assignment version:

- `v1.0/`: Strategic deconfliction baseline.
- `v1.1/`: Continuous trajectory analysis with constant velocity and computed timings.
- `v2.0/`: Real-time ATC-oriented extension (telemetry simulator + dashboard flow).

## Notes

- Each version folder is independent and can be developed as a separate branch target.

## Development note

AI assistance was used selectively for drafting, scaffolding, and documentation cleanup. Final logic, tests, and runnable outputs were reviewed and validated locally in this repository.

## Verification status

Verified in this workspace on March 26, 2026:

- `v1.0` tests passed
- `v1.1` tests passed
- `v2.0` tests passed
- `v2.0/frontend` production build passed

## Shared workspace setup

These commands work in this repo as checked on March 26, 2026:

```bash
cd /home/bhushan-arc/flytbase
python3 -m venv .venv
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r v1.0/requirements.txt -r v1.1/requirements.txt -r v2.0/requirements.txt
./.venv/bin/pip install -e ./v2.0
cd v2.0/frontend
npm install
```

## Quick run commands

Use the shared root interpreter instead of assuming a global `python` binary exists.

V1.0:

```bash
cd /home/bhushan-arc/flytbase
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -q v1.0/tests
cd v1.0/src && ../../.venv/bin/python visualization.py
```

Outputs:

- `v1.0/src/plots/conflict_case.html`
- `v1.0/src/plots/conflict_case_3d.html`
- `v1.0/src/plots/conflict_case_4d.html`

V1.1:

```bash
cd /home/bhushan-arc/flytbase
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -q v1.1/tests
cd v1.1/src && ../../.venv/bin/python visualization.py
```

Outputs:

- `v1.1/src/plots/crossing_conflict.html`
- `v1.1/src/plots/crossing_conflict_3d.html`
- `v1.1/src/plots/crossing_conflict_4d.html`

V2.0 (fullstack):

```bash
cd /home/bhushan-arc/flytbase/v2.0
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/python -m pytest -q
../.venv/bin/python -m streamlit run app.py
../.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

```bash
cd /home/bhushan-arc/flytbase/v2.0/frontend
npm install
npm run dev
```

V2.0 benchmark sweep:

```bash
cd /home/bhushan-arc/flytbase/v2.0
../.venv/bin/python scripts/benchmark_load.py
```

V2.0 demo visuals:

```bash
cd /home/bhushan-arc/flytbase/v2.0
../.venv/bin/python scripts/generate_visuals.py
```

Launch both live web apps together:

```bash
cd /home/bhushan-arc/flytbase
./run_live_webapps.sh
```

The live launcher now waits for the Streamlit dashboard and React ATC Console to become reachable, then opens both pages in your default browser automatically. Set `OPEN_BROWSER=0` if you want the script to stay terminal-only.

## Run everything sequentially

```bash
cd /home/bhushan-arc/flytbase
./run_all_versions.sh
```

The sequential runner now opens the generated HTML artifacts for `v1.0`, `v1.1`, and `v2.0` in your browser after they are created. Set `OPEN_BROWSER=0` if you want it to run without opening tabs.
After the sequential checks finish, it also launches the live `v2.0` stack automatically, so the Streamlit ATC dashboard and React ATC Console come up at the end of the run.
Private study notes are expected at `~/flytbase_private_docs` by default and are built there if `repo_code_walkthrough.tex` is present. You can override that location with `PRIVATE_DOCS_DIR=/your/path`.
