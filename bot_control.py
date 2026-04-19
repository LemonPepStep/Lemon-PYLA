"""Shared bot-control signals.

Lives in its own module so both `main` (when run as __main__) and the GUI can
reference the *same* Event objects. If these were defined in main.py, importing
`main` from elsewhere would re-execute main.py under a different module name
and produce a second, unrelated set of Events.
"""
import threading
import time


stop_event = threading.Event()
pause_event = threading.Event()


def request_stop() -> None:
    stop_event.set()
    # Wake any paused loop so it can see the stop flag immediately
    pause_event.clear()


def clear_stop() -> None:
    stop_event.clear()


def is_stop_requested() -> bool:
    return stop_event.is_set()


def request_pause() -> None:
    pause_event.set()


def clear_pause() -> None:
    pause_event.clear()


def is_paused() -> bool:
    return pause_event.is_set()


def wait_while_paused(poll_s: float = 0.25) -> None:
    """Block while pause is set. Returns immediately if stop is requested."""
    while pause_event.is_set() and not stop_event.is_set():
        time.sleep(poll_s)
