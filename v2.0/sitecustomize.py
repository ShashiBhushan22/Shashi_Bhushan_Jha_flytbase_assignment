from __future__ import annotations

import os

# Avoid unrelated globally installed pytest plugins (e.g., ROS) from breaking local test runs.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
os.environ.setdefault(
	"PYTEST_ADDOPTS",
	"-p no:launch_testing -p no:launch_testing_ros_pytest_entrypoint",
)
