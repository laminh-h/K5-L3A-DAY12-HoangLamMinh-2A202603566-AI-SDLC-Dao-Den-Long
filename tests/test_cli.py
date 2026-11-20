"""CLI tests: run the real headless_cmd from game.contract.json as a subprocess."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from lantern import config

ROOT = config.ROOT


def cli(*args):
    cmd = [sys.executable, "-m", "lantern.headless", *args]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def path(self, name, obj=None, raw=None):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(raw if raw is not None else json.dumps(obj))
        return p

    def test_contract_file(self):
        with open(config.CONTRACT_PATH, encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.0")
        self.assertEqual(c["tuning"]["lantern_count_night1"], 5)
        for k in ("build_cmd", "run_cmd", "headless_cmd", "team"):
            self.assertTrue(c[k])

    def test_ok_run_and_jsonl(self):
        out = os.path.join(self.tmp, "o.jsonl")
        r = cli("--seed", "3", "--night", "1", "--ticks", "120", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]
        self.assertEqual(lines[0]["type"], "snapshot")
        self.assertEqual(lines[-1]["type"], "end")

    def test_deterministic_files(self):
        a, b = os.path.join(self.tmp, "a.jsonl"), os.path.join(self.tmp, "b.jsonl")
        for o in (a, b):
            cli("--seed", "9", "--night", "1", "--ticks", "2000", "--out", o)
        with open(a, "rb") as fa, open(b, "rb") as fb:
            self.assertEqual(fa.read(), fb.read())

    def test_bad_json_exit_2(self):
        p = self.path("bad.json", raw="{not json")
        r = cli("--seed", "1", "--night", "1", "--ticks", "5", "--inputs", p,
                "--out", os.path.join(self.tmp, "x.jsonl"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("error", r.stderr)

    def test_non_increasing_ticks_exit_2(self):
        p = self.path("i.json", {"frames": [{"tick": 5}, {"tick": 5}]})
        r = cli("--seed", "1", "--night", "1", "--ticks", "5", "--inputs", p,
                "--out", os.path.join(self.tmp, "x.jsonl"))
        self.assertEqual(r.returncode, 2)

    def test_bad_scenario_exit_2(self):
        p = self.path("s.json", {"lanterns": [{"id": "L9"}]})
        r = cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", p,
                "--out", os.path.join(self.tmp, "x.jsonl"))
        self.assertEqual(r.returncode, 2)

    def test_missing_args_nonzero(self):
        self.assertNotEqual(cli("--seed", "1").returncode, 0)


if __name__ == "__main__":
    unittest.main()
