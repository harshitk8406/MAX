"""
MAX 2.0 — Dictionary Skill
Offline dictionary with fuzzy spell-check using data.json
"""
import json
import os
from difflib import get_close_matches
from skills.router import skill
from core.logger import log

_base = os.path.dirname(os.path.dirname(__file__))
_data_path = os.path.join(_base, "data.json")

_data: dict = {}
try:
    with open(_data_path, "r", encoding="utf-8") as f:
        _data = json.load(f)
    log.info(f"Dictionary loaded: {len(_data)} words")
except FileNotFoundError:
    log.warning("data.json not found — dictionary skill disabled")
except Exception as e:
    log.error(f"Dictionary load error: {e}")


@skill("dictionary")
def look_up(args: dict, spoken: str) -> str:
    word = args.get("word", "").lower().strip()

    if not _data:
        return "The dictionary file is missing. Please ensure data.json is present."

    if not word:
        from core.voice import take_command
        word = take_command(prompt="What word would you like me to define?").strip()

    if not word:
        return "I didn't catch the word."

    if word in _data:
        definition = _data[word]
        if isinstance(definition, list):
            definition = definition[0]
        return f"{word}: {definition}"

    # Fuzzy match
    suggestions = get_close_matches(word, _data.keys(), n=1, cutoff=0.7)
    if suggestions:
        suggested = suggestions[0]
        definition = _data[suggested]
        if isinstance(definition, list):
            definition = definition[0]
        return (f"I didn't find '{word}' exactly. Did you mean '{suggested}'? "
                f"Definition: {definition}")

    return f"I couldn't find a definition for '{word}'. Double-check the spelling."
