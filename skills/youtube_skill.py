"""
MAX 2.0 — YouTube Smart Skill
Search + open specific videos, download via yt-dlp, summarize content.
"""
import json
import os
import urllib.parse
import webbrowser
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_chrome = _cfg.get("chrome_path", "")


def _open_url(url: str):
    try:
        if _chrome and os.path.exists(_chrome):
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(_chrome))
            webbrowser.get('chrome').open_new_tab(url)
        else:
            webbrowser.open_new_tab(url)
    except Exception:
        webbrowser.open(url)


def _search_youtube_api(query: str) -> str:
    """Get the first YouTube video URL for a query (no API key via web scraping)."""
    try:
        import requests
        from bs4 import BeautifulSoup
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=8)
        # Find video IDs in response
        import re
        ids = re.findall(r'"videoId":"([^"]+)"', resp.text)
        if ids:
            return f"https://www.youtube.com/watch?v={ids[0]}"
    except Exception as e:
        log.error(f"YouTube search error: {e}")
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"


@skill("play_youtube")
def play_youtube(args: dict, spoken: str) -> str:
    query = args.get("query", "") or args.get("song", "") or args.get("video", "")
    if not query:
        from core.voice import take_command
        query = take_command(prompt="What should I play on YouTube?")
    if not query:
        return "What should I play?"

    log.info(f"YouTube play: {query}")
    url = _search_youtube_api(query)
    _open_url(url)
    return spoken or f"Playing '{query}' on YouTube!"


@skill("search_youtube")
def search_youtube(args: dict, spoken: str) -> str:
    query = args.get("query", "") or args.get("search", "")
    if not query:
        from core.voice import take_command
        query = take_command(prompt="What should I search for on YouTube?")
    if not query:
        return "What should I search on YouTube?"

    encoded = urllib.parse.quote(query)
    _open_url(f"https://www.youtube.com/results?search_query={encoded}")
    return spoken or f"Searching YouTube for '{query}'!"


@skill("download_youtube")
def download_youtube(args: dict, spoken: str) -> str:
    url = args.get("url", "") or args.get("link", "")
    if not url:
        from core.voice import take_command
        url = take_command(prompt="Give me the YouTube URL to download.")
    if not url:
        return "I need a YouTube URL to download."

    # Ensure it looks like a URL
    if "youtube.com" not in url and "youtu.be" not in url:
        url = _search_youtube_api(url)

    download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "MAX_YouTube")
    os.makedirs(download_dir, exist_ok=True)

    try:
        import subprocess
        result = subprocess.Popen(
            ["yt-dlp", "-f", "best[height<=1080]", "-o",
             os.path.join(download_dir, "%(title)s.%(ext)s"), url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return spoken or f"Download started! It'll appear in your Downloads/MAX_YouTube folder."
    except FileNotFoundError:
        return "yt-dlp is not installed. Run: pip install yt-dlp"
    except Exception as e:
        log.error(f"YouTube download error: {e}")
        return f"Download failed: {e}"


@skill("youtube_transcript")
def youtube_transcript(args: dict, spoken: str) -> str:
    """Get transcript/summary of a YouTube video."""
    url = args.get("url", "") or args.get("link", "")
    query = args.get("query", "")

    if not url and query:
        url = _search_youtube_api(query)
    if not url:
        from core.voice import take_command
        url = take_command(prompt="Which YouTube video should I summarize?")
    if not url:
        return "I need a video URL or name."

    try:
        import subprocess
        result = subprocess.run(
            ["yt-dlp", "--write-auto-sub", "--sub-format", "vtt",
             "--skip-download", "--print", "description", url],
            capture_output=True, text=True, timeout=20
        )
        description = result.stdout.strip()[:2000]
        if description:
            from core.brain import quick_chat
            summary = quick_chat(f"Summarize this YouTube video description in 3 sentences:\n{description}")
            return summary
        return "Couldn't fetch the video description."
    except Exception as e:
        log.error(f"Transcript error: {e}")
        return f"Couldn't summarize that video: {e}"
