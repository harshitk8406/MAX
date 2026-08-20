"""
MAX 2.0 — Wikipedia Skill
"""
import wikipedia
from skills.router import skill
from core.logger import log


@skill("wikipedia")
def search_wikipedia(args: dict, spoken: str) -> str:
    query = args.get("query", "")
    sentences = args.get("sentences", 2)
    if not query:
        return spoken or "What would you like me to look up on Wikipedia?"
    try:
        wikipedia.set_lang("en")
        results = wikipedia.summary(query, sentences=int(sentences), auto_suggest=True)
        log.info(f"Wikipedia result for '{query}': {results[:60]}...")
        return results
    except wikipedia.exceptions.DisambiguationError as e:
        # Pick the first option
        try:
            results = wikipedia.summary(e.options[0], sentences=int(sentences))
            return results
        except Exception:
            return f"There are multiple results for {query}. Can you be more specific?"
    except wikipedia.exceptions.PageError:
        return f"I couldn't find a Wikipedia page for {query}."
    except Exception as e:
        log.error(f"Wikipedia error: {e}")
        return "I had trouble accessing Wikipedia right now."
