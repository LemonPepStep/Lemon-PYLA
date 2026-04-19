"""Pre-flight validation run before starting the bot.

Returns a list of human-readable problems. An empty list means "ready to go".
"""
import os
import re
import shutil
import subprocess


MODEL_FILES = [
    "./models/mainInGameModel.onnx",
    "./models/tileDetector.onnx",
]


EMULATOR_PORTS = {
    "LDPlayer":   "127.0.0.1:5555",
    "BlueStacks": "127.0.0.1:5037",
    "MEmu":       "127.0.0.1:21503",
    "Others":     None,
}


def _adb_reachable(host_port: str, timeout_s: float = 3.0,
                   reconnect: bool = True) -> tuple[bool, str]:
    adb = shutil.which("adb") or "adb"
    try:
        if reconnect:
            subprocess.run(
                [adb, "connect", host_port],
                timeout=timeout_s,
                capture_output=True,
                check=False,
            )
        result = subprocess.run(
            [adb, "devices"],
            timeout=timeout_s,
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return False, "adb binary not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"adb timed out contacting {host_port}"
    except Exception as e:
        return False, f"adb error: {e}"

    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if line.startswith(host_port) and re.search(r"\bdevice\b", line):
            return True, "connected"
    return False, f"no device at {host_port} (start your emulator)"


def validate(queue_data: list[dict], emulator_name: str,
             skip_adb: bool = False, auto_reconnect: bool = True) -> list[str]:
    problems: list[str] = []

    # Queue
    if not queue_data:
        problems.append("Queue is empty — add at least one brawler on the Brawlers page.")

    # Per-entry target/current sanity
    for i, e in enumerate(queue_data or []):
        b = (e.get("brawler") or "").title() or f"Entry {i + 1}"
        kind = e.get("type", "trophies")
        target = e.get("push_until", 0)
        current = e.get("trophies", 0) if kind == "trophies" else e.get("wins", 0)
        try:
            target = int(target); current = int(current)
        except (TypeError, ValueError):
            problems.append(f"{b}: target and current must be numbers.")
            continue
        if target <= current:
            problems.append(f"{b}: target ({target}) must be greater than current ({current}).")
        if target < 0 or current < 0:
            problems.append(f"{b}: target and current must be non-negative.")

    # Model files
    for path in MODEL_FILES:
        if not os.path.exists(path):
            problems.append(f"Missing model file: {path}")

    # Emulator reachability
    if not skip_adb:
        port = EMULATOR_PORTS.get(emulator_name)
        if port is None:
            # "Others" — skip check, user knows what they're doing
            pass
        else:
            ok, detail = _adb_reachable(port, reconnect=auto_reconnect)
            if not ok:
                problems.append(f"Emulator '{emulator_name}' unreachable: {detail}")

    return problems
