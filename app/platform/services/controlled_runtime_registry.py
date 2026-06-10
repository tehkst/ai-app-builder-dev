from __future__ import annotations

import subprocess
from typing import Dict


RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}
