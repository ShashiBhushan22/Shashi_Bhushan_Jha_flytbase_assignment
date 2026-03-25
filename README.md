# FlytBase Assignment Repository Layout

This folder is organized by assignment version:

- `v1.0/`: Strategic deconfliction baseline.
- `v1.1/`: Continuous trajectory analysis with constant velocity and computed timings.
- `v2.0/`: Real-time ATC-oriented extension (telemetry simulator + dashboard flow).

## Notes

- Each version folder is independent and can be developed as a separate branch target.

## Quick run commands

V1.0:

```bash
cd /home/bhushan-arc/flytbase/v1.0
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
cd src && python visualization.py
```

V1.1:

```bash
cd /home/bhushan-arc/flytbase/v1.1
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
cd src && python visualization.py
```

V2.0 (fullstack):

```bash
cd /home/bhushan-arc/flytbase/v2.0
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
streamlit run app.py
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

```bash
cd /home/bhushan-arc/flytbase/v2.0/frontend
npm install
npm run dev
```

V2.0 benchmark sweep:

```bash
cd /home/bhushan-arc/flytbase/v2.0
python scripts/benchmark_load.py
```

## Run everything sequentially

```bash
cd /home/bhushan-arc/flytbase
./run_all_versions.sh
```
