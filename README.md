# PylaAI

**PylaAI** is a high-performance external bot for **Brawl Stars**, powered by on-device ONNX vision models and a modern PySide6 GUI. It automates trophy pushing, queues multiple brawlers, and tracks every match so you can see exactly how your sessions perform over time.

> This repo is the **source build** for developers. If you just want to run the bot, grab the pre-packaged `.exe` from the [Pyla Discord](https://discord.gg/xUusk3fw4A) instead.

---

## Features

### Automation
- **ONNX vision pipeline** — in-game entity detection + wall/tile classifier running on CPU or GPU (CUDA / TensorRT auto-detected)
- **Multi-brawler queue** — push several brawlers in sequence, each with its own trophy / win target
- **Lobby automation** — auto-picks the right brawler, handles game-mode selection, and recovers from idle states
- **Crash recovery** — detects stale frames, stuck screens, and Brawl Stars app crashes; optionally auto-restarts the game
- **Configurable pacing** — cap max IPS, set per-ability detection delays, and tune movement timing

### GUI (PySide6)
- **Home** — pick map orientation, game mode, and emulator; see your last 3 sessions at a glance
- **Brawlers** — browse brawlers by rarity (Rare → Ultra Legendary), drag-and-drop to reorder the queue, edit targets in place
- **Live Feed** — real-time console output with filters (errors / warnings / info / IPS), Ctrl+F search, and live W/L counters
- **History** — per-session match filter, 7-tier stats per brawler, daily win/loss timeline with hover tooltips
- **Settings** — movement delays, detection confidence, pixel thresholds, compute mode, reliability toggles, and notifications
- **Start / Pause / Stop** — bot runs in a background thread; confirm dialog if you stop within 60s of starting
- **Crash toasts** — non-blocking banner when the bot throws; session-end summary when it finishes

### Reliability & QoL
- Auto-restart on crash, auto-reconnect ADB, stale-frame timeout (all configurable)
- Discord webhook notifications on session end / crash
- Debug screenshot capture on stuck events
- Minimize-to-background mode (bot keeps running when the window is closed)
- Pre-flight validation — checks queue targets, model files, and ADB reachability before starting

---

## Quick start

### Prerequisites
- **Python 3.11.9** (tested version)
- **Git**
- An Android emulator with ADB enabled — **LDPlayer**, **BlueStacks**, or **MEmu** (native Android via USB debugging also works)
- Brawl Stars installed on the emulator

### Install
```bash
git clone https://github.com/MrMuff1nn/PylaAI-OP.git
cd PylaAI-OP
python setup.py install
python main.py
```

The GUI opens automatically — pick your emulator on the **Home** page, queue brawlers on the **Brawlers** page, then hit **▶ START BOT**.

---

## Configuration

Config files live in [`cfg/`](cfg/) and can be edited either from the Settings page (recommended) or by hand:

| File | Purpose |
|---|---|
| `general_config.toml` | Global toggles: emulator, GPU mode, IPS cap, notifications, crash recovery |
| `bot_config.toml` | Gameplay: game mode, movement delays, detection confidence, pixel thresholds |
| `time_tresholds.toml` | Polling cadences: ability checks, wall detection, state check intervals |
| `brawlers_info.json` | Brawler metadata (rarity, class, trophies) |

Notable `general_config.toml` keys:

```toml
cpu_or_gpu          = "auto"   # "cpu" | "auto" (picks CUDA/TensorRT if available)
max_ips             = 150      # target frame rate
auto_restart_on_crash  = "yes"
auto_reconnect_adb     = "yes"
stale_frame_timeout_s  = 8
notify_on_session_end  = "yes"
notify_on_crash        = "yes"
save_debug_screenshots = "no"
minimize_to_tray       = "no"
```

---

## Project layout

```
.
├── main.py                    # bot entry point + core loop
├── bot_control.py             # shared stop/pause events (GUI ↔ bot thread)
├── play.py                    # per-frame decision making
├── stage_manager.py           # lobby / match / result state machine
├── state_finder.py            # classifies the current game state from a frame
├── lobby_automation.py        # menu taps, brawler selection, idle recovery
├── window_controller.py       # scrcpy / ADB I/O, input injection
├── trophy_observer.py         # tracks trophy deltas and session outcomes
├── time_management.py         # cadence gates for periodic tasks
├── utils.py                   # config I/O, Discord notifications, misc
├── models/                    # ONNX models (not versioned)
│   ├── mainInGameModel.onnx
│   └── tileDetector.onnx
├── cfg/                       # TOML / JSON config
├── gui/qt/                    # PySide6 GUI
│   ├── app.py                 # QApplication bootstrap
│   ├── shell.py               # main window, nav, bot lifecycle
│   ├── home_page.py
│   ├── fighters_page.py       # brawler grid + queue
│   ├── live_feed.py           # stdout streaming + console
│   ├── history_page.py        # match + session analytics
│   ├── settings_page.py
│   ├── preflight.py           # pre-start validation
│   ├── sessions.py            # session log (JSONL)
│   ├── match_log.py           # per-match log (JSONL)
│   ├── meta.py                # brawler rarity / role lookup
│   ├── theme.py               # colors, gradients
│   └── widgets.py             # reusable tiles, cards, stat widgets
├── api/                       # static assets (brawler icons, etc.)
└── tests/                     # unittest suite
```

---

## Running tests

```bash
python -m unittest discover
```

---

## Notes

- This is the **"localhost" build** — API-dependent features (login, cloud stats, auto brawler-list updates, auto model updates) are disabled. To enable them, edit `api_base_url` in `cfg/general_config.toml` and implement the matching endpoints.
- `.pt` source weights for the vision model are available at [AngelFireLA/BrawlStarsBotMaking](https://github.com/AngelFireLA/BrawlStarsBotMaking).
- This repo will not contain early-access features before they are released publicly.
- Please respect the "no selling" license.

---

## Contributing

Open an **Issue** or **Pull Request**, or drop a ticket in the [Pyla Discord](https://discord.gg/xUusk3fw4A). If you're looking for something to work on, the public Trello has open ideas and bugs:

- **Trello:** https://trello.com/b/SAz9J6AA/public-pyla-trello

---

## Credits

- **AngelFire**
- **MrMuff1nn**

---

## License

Source-available for personal and development use. **No resale** — please respect the authors' work.
