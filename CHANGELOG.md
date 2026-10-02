# Changelog

## 0.1.0 - 2026-10-02

First release.

- `flakehunt run`: repeat any test command N times, read the JUnit XML each run writes, and
  report flaky tests with failure rate, per-run strip, normalised failure messages and a
  suspected-cause hint. Console, JSON and Markdown output.
- Always-failing pytest tests are re-run alone to separate genuinely broken tests from
  order-dependent ones.
- `flakehunt why` (pytest): classify a test as intrinsically flaky, order-dependent, or
  unreproduced; for order-dependent tests, delta debugging finds the minimal set of earlier
  tests that makes it fail, with a one-line reproduce command.
- `flakehunt demo`: bundled project with planted flakiness.
