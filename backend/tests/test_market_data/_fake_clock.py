"""Test-only controllable clock, shared by the simulator and Massive client
test suites so history-downsampling cadence can be tested deterministically
without real sleeps."""

from __future__ import annotations


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds
