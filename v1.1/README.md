# FlytBase Assignment V1.1

## Scope

V1.1 requires continuous trajectory analysis with:

- Constant speed per drone.
- Only departure time provided.
- No precomputed waypoint timestamps.
- Conflict detection computed analytically in continuous time.
- Conflict explanation with exact time/location and minimum distance.
- Optional altitude-aware 3D paths and 4D replay-style visualization outputs.

## Structure

- `src/models.py`: typed mission and trajectory models.
- `src/trajectory.py`: computes segment timing from path length and speed.
- `src/solver.py`: continuous conflict analysis and report generation.
- `src/scenarios.py`: assignment-ready demonstration scenarios.
- `src/visualization.py`: graph generation for scenario demonstrations.
- `tests/test_continuous_solver.py`: crossing, clear, and mixed-speed tests.

## Setup

```bash
cd /home/bhushan-arc/flytbase/v1.1
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Run

```bash
cd /home/bhushan-arc/flytbase/v1.1
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

## Generate demonstration plots

```bash
cd /home/bhushan-arc/flytbase/v1.1/src
python visualization.py
```

Interactive visualization files are written to `src/plots/` as `.html` artifacts.

Generated artifacts include:

- `crossing_conflict.html` for the 2D overview,
- `crossing_conflict_3d.html` for altitude-aware airspace view,
- `crossing_conflict_4d.html` for animated 3D + time playback.

## Query interface example

```python
from scenarios import crossing_conflict_case
from solver import analyze_mission

primary, others = crossing_conflict_case()
report = analyze_mission(primary, others, buffer_m=10.0)
```

This returns:

- `report.status`: `"clear"` or `"conflict detected"`
- `report.conflicts`: list of exact conflict details
