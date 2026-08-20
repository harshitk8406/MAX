"""
MAX 2.0 — Calendar & Scheduling Skill
Natural-language reminders, daily schedule, morning briefing.
"""
import json
import os
import re
import datetime
import threading
import time
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

USER_NAME = _cfg["user"]["name"]

# ── Time parser ───────────────────────────────────────────────────────────────

def _parse_time_string(time_str: str) -> tuple[int, str]:
    """
    Parse natural language time to (seconds, human_label).
    Supports: '5 minutes', '2 hours', '30 seconds', 'in an hour', '10 mins'
    Returns (0, '') if unparseable.
    """
    if not time_str:
        return 0, ""
    s = time_str.lower().strip()

    # Handle "an hour" / "a minute"
    s = s.replace("an hour", "1 hour").replace("a minute", "1 minute").replace("a second", "1 second")

    # Match patterns like "5 minutes", "2 hours 30 minutes"
    total = 0
    label_parts = []
    pattern = r'(\d+(?:\.\d+)?)\s*(second|sec|minute|min|hour|hr|day)s?'
    for match in re.finditer(pattern, s):
        amount = float(match.group(1))
        unit = match.group(2)
        if unit in ("second", "sec"):
            total += int(amount)
            label_parts.append(f"{int(amount)} second{'s' if amount != 1 else ''}")
        elif unit in ("minute", "min"):
            total += int(amount * 60)
            label_parts.append(f"{int(amount)} minute{'s' if amount != 1 else ''}")
        elif unit in ("hour", "hr"):
            total += int(amount * 3600)
            label_parts.append(f"{int(amount)} hour{'s' if amount != 1 else ''}")
        elif unit == "day":
            total += int(amount * 86400)
            label_parts.append(f"{int(amount)} day{'s' if amount != 1 else ''}")

    label = " and ".join(label_parts) if label_parts else ""
    return total, label


def _fire_reminder(content: str, delay: int):
    """Background thread: sleep then speak + log."""
    time.sleep(delay)
    from core.voice import speak
    speak(f"Hey {USER_NAME}! Reminder: {content}")
    log.info(f"Reminder fired: {content}")


# ── Skill Handlers ─────────────────────────────────────────────────────────────

@skill("set_reminder")
def set_reminder(args: dict, spoken: str) -> str:
    content = args.get("content", "") or args.get("reminder", "") or args.get("task", "")
    time_str = args.get("time", "") or args.get("when", "") or args.get("delay", "")

    if not content:
        from core.voice import take_command
        content = take_command(prompt="What should I remind you about?")
    if not content:
        return "What should I remind you about?"

    if not time_str:
        from core.voice import take_command
        time_str = take_command(prompt="When should I remind you? Say something like 5 minutes or 2 hours.")

    delay, label = _parse_time_string(time_str)

    # Save to memory
    from core import memory
    memory.add_reminder(content, remind_at=time_str)

    if delay > 0:
        threading.Thread(target=_fire_reminder, args=(content, delay), daemon=True).start()
        return spoken or f"Got it! I'll remind you about '{content}' in {label}."
    else:
        return spoken or f"Reminder saved: '{content}'. I couldn't parse the time, so I stored it — tell me the time to set a countdown."


@skill("get_reminders")
def get_reminders(args: dict, spoken: str) -> str:
    from core import memory
    pending = memory.get_pending_reminders()
    if not pending:
        return spoken or "You have no pending reminders. All clear!"
    items = [r["content"] for r in pending[:5]]
    if len(items) == 1:
        return spoken or f"You have 1 reminder: {items[0]}"
    return spoken or f"You have {len(pending)} reminders. Here are the first few: {'. '.join(items[:3])}."


@skill("get_schedule")
def get_schedule(args: dict, spoken: str) -> str:
    """Give a summary of today's pending reminders + current time."""
    from core import memory
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d")
    pending = memory.get_pending_reminders()

    if not pending:
        return spoken or f"It's {time_str} on {date_str}. You have nothing scheduled. Enjoy your free time!"

    items = [r["content"] for r in pending[:5]]
    reminder_text = ". ".join(items)
    return spoken or f"It's {time_str} on {date_str}. You have {len(pending)} things pending: {reminder_text}."


@skill("morning_briefing")
def morning_briefing(args: dict, spoken: str) -> str:
    """Full morning briefing: time, weather, reminders, news headline."""
    from core import memory
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")

    lines = [f"Good morning, {USER_NAME}! It's {time_str} on {date_str}."]

    # Reminders
    pending = memory.get_pending_reminders()
    if pending:
        lines.append(f"You have {len(pending)} pending reminder{'s' if len(pending) > 1 else ''}.")
        for r in pending[:2]:
            lines.append(f"Don't forget: {r['content']}.")
    else:
        lines.append("No reminders today — you're free!")

    # Quick weather snippet
    try:
        import requests, geocoder
        g = geocoder.ip("me")
        if g.latlng:
            api_url = f"https://fcc-weather-api.glitch.me/api/current?lat={g.latlng[0]}&lon={g.latlng[1]}"
            resp = requests.get(api_url, timeout=5)
            d = resp.json()
            if d.get("cod") == 200:
                temp = d["main"]["temp"]
                desc = d["weather"][0]["main"]
                city = d["name"]
                lines.append(f"Weather in {city}: {desc}, {temp}°C.")
    except Exception:
        pass

    # Motivational closer
    try:
        from core.brain import quick_chat
        quote = quick_chat(f"Give a single short motivational sentence for {USER_NAME}'s morning. No quotes, no markdown.")
        lines.append(quote)
    except Exception:
        lines.append("Have a productive day ahead!")

    return " ".join(lines)


@skill("remember_note")
def remember_note(args: dict, spoken: str) -> str:
    content = args.get("content", "") or args.get("note", "") or args.get("text", "")
    if not content:
        from core.voice import take_command
        content = take_command(prompt="What should I remember?")
    if not content:
        return "I didn't catch anything to remember."
    from core import memory
    memory.save_note(content)
    return spoken or f"Got it! I'll remember: '{content}'."


@skill("recall_note")
def recall_note(args: dict, spoken: str) -> str:
    from core import memory
    notes = memory.get_notes()
    if not notes:
        return spoken or "You haven't asked me to remember anything yet."
    last = notes[-1]
    created = last.get("created_at", "")[:10]
    return spoken or f"You told me to remember: '{last['content']}'. That was on {created}."
