"""Minimal live progress bar (0-100%).

On a TTY it rewrites one line (\r) for a real-time bar; when output is
captured (logs, CI) it prints one line per percent change instead.
"""
import sys


class Progress:
    def __init__(self, total: int, desc: str = ""):
        self.total = max(1, int(total))
        self.done = 0
        self.desc = desc
        self._last = -1
        self._tty = sys.stdout.isatty()

    def update(self, n: int = 1):
        self.done += n
        pct = int(100 * self.done / self.total)
        if pct == self._last:
            return
        self._last = pct
        bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
        line = f"{self.desc} [{bar}] {pct:3d}%"
        if self._tty:
            sys.stdout.write("\r" + line)
        else:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def finish(self):
        if self._tty:
            sys.stdout.write("\n")
        sys.stdout.flush()
