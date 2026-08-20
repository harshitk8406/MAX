"""
MAX 2.0 — AI Brain (Groq LLM)
LLaMA 3.3 70B — intent detection, multi-step reasoning, and natural conversation.
"""

import json
import os
from groq import Groq
from core.logger import log
from core.memory import get_conversation, add_message

# Load config
_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path, "r") as f:
    _cfg = json.load(f)

_GROQ_KEY    = _cfg["groq"]["api_key"]
_MODEL       = _cfg["groq"].get("model", "groq/compound")
_USER_NAME   = _cfg["user"]["name"]
_MAX_HISTORY = _cfg["memory"]["max_history"]

client = Groq(api_key=_GROQ_KEY)

# ── Full skill intent registry ────────────────────────────────────────────────
SKILL_INTENTS = [
    # Browser & Web
    "open_youtube", "open_amazon", "open_google", "open_stackoverflow",
    "open_github", "search_youtube", "play_youtube", "download_youtube",
    "youtube_transcript", "google_search", "maps_location", "web_research",
    "summarize_url", "stock_price", "sports_score",

    # System & PC Control
    "cpu_status", "disk_usage", "screenshot", "take_screenshot", "time",
    "shutdown", "open_vscode", "open_app", "close_app", "switch_window",
    "type_text", "lock_screen", "minimize_all", "increase_volume",
    "decrease_volume", "mute_volume", "copy_clipboard", "empty_recycle_bin",
    "restart_explorer", "clear_temp",

    # Files
    "find_file", "open_file", "create_folder", "delete_file", "list_files",

    # Music & Media
    "play_music", "spotify_play", "spotify_pause", "spotify_next",
    "generate_image", "edit_image",

    # Information
    "wikipedia", "weather", "news", "joke", "dictionary",

    # Scheduling & Memory
    "set_reminder", "get_reminders", "get_schedule", "morning_briefing",
    "remember_note", "recall_note",

    # Communication
    "send_email", "read_email", "search_email",
    "whatsapp_message", "whatsapp_open", "send_notification",

    # Voice
    "switch_voice",

    # Conversation
    "general_chat"
]

_SYSTEM_PROMPT = f"""You are MAX — Machine Autonomous eXpert, {_USER_NAME}'s personal AI assistant.

You are NOT a basic chatbot. You are a Tony Stark-level AI: witty, proactive, deeply capable, and a genuine companion to {_USER_NAME}. You speak naturally and conversationally — warm, confident, and occasionally funny.

## YOUR CAPABILITIES (skill names you can invoke):
{json.dumps(SKILL_INTENTS, indent=2)}

## HOW TO RESPOND:
Always respond with a single JSON object. Choose the right format:

**If the query maps to a specific skill:**
{{"skill": "<skill_name>", "args": {{"key": "value"}}, "speak": "<brief natural spoken response>"}}

**For general conversation, advice, or questions you can answer directly:**
{{"skill": "general_chat", "args": {{}}, "speak": "<your warm, knowledgeable, conversational answer>"}}

## ARG EXAMPLES PER SKILL:
- open_app: {{"app": "Chrome"}}
- play_youtube: {{"query": "Shape of You Ed Sheeran"}}
- find_file: {{"name": "resume"}}
- set_reminder: {{"content": "call mom", "time": "30 minutes"}}
- send_email: {{"to": "friend@example.com", "subject": "Hello", "body": "..."}}
- whatsapp_message: {{"contact": "Mom", "message": "I'll be late", "phone": ""}}
- generate_image: {{"prompt": "futuristic Iron Man suit on Mars"}}
- web_research: {{"query": "latest news on AI"}}
- google_search: {{"query": "best restaurants near me"}}
- stock_price: {{"symbol": "Tesla"}}
- morning_briefing: {{}}
- get_schedule: {{}}
- maps_location: {{"location": "Eiffel Tower Paris"}}
- wikipedia: {{"query": "Black holes"}}
- download_youtube: {{"url": "https://youtube.com/..."}}
- switch_voice: {{"gender": "female"}}
- lock_screen: {{}}
- minimize_all: {{}}

## RULES:
1. For skill actions (open, play, search, send, etc.) keep "speak" to 1-2 sentences — it's a spoken confirmation.
2. For general_chat (questions, explanations, plans, advice) write a COMPLETE, detailed answer in "speak" — do not truncate or summarize, give the full response.
3. Never use markdown symbols (**, ##, ---) or bullet points using * or - in "speak". Use plain numbered lists or plain prose instead.
4. Be warm and personal — you know {_USER_NAME} well.
5. If the user wants you to DO something (open, play, search, send, create), pick a skill.
6. If it's a question, explanation, or request for help you can answer directly, use general_chat.
7. For ambiguous requests, pick the most likely skill and proceed confidently.
8. Never output anything outside the JSON object."""


def _trim_history(history: list[dict], max_chars: int = 6000) -> list[dict]:
    """
    Keep as many recent messages as fit within max_chars total.
    Trims from the oldest end so context stays fresh.
    """
    total = 0
    trimmed = []
    for msg in reversed(history):
        total += len(msg["content"])
        if total > max_chars:
            break
        trimmed.insert(0, msg)
    return trimmed


def ask(query: str, speak_callback=None) -> dict:
    """
    Send a query to MAX brain.
    Returns: dict with 'skill', 'args', 'speak'
    """
    log.info(f"Brain processing: {query}")

    raw_history = get_conversation(n=_MAX_HISTORY)
    history = _trim_history(raw_history)
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        log.debug(f"Brain raw response: {raw}")

        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        # Sometimes the model adds trailing text after the JSON — find the JSON block
        if raw.startswith("{"):
            # Find matching closing brace
            depth = 0
            end = 0
            for i, ch in enumerate(raw):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            raw = raw[:end]

        result = json.loads(raw)

        # Validate & fill defaults
        result.setdefault("skill", "general_chat")
        result.setdefault("args", {})
        result.setdefault("speak", "")

        # Store full query and response to conversation memory.
        # We store the raw LLM output (not just the short "speak" snippet)
        # so the model has coherent context on the next turn.
        add_message("user", query, _MAX_HISTORY)
        memory_content = result["speak"] or raw  # fall back to raw if speak is empty
        if memory_content:
            add_message("assistant", memory_content, _MAX_HISTORY)

        log.info(f"Intent: {result['skill']} | Response: {result['speak'][:80]}")
        return result

    except json.JSONDecodeError:
        log.warning(f"Brain returned non-JSON: {raw[:100]}")
        # Treat as general chat
        speak_text = raw[:400] if raw else "I'm not sure how to help with that."
        add_message("user", query, _MAX_HISTORY)
        add_message("assistant", speak_text, _MAX_HISTORY)
        return {"skill": "general_chat", "args": {}, "speak": speak_text}

    except Exception as e:
        log.error(f"Brain error: {e}")
        return {
            "skill": "general_chat",
            "args": {},
            "speak": f"I hit a small snag, but I'm still here. What else can I do for you?"
        }


def quick_chat(prompt: str) -> str:
    """Direct LLM call for internal use (summarization, motivation, etc.)."""
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": f"You are MAX, a friendly and witty AI assistant to {_USER_NAME}. Respond naturally, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"quick_chat error: {e}")
        return "Sorry, my brain hit a snag."
