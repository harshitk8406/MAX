"""
MAX 2.0 — Notes & Reminders Skills
"""
import json
import threading
import time
import datetime
from skills.router import skill
from core import memory
from core.logger import log


@skill("remember_note")
def remember_note(args: dict, spoken: str) -> str:
    content = args.get("content", "")
    if not content:
        from core.voice import take_command
        content = take_command(prompt="What should I remember?")
    if content:
        memory.save_note(content)
        return spoken or f"Got it! I'll remember: {content}"
    return "I didn't catch what to remember."


@skill("recall_note")
def recall_note(args: dict, spoken: str) -> str:
    notes = memory.get_notes()
    if not notes:
        return spoken or "You haven't asked me to remember anything yet."
    last = notes[-1]
    created = last.get("created_at", "")[:10]
    return spoken or f"You told me to remember: {last['content']}. That was on {created}."


@skill("set_reminder")
def set_reminder(args: dict, spoken: str) -> str:
    content = args.get("content", "")
    time_str = args.get("time", "")

    if not content:
        from core.voice import take_command
        content = take_command(prompt="What should I remind you about?")
    if not time_str:
        from core.voice import take_command
        time_str = take_command(prompt="When should I remind you? Say something like 5 minutes.")

    memory.add_reminder(content, remind_at=time_str)

    # Schedule the reminder in a background thread if time is given
    delay_seconds = _parse_time_to_seconds(time_str)
    if delay_seconds:
        threading.Thread(
            target=_fire_reminder,
            args=(content, delay_seconds),
            daemon=True
        ).start()
        return spoken or f"I'll remind you about '{content}' in {time_str}."
    else:
        return spoken or f"Reminder saved: {content}. I couldn't parse the time, so I saved it as a note."


def _parse_time_to_seconds(time_str: str) -> int:
    """Simple parser: '5 minutes', '1 hour', '30 seconds'"""
    try:
        parts = time_str.lower().split()
        for i, part in enumerate(parts):
            if part.isdigit() or part.replace('.', '').isdigit():
                amount = float(part)
                if i + 1 < len(parts):
                    unit = parts[i + 1]
                    if 'sec' in unit:
                        return int(amount)
                    elif 'min' in unit:
                        return int(amount * 60)
                    elif 'hour' in unit:
                        return int(amount * 3600)
    except Exception:
        pass
    return 0


def _fire_reminder(content: str, delay_seconds: int) -> None:
    time.sleep(delay_seconds)
    from core.voice import speak
    speak(f"Hey! Reminder: {content}")
    log.info(f"Reminder fired: {content}")


@skill("get_reminders")
def get_reminders(args: dict, spoken: str) -> str:
    pending = memory.get_pending_reminders()
    if not pending:
        return spoken or "You have no pending reminders."
    items = [r["content"] for r in pending[:5]]
    list_str = ". ".join(items)
    return spoken or f"You have {len(pending)} reminders: {list_str}"
