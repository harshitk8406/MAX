"""
MAX 2.0 — News Skill
Fetches top headlines via NewsAPI.
"""
import json
import os
import requests
import webbrowser
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_NEWS_KEY = _cfg.get("news", {}).get("api_key", "")
_NEWS_SOURCE = _cfg.get("news", {}).get("source", "the-times-of-india")
_NEWS_URL = "https://newsapi.org/v2/top-headlines"

_cached_articles = []
_cached_url = ""


def _fetch_news(source: str = None, query: str = None) -> list:
    global _cached_articles, _cached_url
    params = {"apiKey": _NEWS_KEY}
    if source:
        params["sources"] = source
    elif query:
        params["q"] = query
        params["language"] = "en"
    else:
        params["sources"] = _NEWS_SOURCE

    try:
        r = requests.get(_NEWS_URL, params=params, timeout=6)
        data = r.json()
        if data.get("status") == "ok":
            _cached_articles = data.get("articles", [])
            _cached_url = f"https://newsapi.org/v2/top-headlines?sources={_NEWS_SOURCE}&apiKey={_NEWS_KEY}"
            return _cached_articles
        else:
            log.warning(f"NewsAPI error: {data.get('message')}")
            return []
    except Exception as e:
        log.error(f"News fetch error: {e}")
        return []


@skill("news")
def get_news(args: dict, spoken: str) -> str:
    source = args.get("source", _NEWS_SOURCE)
    query = args.get("query", "")
    articles = _fetch_news(source=source if not query else None, query=query)

    if not articles:
        return "I couldn't fetch the news right now. Check your NewsAPI key."

    # Build spoken summary of top 5 headlines
    headlines = [a["title"] for a in articles[:5] if a.get("title")]
    if not headlines:
        return "No headlines found."

    summary = "Here are today's top headlines. "
    for i, h in enumerate(headlines, 1):
        summary += f"Headline {i}: {h}. "

    summary += "Would you like me to open the full news page?"

    # Store globally so voice loop can open URL if user says yes
    return summary


def open_news_url() -> None:
    global _cached_url
    if _cached_url:
        webbrowser.open(_cached_url)
    else:
        webbrowser.open("https://timesofindia.indiatimes.com")


def get_cached_url() -> str:
    return _cached_url
