"""
M.A.X 2.0 — Main Entry Point
Wires together: GUI, Voice Engine, AI Brain, Skills Router, REST API.

Usage:
    python main.py
"""

import sys
import os
import json
import threading
import datetime

# ── Add project root to path ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import log
from core.brain import ask as brain_ask
from core.voice import (
    speak, take_command, set_speak_callbacks, set_stt_callbacks,
    start_wake_listener, stop_wake_listener
)
from core.memory import log_command, add_message

from skills.router import get_router

# Import all skills to register them via @skill decorators
import skills.browser        # noqa: F401
import skills.system         # noqa: F401
import skills.weather        # noqa: F401
import skills.news           # noqa: F401
import skills.wiki           # noqa: F401
import skills.calendar_skill # noqa: F401  — replaces notes.py (smarter reminders)
import skills.jokes          # noqa: F401
import skills.dictionary     # noqa: F401
import skills.email_skill    # noqa: F401
import skills.spotify        # noqa: F401
# ── New capabilities ──────────────────────────────────────────────────────────
import skills.files          # noqa: F401  — deep file management
import skills.pc_control     # noqa: F401  — app control, volume, lock screen
import skills.web_research   # noqa: F401  — autonomous web fetch + LLM summarize
import skills.youtube_skill  # noqa: F401  — smart YouTube: play, download, summarize
import skills.messaging      # noqa: F401  — WhatsApp, notifications
import skills.image_gen      # noqa: F401  — AI image generation (Pollinations.ai)


from gui.app import MaxGUI

# ── Load config ────────────────────────────────────────────────────────────────
_cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

USER_NAME = _cfg["user"]["name"]
ASSISTANT_NAME = _cfg["user"].get("assistant_name", "MAX")
_api_enabled = _cfg.get("api", {}).get("enabled", True)

# ── Global GUI reference ───────────────────────────────────────────────────────
gui: MaxGUI = None
router = get_router()

# ── Core Processing ────────────────────────────────────────────────────────────

def process_query(query: str, speak_response: bool = True) -> dict:
    """
    Full pipeline: query → brain → skill dispatch → speak → log.
    Returns intent dict.
    """
    if not query or query.strip() in ("", "none"):
        return {"skill": "none", "args": {}, "speak": ""}

    log.info(f"Processing query: {query}")

    # Special fast-paths (no LLM needed)
    low = query.lower().strip()

    # Shutdown MAX (ONLY explicit full phrases — 'sleep' alone must not trigger this)
    if any(w in low for w in ["goodbye max", "shut down max", "stop max", "exit max"]):
        response = "Alright, shutting down. It was a pleasure as always. Take care!"
        _deliver(response)
        if gui:
            gui.root.after(2000, gui.root.destroy)
        return {"skill": "sleep", "args": {}, "speak": response}

    # Direct reminder fast-path — avoids LLM misrouting
    if any(w in low for w in ["my reminders", "show reminders", "list reminders", "any reminders", "pending reminders"]):
        response = router.dispatch({"skill": "get_reminders", "args": {}, "speak": ""})
        if speak_response:
            _deliver(response)
        return {"skill": "get_reminders", "args": {}, "speak": response}

    # Wake-word echo
    if low in ("hey max", "max"):
        response = "Hey! What's up?"
        _deliver(response)
        return {"skill": "wake", "args": {}, "speak": response}

    # Brain intent detection
    if gui:
        gui.set_state("thinking")

    intent = brain_ask(query)
    response = router.dispatch(intent)

    # If skill returned None, fall back to spoken text
    if response is None:
        response = intent.get("speak", "I'm not sure how to help with that.")

    # Patch conversation memory: if a skill returned a richer response than
    # the short "speak" blurb brain.py stored, update it so future context
    # reflects what MAX actually said (prevents context drift / nonsense).
    speak_blurb = intent.get("speak", "")
    if response and response != speak_blurb:
        # Replace last assistant message with the real full response
        from core.memory import _load as _mem_load, _save as _mem_save, _DEFAULT
        import json as _json
        _data = _mem_load()
        conv = _data.get("conversation", [])
        if conv and conv[-1]["role"] == "assistant":
            conv[-1]["content"] = response[:1500]  # cap to avoid bloat
        _mem_save(_data)

    # Deliver to user
    if speak_response:
        _deliver(response)
    else:
        if gui:
            gui.add_max_message(response)

    # Log to memory
    log_command(query, intent.get("skill", "unknown"), response[:100])

    return {**intent, "speak": response}


def _deliver(text: str) -> None:
    """Speak and display a response."""
    if not text:
        return
    if gui:
        gui.add_max_message(text)
    speak(text)


# ── Voice Loop ─────────────────────────────────────────────────────────────────

# Phrases that close the continuous session
_CLOSE_PHRASES  = ["over and out", "over out"]
_SLEEP_PHRASES  = ["go to sleep", "stand by", "standby", "stop listening"]
_SHUTDOWN_PHRASES = ["goodbye max", "shut down max", "exit max"]

