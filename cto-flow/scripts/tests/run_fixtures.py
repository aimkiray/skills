#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑完 scripts/tests/fixtures/ 下全部夹具，核对退出码与首个违规规则。

每个夹具目录含：
  report.md     被测报告
  manifest.txt  期望文件清单
  expect.txt    期望：exit=<0|1>、first_rule=<规则名>、rules=<逗号分隔的规则集合>

用法：python -B scripts/tests/run_fixtures.py [--verbose]
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "cto_verify.py")
FIXTURES = os.path.join(HERE, "fixtures")


def parse_expect(path):
    data = {}
    with open(path, "r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep:
                data[key.strip()] = value.strip()
    return data


def main(argv=None):
    verbose = "--verbose" in (argv if argv is not None else sys.argv[1:])
    names = sorted(
        n
        for n in os.listdir(FIXTURES)
        if os.path.isdir(os.path.join(FIXTURES, n))
    )
    rows = []
    ok_count = 0
    for name in names:
        base = os.path.join(FIXTURES, name)
        report = os.path.join(base, "report.md")
        manifest = os.path.join(base, "manifest.txt")
        expect = parse_expect(os.path.join(base, "expect.txt"))
        cmd = [sys.executable, "-B", TOOL, "--report", report]
        if os.path.isfile(manifest):
            cmd += ["--manifest", manifest]
        cmd += ["--json"]
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"  # 不产生 scripts/__pycache__
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", env=env
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            rows.append((name, proc.returncode, "<bad-json>", "", False,
                         proc.stdout + proc.stderr))
            continue
        violations = payload["reports"][0]["violations"]
        errors = [v for v in violations if v["severity"] == "ERROR"]
        first_rule = errors[0]["rule"] if errors else ""
        actual_rules = sorted({v["rule"] for v in errors})
        expected_exit = int(expect.get("exit", "0"))
        expected_first = expect.get("first_rule", "")
        expected_rules = [r for r in expect.get("rules", "").split(",") if r]
        ok = proc.returncode == expected_exit
        if expected_first and first_rule != expected_first:
            ok = False
        for rule in expected_rules:
            if rule not in actual_rules:
                ok = False
        ok_count += 1 if ok else 0
        rows.append((name, proc.returncode, first_rule, expected_first, ok,
                     ",".join(actual_rules)))

    width = max([len(r[0]) for r in rows] + [7])
    print("%-*s | exit | first-rule            | expected              | ok" % (width, "fixture"))
    print("-" * (width + 62))
    for name, code, first, expected_first, ok, actual in rows:
        print("%-*s |  %d   | %-22s | %-21s | %s" % (width, name, code, first, expected_first, "OK" if ok else "FAIL"))
        if verbose and not ok:
            print("    actual rules: %s" % actual)
    print("FIXTURES %d/%d passed" % (ok_count, len(rows)))
    return 0 if ok_count == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
