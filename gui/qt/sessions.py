"""Per-session log at cfg/sessions.jsonl.

One JSON object per line:
    {"start": 1712345678.9, "end": 1712350000.0, "duration_s": 4321.1,
     "wins": 12, "losses": 4, "draws": 0, "reason": "user_stopped"}

`reason` is one of: user_stopped, crashed, finished, unknown.
"""
import json
import os
import time


SESSIONS_PATH = "./cfg/sessions.jsonl"


def log_session(start_ts: float, end_ts: float, wins: int, losses: int,
                draws: int, reason: str) -> None:
    entry = {
        "start": float(start_ts),
        "end": float(end_ts),
        "duration_s": float(end_ts - start_ts),
        "wins": int(wins),
        "losses": int(losses),
        "draws": int(draws),
        "reason": reason,
    }
    try:
        os.makedirs(os.path.dirname(SESSIONS_PATH), exist_ok=True)
        with open(SESSIONS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[sessions] failed to write entry: {e}")


def load_sessions() -> list[dict]:
    if not os.path.exists(SESSIONS_PATH):
        return []
    out: list[dict] = []
    try:
        with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[sessions] failed to read: {e}")
    return out


def recent_sessions(n: int = 3) -> list[dict]:
    return list(reversed(load_sessions()[-n:]))


def format_duration(seconds: float) -> str:
    s = int(max(0, seconds))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"
