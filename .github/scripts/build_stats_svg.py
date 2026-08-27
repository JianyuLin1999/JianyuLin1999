#!/usr/bin/env python3
"""Render contribution stats SVGs from the GitHub GraphQL contribution calendar.

Data source is the same calendar that powers the official profile heatmap,
so every number matches what visitors see on the profile page.
"""
import json
import os
import subprocess

USER = os.environ.get("TARGET_USER", "JianyuLin1999")
OUT_DIR = os.environ.get("OUT_DIR", "assets")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

raw = subprocess.run(
    ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={USER}"],
    capture_output=True, text=True, check=True,
).stdout
cal = json.loads(raw)["data"]["user"]["contributionsCollection"]["contributionCalendar"]

days = [d for w in cal["weeks"] for d in w["contributionDays"]]
counts = [d["contributionCount"] for d in days]
total = cal["totalContributions"]
active = sum(1 for c in counts if c > 0)
best = max(days, key=lambda d: d["contributionCount"])
avg = total / max(len(days), 1)

longest = run = 0
for c in counts:
    run = run + 1 if c > 0 else 0
    longest = max(longest, run)

# Current streak: today may still be in progress, so a trailing zero is skipped once.
i = len(counts) - 1
if i >= 0 and counts[i] == 0:
    i -= 1
current = 0
while i >= 0 and counts[i] > 0:
    current += 1
    i -= 1

weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
peak = max(weekly) if weekly else 0

PALETTES = {
    "light": {"fg": "#24292f", "muted": "#57606a", "accent": "#1a7f37", "bar": "#40c463", "grid": "#d0d7de"},
    "dark": {"fg": "#e6edf3", "muted": "#8b949e", "accent": "#3fb950", "bar": "#26a641", "grid": "#30363d"},
}

W, H = 880, 200
CHART_X, CHART_W, CHART_Y, CHART_H = 400, 450, 40, 110  # bar chart box, baseline at CHART_Y+CHART_H


def render(p):
    bars = []
    n = len(weekly)
    if n and peak:
        bw = CHART_W / n
        for k, v in enumerate(weekly):
            h = 0 if peak == 0 else (v / peak) * CHART_H
            x = CHART_X + k * bw
            bars.append(
                f'<rect x="{x:.1f}" y="{CHART_Y + CHART_H - h:.1f}" width="{max(bw - 2, 1):.1f}" '
                f'height="{max(h, 0.5):.1f}" rx="1.5" fill="{p["bar"]}" />'
            )
    first, last = days[0]["date"], days[-1]["date"]
    stats = [
        (f"{best['contributionCount']}", f"busiest day · {best['date']}"),
        (f"{active}/{len(days)}", "active days"),
        (f"{avg:.1f}", "per-day average"),
        (f"{current} d", "current streak"),
        (f"{longest} d", "longest streak"),
    ]
    cols = []
    for k, (num, label) in enumerate(stats):
        x = 30 + (k % 3) * 123
        y = 148 if k < 3 else 183
        if k >= 3:
            x = 30 + (k - 3) * 123
        cols.append(
            f'<text x="{x}" y="{y}" font-size="17" font-weight="600" fill="{p["accent"]}">{num}</text>'
            f'<text x="{x}" y="{y + 15}" font-size="11" fill="{p["muted"]}">{label}</text>'
        )
    font = "font-family=\"'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif\""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + 20}" viewBox="0 0 {W} {H + 20}">
<g {font}>
  <text x="30" y="72" font-size="52" font-weight="700" fill="{p['fg']}">{total:,}</text>
  <text x="30" y="98" font-size="14" fill="{p['muted']}">contributions · {first} → {last}</text>
  {''.join(cols)}
  <line x1="{CHART_X}" y1="{CHART_Y + CHART_H + 0.5}" x2="{CHART_X + CHART_W}" y2="{CHART_Y + CHART_H + 0.5}" stroke="{p['grid']}" stroke-width="1" />
  {''.join(bars)}
  <text x="{CHART_X}" y="{CHART_Y + CHART_H + 22}" font-size="11" fill="{p['muted']}">weekly contributions · peak {peak}</text>
  <text x="{CHART_X + CHART_W}" y="{CHART_Y - 12}" font-size="11" text-anchor="end" fill="{p['muted']}">same data as the official heatmap</text>
</g>
</svg>"""


os.makedirs(OUT_DIR, exist_ok=True)
for name, palette in PALETTES.items():
    path = os.path.join(OUT_DIR, f"stats-{name}.svg")
    with open(path, "w") as f:
        f.write(render(palette))
    print(f"wrote {path}")
print(f"total={total} active={active} best={best['date']}:{best['contributionCount']} current={current} longest={longest} peak_week={peak}")
