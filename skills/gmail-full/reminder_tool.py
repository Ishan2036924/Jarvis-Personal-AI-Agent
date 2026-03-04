#!/usr/bin/env python3
"""Reminder tool — creates one-shot cron jobs via CLI."""
import os, sys, json, subprocess

def set_reminder(duration, message):
    """duration: +5m, +1h, +30m etc."""
    import random
    name = f"reminder-{random.randint(100,999)}"
    cmd = [
        "openclaw", "cron", "add",
        "--name", name,
        "--at", duration.lstrip("+"),
        "--session", "isolated",
        "--announce",
        "--channel", "telegram",
        "--to", os.environ.get("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID"),
        "--message", f"⏰ Reminder: {message}",
        "--delete-after-run"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode == 0:
        print(json.dumps({"status": "reminder_set", "name": name, "when": duration, "message": message}))
    else:
        print(json.dumps({"error": result.stderr.strip(), "stdout": result.stdout.strip()}))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: reminder_tool.py <+duration> <message>")
        print("Examples: reminder_tool.py +5m 'Check email'")
        print("          reminder_tool.py +2h 'Call mom'")
        sys.exit(1)
    dur = sys.argv[1].lstrip("+")
    set_reminder(dur, ' '.join(sys.argv[2:]))
