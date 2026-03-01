import time
from typing import Iterator


class PollScheduler:
    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds

    def intervals(self) -> Iterator[int]:
        """Yield sleep durations for polling loop."""
        while True:
            yield self.interval
