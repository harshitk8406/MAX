"""
MAX 2.0 — Jokes Skill
"""
import pyjokes
from skills.router import skill
from core.logger import log


@skill("joke")
def tell_joke(args: dict, spoken: str) -> str:
    category = args.get("category", "neutral")  # neutral, chuck, all
    lang = args.get("lang", "en")
    try:
        joke = pyjokes.get_joke(language=lang, category=category)
        log.info(f"Telling joke: {joke[:50]}")
        return joke
    except Exception as e:
        log.error(f"Joke error: {e}")
        return "Why did the programmer quit? Because he didn't get arrays!"
