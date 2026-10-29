"""This Mac's CPU as a scrolling area chart, with CPU and memory readouts on top.

Layout (52x16):
  y 0-4   CPU nn            MEM nn      (values coloured by load)
  y 6-15  last 52 CPU samples, one column each, newest on the right; the newest
          column pulses so the chart reads as live
"""

import re
import subprocess
from collections import deque
from dataclasses import dataclass

from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas, dim, mix
from ..render.palette import LED

CHART_TOP, CHART_H = 6, 10
LABEL, GRID = LED["label"], LED["grid"]
GREEN, YELLOW, RED = LED["green"], LED["yellow"], LED["red"]


@dataclass(frozen=True)
class State:
    cpu: int
    mem: int
    history: tuple[int, ...]


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout


def cpu_percent(iostat_output):
    """Busy % from the last `iostat -n0 -c 2 -w 1` line (the first is since boot)."""
    fields = iostat_output.strip().splitlines()[-1].split() if iostat_output.strip() else []
    try:
        idle = int(fields[2])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"unexpected iostat output: {iostat_output!r}") from exc
    return max(0, min(100, 100 - idle))


def mem_percent(vm_stat_output, total_bytes):
    """Used = active + wired + compressed pages, like Activity Monitor's 'Memory Used'."""
    m = re.search(r"page size of (\d+)", vm_stat_output)
    if m is None:
        raise ValueError("vm_stat output has no page size")
    page = int(m.group(1))

    def pages(name):
        found = re.search(rf"{name}:\s+(\d+)", vm_stat_output)
        return int(found.group(1)) if found else 0

    used = pages("Pages active") + pages("Pages wired down") + pages("Pages occupied by compressor")
    return min(100, round(used * page * 100 / total_bytes))


def load_color(pct):
    """Green to yellow over 0-60 %, yellow to red over 60-100 %."""
    if pct <= 60:
        return mix(GREEN, YELLOW, pct / 60)
    return mix(YELLOW, RED, (pct - 60) / 40)


class SysScreen:
    """Keeps the CPU history; each sample becomes a two-frame pulsing GIF."""

    APP = "sys"
    TICK = 0.2  # iostat itself blocks for 1 s per sample

    def __init__(self, run=_run):
        self.run = run
        self.history = deque([0] * WIDTH, maxlen=WIDTH)
        self.memsize = None

    def sample(self):
        if self.memsize is None:
            self.memsize = int(self.run(["sysctl", "-n", "hw.memsize"]))
        cpu = cpu_percent(self.run(["iostat", "-n0", "-c", "2", "-w", "1"]))
        self.history.append(cpu)
        mem = mem_percent(self.run(["vm_stat"]), self.memsize)
        return State(cpu, mem, tuple(self.history))

    def render(self, state):
        return Animation([_frame(state, glow) for glow in (True, False)], 500, key=state)


def _frame(state, glow):
    c = Canvas()
    c.text(0, 0, "CPU", LABEL, big=False)
    c.text(13, 0, str(state.cpu), load_color(state.cpu), big=False)
    mem = str(state.mem)
    mem_x = WIDTH - font.text_width(font.SMALL, mem)
    c.text(mem_x, 0, mem, load_color(state.mem), big=False)
    c.text(mem_x - 14, 0, "MEM", LABEL, big=False)

    for x in range(0, WIDTH, 2):  # 50 % guide
        c.set(x, CHART_TOP + CHART_H // 2, GRID)
    for x, pct in enumerate(state.history):
        height = round(pct * CHART_H / 100) or (1 if pct else 0)
        for row in range(height):
            if x == WIDTH - 1:  # newest sample pulses
                shade = 1.0 if glow else 0.55
            else:  # bright top edge over a dimmer fill
                shade = 1.0 if row == height - 1 else 0.4
            color = load_color(100 * (row + 1) / CHART_H)
            c.set(x, CHART_TOP + CHART_H - 1 - row, dim(color, shade))
    return c
