from pathlib import Path

import pytest

from flakehunt.analyze import (
    BROKEN,
    FLAKY,
    STABLE,
    analyse,
    fingerprint,
    hint_for,
    miss_probability,
)
from flakehunt.junit import parse_junit

XML = """<?xml version="1.0"?>
<testsuites><testsuite name="s">
  <testcase classname="a.b" name="ok" time="0.01"/>
  <testcase classname="a.b" name="bad" time="0.02"><failure message="boom 42">trace</failure></testcase>
  <testcase classname="a.b" name="err"><error message="">ValueError: nope</error></testcase>
  <testcase classname="a.b" name="skip"><skipped message="why"/></testcase>
</testsuite></testsuites>"""


def test_parse_outcomes(tmp_path: Path):
    f = tmp_path / "r.xml"
    f.write_text(XML)
    cases = {c.name: c for c in parse_junit(str(f))}
    assert cases["ok"].outcome == "pass"
    assert cases["bad"].outcome == "fail" and cases["bad"].message == "boom 42"
    assert cases["err"].outcome == "fail" and cases["err"].message == "ValueError: nope"
    assert cases["skip"].outcome == "skip"
    assert cases["ok"].id == "a.b.ok"


def test_parse_glob_and_missing(tmp_path: Path):
    (tmp_path / "a.xml").write_text(XML)
    (tmp_path / "b.xml").write_text(XML)
    assert len(parse_junit(str(tmp_path / "*.xml"))) == 4
    assert parse_junit(str(tmp_path / "nothing*.xml")) == []


def test_invalid_xml_is_a_clear_error(tmp_path: Path):
    f = tmp_path / "bad.xml"
    f.write_text("<not xml")
    with pytest.raises(ValueError, match="not valid JUnit XML"):
        parse_junit(str(f))


def _run(*pairs):
    from flakehunt.junit import Case

    return [Case(f"t.{n}", "t", n, o, m) for n, o, m in pairs]


def test_classification():
    runs = [
        _run(("steady", "pass", ""), ("flip", "fail", "Connection refused"), ("dead", "fail", "x")),
        _run(("steady", "pass", ""), ("flip", "pass", ""), ("dead", "fail", "x")),
        _run(("steady", "pass", ""), ("flip", "pass", ""), ("dead", "fail", "x")),
    ]
    by = {s.id: s for s in analyse(runs)}
    assert by["t.steady"].status == STABLE
    assert by["t.flip"].status == FLAKY and by["t.flip"].fails == 1
    assert by["t.flip"].rate == pytest.approx(1 / 3)
    assert by["t.dead"].status == BROKEN
    assert by["t.flip"].hint and by["t.flip"].hint[0] == "network or service startup"


def test_fingerprint_collapses_volatile_parts():
    a = fingerprint("fail at 0x7f3a1c in /tmp/pytest-1234/x took 0.412s")
    b = fingerprint("fail at 0x99ab in /tmp/pytest-9/y took 3.1s")
    assert a == b


def test_hint_priority_and_none():
    assert hint_for(["Address already in use"])[0] == "port collision"
    assert hint_for(["assert 1 == 2"]) is None


def test_miss_probability():
    assert miss_probability(0.5, 1) == 0.5
    assert miss_probability(0.1, 10) == pytest.approx(0.3487, abs=1e-3)
