# FlytBase Assignment V1.0

## Scope

Implements strategic pre-flight deconfliction for waypoint missions with spatial and temporal conflict checks.

- Spatial safety buffer checks.
- Temporal overlap checks.
- Conflict explanation (where, when, and with which drone).
- Scenario plotting outputs for demo video frames.
- Optional altitude-aware 3D waypoints and 4D replay-style visualization outputs.

## Structure

- `src/models.py`: mission and conflict data models.
- `src/deconfliction.py`: main query interface (`check_mission`).
- `src/scenarios.py`: sample conflict and non-conflict missions.
- `src/visualization.py`: plot generator for assignment demonstrations.
- `tests/test_deconfliction.py`: core behavior tests.

## Setup

```bash
cd /home/bhushan-arc/flytbase/v1.0
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Run

```bash
cd /home/bhushan-arc/flytbase/v1.0
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

## Generate demonstration plots

```bash
cd /home/bhushan-arc/flytbase/v1.0/src
python visualization.py
```

Interactive visualization files are written to `src/plots/` as `.html` artifacts by default.

Generated artifacts include:

- `conflict_case.html` for the 2D overview,
- `conflict_case_3d.html` for altitude-aware airspace view,
- `conflict_case_4d.html` for animated 3D + time playback.

## Query interface example

```python
from deconfliction import check_mission
from scenarios import basic_conflict_case

primary, others = basic_conflict_case()
status, conflicts = check_mission(primary, others, safety_buffer_m=10.0)
```

This returns:

- `status`: `"clear"` or `"conflict detected"`
- `conflicts`: list of conflict explanations including time, location, and offending drone
