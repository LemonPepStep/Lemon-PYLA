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


# Common ADB ports per emulator. BlueStacks 4 uses 5555, BlueStacks 5 uses 5565.
# LDPlayer cycles 5555 / 5557 / 5559... per instance. MEmu uses 21503.
EMULATOR_PORTS = {
    "LDPlayer":   ["127.0.0.1:5555", "127.0.0.1:5557", "127.0.0.1:5559"],
    "BlueStacks": ["127.0.0.1:5555", "127.0.0.1:5565", "127.0.0.1:5575", "127.0.0.1:5585"],
    "MEmu":       ["127.0.0.1:21503", "127.0.0.1:21513"],
    "Others":     None,
}


def _adb_devices(timeout_s: float = 3.0) -> tuple[bool, str, list[str]]:
    """Returns (ok, detail, connected_host_ports)."""
    adb = shutil.which("adb") or "adb"
    try:
        result = subprocess.run(
            [adb, "devices"],
            timeout=timeout_s,
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return False, "adb binary not found on PATH", []
    except subprocess.TimeoutExpired:
        return False, "adb timed out listing devices", []
    except Exception as e:
        return False, f"adb error: {e}", []

    connected: list[str] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        if re.search(r"\bdevice\b", line):
            connected.append(line.split()[0])
    return True, "ok", connected


def _adb_reachable(host_ports: list[str], timeout_s: float = 3.0,
                   reconnect: bool = True) -> tuple[bool, str]:
    adb = shutil.which("adb") or "adb"
    # First, see what's already connected — covers emulators that auto-register with adb
    ok, detail, connected = _adb_devices(timeout_s)
    if not ok:
        return False, detail
    for hp in host_ports:
        if hp in connected:
            return True, f"already connected at {hp}"
    # If nothing is connected yet, optionally try to `adb connect` each candidate port
    if reconnect:
        for hp in host_ports:
            try:
                subprocess.run([adb, "connect", hp], timeout=timeout_s,
                               capture_output=True, check=False)
            except Exception:
                continue
        ok, detail, connected = _adb_devices(timeout_s)
        if not ok:
            return False, detail
        for hp in host_ports:
            if hp in connected:
                return True, f"connected at {hp}"
    # Last-ditch: if ANY device is connected (e.g. USB phone, port we don't know), accept it
    if connected:
        return True, f"using already-attached device {connected[0]}"
    tried = ", ".join(host_ports)
    return False, f"no device found — tried {tried} (is the emulator running with ADB enabled?)"


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
        ports = EMULATOR_PORTS.get(emulator_name)
        if ports is None:
            # "Others" — skip check, user knows what they're doing
            pass
        else:
            ok, detail = _adb_reachable(ports, reconnect=auto_reconnect)
            if not ok:
                problems.append(f"Emulator '{emulator_name}' unreachable: {detail}")

    return problems
