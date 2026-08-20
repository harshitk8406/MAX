"""
MAX 2.0 — Web Research Skill
Autonomously fetch, parse, and summarize web content using the LLM.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)


def _fetch_text(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return cleaned plain text."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except ImportError:
        # Fallback without bs4
        try:
            import requests
            resp = requests.get(url, timeout=8)
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        except Exception as e:
            log.error(f"Fetch fallback failed: {e}")
            return ""
    except Exception as e:
        log.error(f"Fetch error for {url}: {e}")
        return ""


def _google_first_url(query: str) -> str:
    """Get the first organic Google result URL (no API key needed)."""
    try:
        import requests
        from bs4 import BeautifulSoup
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}&num=3"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/url?q="):
                actual = href.split("/url?q=")[1].split("&")[0]
                if actual.startswith("http") and "google" not in actual:
                    return urllib.parse.unquote(actual)
        return ""
    except Exception as e:
        log.error(f"Google search failed: {e}")
        return ""


def _summarize_with_llm(content: str, question: str) -> str:
    """Ask the LLM to summarize content in context of the question."""
    try:
        from core.brain import quick_chat
        prompt = f"""You are MAX. The user asked: "{question}"

Here is the raw web content I fetched:
---
{content[:3000]}
---

Give a concise, helpful answer based on the content above. Keep it under 4 sentences, no markdown, speak naturally."""
        return quick_chat(prompt)
    except Exception as e:
        log.error(f"LLM summarize error: {e}")
        return content[:300] + "..."


@skill("web_research")
def web_research(args: dict, spoken: str) -> str:
    import concurrent.futures
    query = args.get("query", "") or args.get("topic", "")
    if not query:
        from core.voice import take_command
        query = take_command(prompt="What should I research?")
    if not query:
        return "What would you like me to look up?"

    # Speak immediately so user knows MAX heard them
    from core.voice import speak
    speak(f"Searching for {query}. Give me a moment.")

    log.info(f"Web research: {query}")

    def _do_research():
        url = _google_first_url(query)
        if not url:
            return f"I couldn't find a good source for '{query}'. Try Google directly."
        content = _fetch_text(url)
        if not content:
            return "I found a page but couldn't read its content."
        return _summarize_with_llm(content, query)

    # 15-second hard timeout — always return something
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_do_research)
        try:
            return future.result(timeout=15)
        except concurrent.futures.TimeoutError:
            return f"That search took too long. Try asking me to Google '{query}' instead."
        except Exception as e:
            log.error(f"Web research error: {e}")
            return f"I ran into an error while searching. {str(e)[:60]}"


@skill("summarize_url")
def summarize_url(args: dict, spoken: str) -> str:
    url = args.get("url", "") or args.get("link", "")
    question = args.get("question", "Summarize this page")
    if not url:
        from core.voice import take_command
        url = take_command(prompt="What URL should I summarize?")
    if not url:
        return "I need a URL to summarize."

    log.info(f"Summarizing URL: {url}")
    content = _fetch_text(url)
    if not content:
        return "I couldn't read that page."
    return _summarize_with_llm(content, question)


@skill("stock_price")
def stock_price(args: dict, spoken: str) -> str:
    symbol = args.get("symbol", "") or args.get("company", "") or args.get("stock", "")
    if not symbol:
        from core.voice import take_command
        symbol = take_command(prompt="Which stock should I look up?")
    if not symbol:
        return "Which stock should I check?"

    query = f"{symbol} stock price today"
    url = _google_first_url(query)
    if url:
        content = _fetch_text(url, max_chars=2000)
        return _summarize_with_llm(content, f"What is the current stock price of {symbol}?")
    return spoken or f"Couldn't fetch stock data for {symbol}."


@skill("sports_score")
def sports_score(args: dict, spoken: str) -> str:
    team = args.get("team", "") or args.get("match", "")
    if not team:
        from core.voice import take_command
        team = take_command(prompt="Which team or sport should I check?")
    if not team:
        return "Which team should I check scores for?"

    query = f"{team} latest score today"
    url = _google_first_url(query)
    if url:
        content = _fetch_text(url, max_chars=2000)
        return _summarize_with_llm(content, f"What is the latest score for {team}?")
    return spoken or f"Couldn't fetch scores for {team}."
