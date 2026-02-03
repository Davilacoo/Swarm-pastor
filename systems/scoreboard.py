from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class ScoreEntry:
    ts: str
    score: int
    time_s: float
    boids: int
    note: str = ""


class Scoreboard:
    """Tiny CSV-backed score history.

    Stored in project root (next to main.py) as data/scores.csv.
    Safe to call even if the file/folder doesn't exist.
    """

    HEADER = ["timestamp", "score", "time_s", "boids", "note"]

    def __init__(self, csv_path: str = "data/scores.csv"):
        # Make path stable no matter where the user runs `python main.py` from.
        # If csv_path is relative, we anchor it to the folder that contains the entry script (main.py).
        if not os.path.isabs(csv_path):
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0] or __file__))
            csv_path = os.path.join(base_dir, csv_path)
        self.csv_path = csv_path
        self._ensure_file()

    def _ensure_file(self) -> None:
        folder = os.path.dirname(self.csv_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(self.HEADER)

    def append(self, score: int, time_s: float, boids: int, note: str = "") -> None:
        self._ensure_file()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([ts, int(score), float(time_s), int(boids), note])

    def read_all(self) -> List[ScoreEntry]:
        self._ensure_file()
        out: List[ScoreEntry] = []
        with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    out.append(
                        ScoreEntry(
                            ts=row.get("timestamp", ""),
                            score=int(float(row.get("score", 0) or 0)),
                            time_s=float(row.get("time_s", 0) or 0),
                            boids=int(float(row.get("boids", 0) or 0)),
                            note=row.get("note", "") or "",
                        )
                    )
                except Exception:
                    # ignore malformed lines
                    continue
        return out

    def top(self, n: int = 10) -> List[ScoreEntry]:
        entries = self.read_all()
        entries.sort(key=lambda e: e.score, reverse=True)
        return entries[:n]

    def last(self, n: int = 10) -> List[ScoreEntry]:
        entries = self.read_all()
        return entries[-n:][::-1]
