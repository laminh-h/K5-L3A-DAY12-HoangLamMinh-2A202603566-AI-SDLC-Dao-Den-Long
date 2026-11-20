"""Claude Code Stop hook: block the agent from finishing while tests or scenarios are red.

Exit 2 + stderr => Claude Code refuses to stop and shows the failure to the agent.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    payload = json.load(sys.stdin)
except ValueError:
    payload = {}
if payload.get("stop_hook_active"):
    sys.exit(0)  # already blocked once this turn; avoid infinite loop

checks = [
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
    [sys.executable, "tools/run_scenarios.py"]  # default phase = current (phase-4),
]
for cmd in checks:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr)[-2500:]
        print("Checks are RED, fix before finishing:\n$ %s\n%s" % (" ".join(cmd[1:]), tail),
              file=sys.stderr)
        sys.exit(2)
sys.exit(0)
