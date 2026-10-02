"""Parse JUnit XML, the lowest common denominator of every test runner."""

from __future__ import annotations

import glob
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

PASS, FAIL, SKIP = "pass", "fail", "skip"
MAX_MESSAGE = 300


@dataclass(frozen=True)
class Case:
    id: str
    classname: str
    name: str
    outcome: str
    message: str = ""
    time: float = 0.0


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:MAX_MESSAGE]
    return ""


def _case_from(el: ET.Element) -> Case:
    classname = el.get("classname", "")
    name = el.get("name", "")
    outcome, message = PASS, ""
    for child in el:
        tag = child.tag
        if tag in ("failure", "error"):
            outcome = FAIL
            message = _first_line(child.get("message") or "") or _first_line(child.text or "")
            break
        if tag == "skipped":
            outcome = SKIP
            message = _first_line(child.get("message") or "")
    try:
        elapsed = float(el.get("time", "0") or 0)
    except ValueError:
        elapsed = 0.0
    ident = f"{classname}.{name}" if classname else name
    return Case(ident, classname, name, outcome, message, elapsed)


def parse_file(path: Path) -> list[Case]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"{path}: not valid JUnit XML ({exc})") from exc
    return [_case_from(el) for el in root.iter("testcase")]


def parse_junit(pattern: str) -> list[Case]:
    """Parse every file matching ``pattern`` (a path or glob). Later duplicates win."""
    paths = sorted(glob.glob(pattern, recursive=True))
    if not paths:
        return []
    merged: dict[str, Case] = {}
    for p in paths:
        for case in parse_file(Path(p)):
            merged[case.id] = case
    return list(merged.values())
