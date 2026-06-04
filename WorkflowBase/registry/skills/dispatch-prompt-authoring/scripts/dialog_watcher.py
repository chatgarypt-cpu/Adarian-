#!/usr/bin/env python3
"""
Monitor a tmux session for permission dialogs and auto-approve.

DESIGN (2026-06-02):
  dialog_watcher is the PRIMARY approval mechanism for simple bash permission
  dialogs. It pattern-matches common dialog text and sends keyboard input.

  ClaudeDialogHandler (in tmux_executor.py) is the FALLBACK — for dialogs that
  watcher cannot match, DialogHandler classifies and defers to human takeover
  via the observer Terminal window.

  workflow auto-mode (option 3: "switch to auto mode") is NEVER auto-approved.
  Instead, the watcher plays a notification sound and prints to stdout so
  Hermes can surface the request to the user for manual approval.

Usage:
    python3 dialog_watcher.py <tmux-session-id>

Canonical path: tools/dialog_watcher.py (project level)
"""
import subprocess
import sys
import time

SESSION = sys.argv[1] if len(sys.argv) > 1 else "adarian_default"

AUTO_APPROVE_PATTERNS = [
    "Do you want to proceed?",
    "Do you want to create",
    "Do you want to overwrite",
    "Proceed?",
    "proceed?",
]

AUTO_MODE_PATTERNS = [
    "switch to auto mode",
    "auto mode",
    "workflows run best with",
]

GLASS_SOUND = "/System/Library/Sounds/Glass.aiff"


def _pane_contains(session: str, patterns: list[str]) -> str | None:
    r = subprocess.run(
        ["tmux", "capture-pane", "-t", session, "-p"],
        capture_output=True, text=True, timeout=10,
    )
    for line in r.stdout.split("\n"):
        for p in patterns:
            if p in line:
                return p
    return None


def _send_enter(session: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], timeout=5)


def _play_sound() -> None:
    try:
        subprocess.run(["afplay", GLASS_SOUND], timeout=3, capture_output=True)
    except Exception:
        pass


def main():
    print(f"[watcher] monitoring tmux session: {SESSION}", flush=True)
    while True:
        try:
            if _pane_contains(SESSION, AUTO_MODE_PATTERNS):
                _play_sound()
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] AUTO-MODE dialog — needs human approval in Hermes CLI", flush=True)
                time.sleep(10)
                continue

            matched = _pane_contains(SESSION, AUTO_APPROVE_PATTERNS)
            if matched:
                _send_enter(SESSION)
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] approved: {matched}", flush=True)
                time.sleep(3)
                continue

            time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[watcher] {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
