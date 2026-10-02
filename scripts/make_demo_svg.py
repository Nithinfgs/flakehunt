"""Render a real `flakehunt demo` run as an animated terminal SVG (docs/assets/demo.svg).

Usage:  .venv/bin/python scripts/make_demo_svg.py
The text comes from actually running the tool; nothing is hand-written.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
COLORS = {"31": "#ff7b72", "32": "#7ee787", "33": "#e3b341", "36": "#79c0ff", "2": "#6e7681"}
FG, BG = "#c9d1d9", "#0d1117"
CHAR_W, LINE_H, PAD = 7.9, 20, 18
ANSI = re.compile(r"\033\[([0-9;]*)m")


def spans(line: str) -> str:
    out, style, pos = [], {"color": None, "bold": False}, 0
    for m in ANSI.finditer(line):
        out.append((line[pos : m.start()], dict(style)))
        pos = m.end()
        code = m.group(1)
        if code in ("0", ""):
            style = {"color": None, "bold": False}
        elif code == "1":
            style["bold"] = True
        elif code in COLORS:
            style["color"] = COLORS[code]
    out.append((line[pos:], dict(style)))
    parts = []
    for text, st in out:
        if not text:
            continue
        attrs = f' fill="{st["color"]}"' if st["color"] else ""
        if st["bold"]:
            attrs += ' font-weight="700"'
        parts.append(f"<tspan{attrs}>{html.escape(text)}</tspan>")
    return "".join(parts)


def build(lines: list[str], out: Path) -> None:
    plain = [ANSI.sub("", ln) for ln in lines]
    width = int(max(len(p) for p in plain) * CHAR_W + 2 * PAD)
    height = PAD * 2 + LINE_H * len(lines) + 24
    # reveal schedule: each line appears in turn; a pause before the `why` section
    total = 6.0 + 0.16 * len(lines) + 5.0
    t, times = 0.4, []
    for i in range(len(plain)):
        if i == 1:
            t += 1.4  # pause after the typed command
        times.append(t)
        t += 0.16
    rows = []
    for i, ln in enumerate(lines):
        y = PAD + 14 + i * LINE_H + 22
        k = times[i] / total
        rows.append(
            f'<text x="{PAD}" y="{y}" opacity="0" style="white-space:pre">{spans(ln)}'
            f'<animate attributeName="opacity" dur="{total:.1f}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="0;{k:.4f};0.97;1" values="0;1;0;0"/></text>'
        )
    dots = "".join(
        f'<circle cx="{PAD + 7 + i * 20}" cy="18" r="6" fill="{c}"/>'
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f"))
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="flakehunt demo terminal output">'
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>{dots}'
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="13" '
        f'fill="{FG}" xml:space="preserve">{"".join(rows)}</g></svg>'
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out.name} ({len(svg) // 1024} KB, {len(lines)} lines)")


def main() -> None:
    env = dict(os.environ, FORCE_COLOR="1", PATH=f"{ROOT / '.venv/bin'}:{os.environ['PATH']}")
    env.pop("NO_COLOR", None)
    proc = subprocess.run(
        [sys.executable, "-m", "flakehunt", "demo"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    lines = proc.stdout.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    split = next(i for i, ln in enumerate(lines) if ANSI.sub("", ln).startswith("flakehunt why"))
    dim_prompt = "\033[2m$\033[0m "
    hunt = [dim_prompt + "flakehunt demo", *lines[: split - 1]]
    why_cmd = "flakehunt why tests/test_settings.py::test_default_timeout_is_30s"
    why = [dim_prompt + why_cmd, *lines[split:]]
    build(hunt, ASSETS / "demo.svg")
    build(why, ASSETS / "why.svg")


if __name__ == "__main__":
    main()
