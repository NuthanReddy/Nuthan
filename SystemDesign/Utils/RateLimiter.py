"""
Sliding-Window (Counter) Rate Limiter
=====================================
A rate limiter caps how many requests/packets a client may send per time unit.
This implements the **sliding-window counter** algorithm, which smooths the
boundary bursts that a fixed-window counter suffers from, while using O(1)
memory per client (unlike a sliding-window *log*, which stores a timestamp per
request).

How it works
------------
The window of length ``time_unit`` is divided into the *current* and *previous*
sub-windows. The effective request count is a weighted blend:

    estimated = previous_count * (fraction of previous window still overlapping)
              + current_count

If ``estimated`` would exceed ``capacity`` the packet is dropped; otherwise it is
forwarded and the current counter is incremented. When the wall clock advances
past ``time_unit``, the current counter rolls into the previous counter and the
current counter resets.

Complexity: O(1) time and space per ``handle`` call.

Run:
    uv run --no-project python SystemDesign\\Utils\\RateLimiter.py
"""

from __future__ import annotations

import threading
from time import sleep, time
from typing import Any, Callable

# A callback receives the packet and returns anything (its return value is
# propagated back through ``handle``).
PacketCallback = Callable[[Any], Any]


class SlidingWindow:
    """Thread-safe sliding-window-counter rate limiter.

    Args:
        capacity: Maximum requests allowed within one ``time_unit``.
        time_unit: Window length in seconds.
        forward_callback: Invoked when a packet is admitted.
        drop_callback: Invoked when a packet is rejected (rate exceeded).
    """

    def __init__(
        self,
        capacity: int,
        time_unit: float,
        forward_callback: PacketCallback,
        drop_callback: PacketCallback,
    ) -> None:
        self.capacity = capacity
        self.time_unit = time_unit
        self.forward_callback = forward_callback
        self.drop_callback = drop_callback

        self.cur_time = time()
        self.pre_count = capacity
        self.cur_count = 0
        # Guards the sliding-window counters so a single limiter can be shared
        # across threads handling concurrent packets.
        self._lock = threading.Lock()

    def handle(self, packet: Any) -> Any:
        """Admit or drop ``packet`` and invoke the matching callback."""
        with self._lock:
            now = time()
            if (now - self.cur_time) > self.time_unit:
                self.cur_time = now
                self.pre_count = self.cur_count
                self.cur_count = 0

            elapsed_fraction = (self.time_unit - (now - self.cur_time)) / self.time_unit
            estimated_capacity = (self.pre_count * elapsed_fraction) + self.cur_count

            if estimated_capacity > self.capacity:
                drop = self.drop_callback
                return drop(packet)

            self.cur_count += 1
            forward = self.forward_callback
        # Callbacks run outside the lock so a slow handler can't block others.
        return forward(packet)


def forward(packet: Any) -> None:
    print("Packet Forwarded: " + str(packet))


def drop(packet: Any) -> None:
    print("Packet Dropped: " + str(packet))


def _demo() -> None:
    """Send 15 packets at ~7/s through a 5-per-second limiter."""
    throttle = SlidingWindow(5, 1, forward, drop)
    for packet in range(15):
        sleep(0.14)
        throttle.handle(packet)


if __name__ == "__main__":
    _demo()
