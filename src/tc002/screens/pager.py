"""Several items on one screen, one at a time: stocks, stories, Home Assistant values.

The items are fetched together every `refresh` seconds and kept; the screen shows the
next one every `seconds`, so each GIF stays within the clock's frame limit and the
service does not ask the internet more often than the user chose. A failed fetch raises
as before, which the sampling loop turns into the data's age on the clock.
"""

import time


class Pager:
    def __init__(self, fetch, refresh, seconds, clock=time.monotonic):
        self.fetch, self.refresh, self.seconds, self.clock = fetch, refresh, seconds, clock
        self._items, self._at = None, None

    def current(self):
        """(index, how many, item) for now; fetches when the kept items are too old."""
        now = self.clock()
        if self._items is None or now - self._at >= self.refresh:
            self._items, self._at = list(self.fetch()), now
        if not self._items:
            return 0, 0, None
        index = int(now // self.seconds) % len(self._items)
        return index, len(self._items), self._items[index]
