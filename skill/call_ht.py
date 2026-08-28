#!/usr/bin/env python3
"""Minimal client the skill runs: POST inputs to the HT Highlighter service and
print the JSON response. Uses only stdlib so it runs anywhere."""
import argparse
import json
import os
import urllib.request

p = argparse.ArgumentParser()
p.add_argument("--domain", required=True)
p.add_argument("--contact", default="")
p.add_argument("--mode", default="person", choices=["person", "general"])
args = p.parse_args()

base = os.environ.get("HT_ENDPOINT", "http://localhost:8000").rstrip("/")
payload = json.dumps({
    "domain": args.domain,
    "contact": args.contact or None,
    "mode": args.mode,
}).encode()

req = urllib.request.Request(
    base + "/research", data=payload,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=180) as r:
    print(r.read().decode())