def _on_wake():
    """
    Called when wake-word is detected.
    Enters a CONTINUOUS session — MAX keeps listening until the user
    says 'Over and Out' (closes app) or 'Go to sleep' (returns to standby).
    Silence is ignored — MAX waits patiently for the next command.
    """
    import time

    log.info("Wake word triggered — entering CONTINUOUS session")

    # Pause the background wake listener while we own the microphone
    stop_wake_listener()

    if gui:
        gui.set_state("listening")
        gui.show_notification("Session active — say 'Over and Out' to close")

    _deliver("I'm listening. What do you need?")

    # Small pause after speaking so the mic doesn't pick up MAX's own voice
    time.sleep(0.8)

    while True:
        if gui:
            gui.set_state("listening")

        query = take_command(timeout=10)

        # ── No speech / couldn't understand — just keep listening ────────────
        if not query:
            continue            # Stay in session, wait for next command

        if gui:
            gui.add_user_message(query)

        low = query.lower().strip()

        # ── "Over and Out" → speak farewell + close MAX ──────────────────
        if any(p in low for p in _CLOSE_PHRASES):
            farewell = "Over and out. It was a pleasure, as always. Goodbye!"
            _deliver(farewell)
            log.info("'Over and Out' received — shutting down MAX")
            if gui:
                gui.root.after(2000, gui.root.destroy)
            return          # App is closing — don't restart wake listener

        # ── "Go to sleep / Stand by" → end session, keep app open ───────────
        if any(p in low for p in _SLEEP_PHRASES):
            _deliver("Going on standby. Say 'Hey Max' when you need me.")
            if gui:
                gui.set_state("idle")
            break           # Exit loop → restart wake listener below

        # ── Shutdown synonyms ────────────────────────────────────────────────
        if any(p in low for p in _SHUTDOWN_PHRASES):
            _deliver("Shutting down. Take care!")
            if gui:
                gui.root.after(2000, gui.root.destroy)
            return

        # ── Normal command ────────────────────────────────────────────────────
        process_query(query)

        # Wait 0.8s after MAX finishes speaking before re-opening the mic.
        # This prevents the mic from picking up MAX's own TTS voice.
        time.sleep(0.8)

    # Session ended — re-arm the wake-word listener
    start_wake_listener(_on_wake)
    log.info("Wake-word listener re-armed after session end")


def _on_listen_trigger():
    """Called when user clicks the mic button in GUI."""
    # Must run in its own thread — _on_wake() is blocking and would freeze the GUI
    stop_wake_listener()
    import threading
    threading.Thread(target=_on_wake, daemon=True, name="ManualSession").start()



def _on_quick_action(intent_name: str):
    """Handle quick action button presses from GUI."""
    intent = {"skill": intent_name, "args": {}, "speak": ""}
    if gui:
        gui.set_state("thinking")
    response = router.dispatch(intent)
    if not response:
        # Trigger brain for richer response
        query_map = {
                "weather":          "what's the weather like?",
                "news":             "tell me today's news",
                "joke":             "tell me a joke",
                "screenshot":       "take a screenshot",
                "take_screenshot":  "take a screenshot",
                "cpu_status":       "check cpu and battery status",
                "spotify_play":     "play music on spotify",
                "get_schedule":     "what's on my schedule today?",
                "morning_briefing": "give me a morning briefing",
                "web_research":     "search the web for something",
                "generate_image":   "generate an image",
                "lock_screen":      "lock the screen",
            }
        query = query_map.get(intent_name, intent_name)
        process_query(query)
    else:
        _deliver(response)
        log_command(f"quick:{intent_name}", intent_name, response[:100])


# ── Voice callbacks for GUI ────────────────────────────────────────────────────

def _on_speaking_start(text: str):
    if gui:
        gui.set_state("speaking")


def _on_speaking_end():
    if gui:
        gui.set_state("idle")


def _on_listening():
    if gui:
        gui.set_state("listening")


def _on_recognized(text: str):
    if gui:
        gui.set_state("thinking")


def _on_stt_error(msg: str):
    if gui:
        gui.set_state("idle")
        gui.show_notification(msg, 2000)


# ── Startup Greeting ───────────────────────────────────────────────────────────

def _startup_greeting():
    """Warm, human-sounding startup message."""
    hour = datetime.datetime.now().hour
    greetings = {
        range(5, 12):  f"Good morning! Systems are fully online and I'm ready to go.",
        range(12, 17): f"Good afternoon! All systems operational.",
        range(17, 21): f"Good evening! Everything's running smoothly.",
    }
    greeting = "Hey there! Good to see you. I'm all set."
    for time_range, msg in greetings.items():
        if hour in time_range:
            greeting = msg
            break

    _deliver(greeting)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    global gui

    log.info("=" * 60)
    log.info(f"  M.A.X 2.0 — Starting Up")
    log.info("=" * 60)

    # ── Register voice callbacks
    set_speak_callbacks(on_start=_on_speaking_start, on_end=_on_speaking_end)
    set_stt_callbacks(on_listening=_on_listening, on_recognized=_on_recognized,
                      on_error=_on_stt_error)

    # ── Build GUI first — before any threads that touch audio/COM
    # (PyAudio's COM initialization in background threads can corrupt
    # tkinter's internal widget name counter if GUI hasn't been created yet)
    gui = MaxGUI()
    gui.register("on_query", process_query)
    gui.register("on_listen_trigger", _on_listen_trigger)
    gui.register("on_quick_action", _on_quick_action)
    gui.register("on_close", lambda: (stop_wake_listener(), log.info("MAX shutting down.")))

    # ── Start REST API server (if enabled)
    if _api_enabled:
        try:
            from api.server import run_server, set_query_processor
            set_query_processor(process_query)
            api_thread = threading.Thread(target=run_server, daemon=True, name="APIServer")
            api_thread.start()
            log.info("REST API server started on http://127.0.0.1:8000")
        except Exception as e:
            log.warning(f"REST API failed to start: {e}")

    # ── Start wake-word listener (after GUI, so PyAudio COM doesn't corrupt Tk)
    start_wake_listener(_on_wake)
    log.info(f"Wake-word listener active: '{_cfg.get('wake_word', 'hey max')}'")

    # ── Startup greeting (non-blocking)
    threading.Thread(target=_startup_greeting, daemon=True).start()

    log.info("GUI starting — MAX 2.0 is live!")

    # ── Run (blocking — mainloop)
    gui.run()


if __name__ == "__main__":
    main()
