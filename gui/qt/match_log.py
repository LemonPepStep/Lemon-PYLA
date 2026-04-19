"""Per-match event log: append-only JSONL at cfg/match_log.jsonl.

Each line is a JSON object:
    {"ts": 1712345678.9, "brawler": "shelly", "result": "victory",
     "trophy_before": 840, "trophy_after": 850, "delta": 10,
     "win_streak": 3, "duration_s": 128.4}

`result` is one of: victory, defeat, draw, 1st, 2nd, 3rd, 4th.
`duration_s` is optional and may be None.
"""
import json
import os
import time
from typing import Iterable


LOG_PATH = "./cfg/match_log.jsonl"


def log_match(
    brawler: str,
    result: str,
    trophy_before: int | float | None,
    trophy_after: int | float | None,
    win_streak: int | None = None,
    duration_s: float | None = None,
    ts: float | None = None,
) -> None:
    entry = {
        "ts": float(ts if ts is not None else time.time()),
        "brawler": (brawler or "").lower(),
        "result": result,
        "trophy_before": trophy_before,
        "trophy_after": trophy_after,
        "delta": (trophy_after - trophy_before)
                 if (trophy_before is not None and trophy_after is not None) else None,
        "win_streak": win_streak,
        "duration_s": duration_s,
    }
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[match_log] failed to write entry: {e}")


def load_entries() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    out: list[dict] = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[match_log] failed to read: {e}")
    return out


def filter_range(entries: Iterable[dict], range_label: str) -> list[dict]:
    now = time.time()
    cutoffs = {
        "24h": now - 24 * 3600,
        "7d":  now - 7 * 24 * 3600,
        "30d": now - 30 * 24 * 3600,
        "ALL": 0.0,
    }
    cutoff = cutoffs.get(range_label, 0.0)
    return [e for e in entries if e.get("ts", 0) >= cutoff]


WIN_RESULTS = {"victory", "1st", "2nd"}
LOSS_RESULTS = {"defeat", "3rd", "4th"}


def classify(result: str) -> str:
    if result in WIN_RESULTS:
        return "win"
    if result in LOSS_RESULTS:
        return "loss"
    return "draw"
