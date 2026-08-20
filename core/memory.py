"""
MAX 2.0 — Memory
Persistent conversation history, notes, command log stored in memory.json
"""

import json
import os
from datetime import datetime
from typing import Optional
from core.logger import log

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")

_DEFAULT = {
    "conversation": [],
    "notes": [],
    "reminders": [],
    "command_history": []
}


def _load() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all keys exist
                for k, v in _DEFAULT.items():
                    data.setdefault(k, v)
                return data
        except Exception as e:
            log.warning(f"Memory file corrupted, resetting. Error: {e}")
    return dict(_DEFAULT)


def _save(data: dict) -> None:
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save memory: {e}")


# ── Conversation ─────────────────────────────────────────────────────────────

def add_message(role: str, content: str, max_history: int = 20) -> None:
    """Add a user/assistant message to conversation history."""
    data = _load()
    data["conversation"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    data["conversation"] = data["conversation"][-max_history:]
    _save(data)


def get_conversation(n: int = 10) -> list[dict]:
    """Get last n conversation turns (for LLM context)."""
    data = _load()
    history = data["conversation"]
    # Return as role/content pairs (strip timestamp for LLM)
    return [{"role": m["role"], "content": m["content"]} for m in history[-n:]]


def clear_conversation() -> None:
    data = _load()
    data["conversation"] = []
    _save(data)


# ── Notes ────────────────────────────────────────────────────────────────────

def save_note(content: str) -> None:
    """Save a note with timestamp."""
    data = _load()
    data["notes"].append({
        "content": content,
        "created_at": datetime.now().isoformat()
    })
    _save(data)
    log.info(f"Note saved: {content[:50]}")


def get_notes() -> list[dict]:
    return _load()["notes"]


def recall_note(index: int = -1) -> Optional[str]:
    """Get the most recent note (or by index)."""
    notes = get_notes()
    if not notes:
        return None
    return notes[index]["content"]


def clear_notes() -> None:
    data = _load()
    data["notes"] = []
    _save(data)


# ── Reminders ────────────────────────────────────────────────────────────────

def add_reminder(content: str, remind_at: Optional[str] = None) -> None:
    data = _load()
    data["reminders"].append({
        "content": content,
        "remind_at": remind_at,
        "created_at": datetime.now().isoformat(),
        "done": False
    })
    _save(data)
    log.info(f"Reminder saved: {content[:50]}")


def get_pending_reminders() -> list[dict]:
    return [r for r in _load()["reminders"] if not r.get("done")]


def mark_reminder_done(index: int) -> None:
    data = _load()
    if 0 <= index < len(data["reminders"]):
        data["reminders"][index]["done"] = True
        _save(data)


# ── Command History ───────────────────────────────────────────────────────────

def log_command(query: str, skill_used: str, response_snippet: str) -> None:
    data = _load()
    data["command_history"].append({
        "query": query,
        "skill": skill_used,
        "response": response_snippet[:100],
        "timestamp": datetime.now().isoformat()
    })
    data["command_history"] = data["command_history"][-100:]
    _save(data)


def get_command_history(n: int = 20) -> list[dict]:
    return _load()["command_history"][-n:]
