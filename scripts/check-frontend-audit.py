#!/usr/bin/env python3
"""Fail closed on Yarn audit errors; block critical production dependency advisories."""
import json
import subprocess
import sys

cmd = ["yarn", "audit", "--json", "--groups", "dependencies"]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
counts = {level: 0 for level in ("info", "low", "moderate", "high", "critical")}
summary = None
parse_errors = 0
for line in result.stdout.splitlines():
    if not line.strip():
        continue
    try:
        item = json.loads(line)
    except json.JSONDecodeError:
        parse_errors += 1
        continue
    if item.get("type") == "auditSummary":
        summary = item.get("data", {}).get("vulnerabilities")
if result.stderr:
    print(result.stderr[-3000:], file=sys.stderr)
if parse_errors or not isinstance(summary, dict):
    sys.exit("Audit failed: missing/invalid structured summary")
for level in counts:
    value = summary.get(level)
    if not isinstance(value, int) or value < 0:
        sys.exit(f"Audit failed: missing/invalid count for {level}")
    counts[level] = value
print("Production dependency audit:", counts)
if counts["critical"]:
    sys.exit(f"Blocking {counts['critical']} critical dependency advisories")
# Yarn 1 audit uses a severity bitmask as its exit code; nonzero for lower levels.
# Accept only that documented bitmask; unexpected failures remain blocking.
expected = sum(bit for name, bit in (("info", 1), ("low", 2), ("moderate", 4), ("high", 8), ("critical", 16)) if counts[name])
if result.returncode != expected:
    sys.exit(f"Audit failed: unexpected exit status {result.returncode} (expected {expected})")
print("PASS: no critical production dependency advisories")
