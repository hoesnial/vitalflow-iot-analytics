"""Pure session playback state for the archived replay timing experiment."""

from bisect import bisect_right
from dataclasses import dataclass, replace
from itertools import accumulate


@dataclass(frozen=True)
class Replay:
    visible: int = 0
    elapsed: float = 0
    started_at: float | None = None

    @property
    def running(self) -> bool:
        return self.started_at is not None

    def tick(self, schedule: tuple[float, ...], now: float) -> "Replay":
        if not self.running:
            return self
        elapsed = self.elapsed + max(0.0, now - self.started_at)
        visible = max(self.visible, bisect_right(schedule, elapsed))
        if visible == len(schedule):
            return Replay(visible, schedule[-1])
        return replace(self, visible=visible)

    def start(self, schedule: tuple[float, ...], now: float) -> "Replay":
        if self.running or self.visible == len(schedule):
            return self
        return replace(self, started_at=now).tick(schedule, now)

    def pause(self, schedule: tuple[float, ...], now: float) -> "Replay":
        if not self.running:
            return self
        updated = self.tick(schedule, now)
        if not updated.running:
            return updated
        return Replay(updated.visible, self.elapsed + max(0.0, now - self.started_at))

    def step(self, schedule: tuple[float, ...], now: float) -> "Replay":
        current = self.pause(schedule, now)
        visible = min(current.visible + 1, len(schedule))
        return Replay(visible, schedule[visible - 1])


def schedule_for(batches: list[dict]) -> tuple[float, ...]:
    return tuple(accumulate((batch["arrival_interval_ms"] or 0) / 1000 for batch in batches))
