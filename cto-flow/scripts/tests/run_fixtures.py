#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑完 scripts/tests/fixtures/ 下全部夹具，核对退出码与首个违规规则。

每个夹具目录含：
  report.md     被测报告
  manifest.txt  期望文件清单（可选；无此文件则不传 --manifest）
  args.txt      可选：每非空非 `#` 行作为一个附加 CLI 参数（如 --kind / impl）
  expect.txt    期望：exit=<0|1>、first_rule=<规则名>、rules=<逗号分隔的规则集合>

用法：python -B scripts/tests/run_fixtures.py [--verbose]（另跑 boundary/ 扁平夹具：<stem>.md + manifests/<stem>.txt + expect/<stem>.txt）
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "cto_verify.py")
FIXTURES = os.path.join(HERE, "fixtures")
BOUNDARY = os.path.join(HERE, "boundary")


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
        extra_args = []
        args_file = os.path.join(base, "args.txt")
        if os.path.isfile(args_file):
            with open(args_file, "r", encoding="utf-8-sig") as fh:
                for raw in fh:
                    arg = raw.strip()
                    if arg and not arg.startswith("#"):
                        extra_args.append(arg)
        expect = parse_expect(os.path.join(base, "expect.txt"))
        cmd = [sys.executable, "-B", TOOL, "--report", report]
        if os.path.isfile(manifest):
            cmd += ["--manifest", manifest]
        cmd += extra_args
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

    # ---- boundary/ 扁平夹具（BOM / 0 字节 / 混合行尾；= --dir 原生形态） ----
    b_rows, b_ok = [], 0
    b_names = []
    if os.path.isdir(BOUNDARY):
        b_names = sorted(
            n[:-3] for n in os.listdir(BOUNDARY)
            if n.endswith(".md") and os.path.isfile(os.path.join(BOUNDARY, n))
        )
    for name in b_names:
        expect = parse_expect(os.path.join(BOUNDARY, "expect", name + ".txt"))
        cmd = [sys.executable, "-B", TOOL, "--report",
               os.path.join(BOUNDARY, name + ".md"), "--json"]
        manifest = os.path.join(BOUNDARY, "manifests", name + ".txt")
        if os.path.isfile(manifest):
            cmd += ["--manifest", manifest]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", env=env
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            b_rows.append((name, proc.returncode, "<bad-json>", "", False,
                           proc.stdout + proc.stderr))
            continue
        errors = [v for v in payload["reports"][0]["violations"]
                  if v["severity"] == "ERROR"]
        first_rule = errors[0]["rule"] if errors else ""
        actual_rules = sorted({v["rule"] for v in errors})
        ok = proc.returncode == int(expect.get("exit", "0"))
        if expect.get("first_rule", "") and first_rule != expect["first_rule"]:
            ok = False
        if any(r not in actual_rules
               for r in expect.get("rules", "").split(",") if r):
            ok = False
        b_ok += 1 if ok else 0
        b_rows.append((name, proc.returncode, first_rule,
                       expect.get("first_rule", ""), ok, ",".join(actual_rules)))
    width = max([len(r[0]) for r in rows + b_rows] + [7])
    print("%-*s | exit | first-rule            | expected              | ok" % (width, "fixture"))
    print("-" * (width + 62))
    for name, code, first, expected_first, ok, actual in rows + b_rows:
        print("%-*s |  %d   | %-22s | %-21s | %s" % (width, name, code, first, expected_first, "OK" if ok else "FAIL"))
        if verbose and not ok:
            print("    actual rules: %s" % actual)
    print("FIXTURES %d/%d passed" % (ok_count, len(rows)))
    print("BOUNDARY %d/%d passed" % (b_ok, len(b_rows)))
    return 0 if (ok_count == len(rows) and b_ok == len(b_rows)) else 1


if __name__ == "__main__":
    sys.exit(main())
