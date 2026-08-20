"""
MAX 2.0 — Browser Skills
Open websites, Google search, YouTube, Maps.
"""
import json
import os
import webbrowser
import urllib.parse
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_chrome = _cfg.get("chrome_path", "")

def _open(url: str):
    """Open URL — try Chrome first, fallback to default browser."""
    try:
        if _chrome and os.path.exists(_chrome):
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(_chrome))
            webbrowser.get('chrome').open_new_tab(url)
        else:
            webbrowser.open_new_tab(url)
    except Exception as e:
        log.warning(f"Browser open failed: {e}, falling back to default")
        webbrowser.open(url)


@skill("open_youtube")
def open_youtube(args: dict, spoken: str) -> str:
    _open("https://youtube.com")
    return spoken or "Opening YouTube!"


@skill("open_amazon")
def open_amazon(args: dict, spoken: str) -> str:
    _open("https://amazon.in")
    return spoken or "Opening Amazon!"


@skill("open_google")
def open_google(args: dict, spoken: str) -> str:
    _open("https://google.com")
    return spoken or "Opening Google!"


@skill("open_stackoverflow")
def open_stackoverflow(args: dict, spoken: str) -> str:
    _open("https://stackoverflow.com")
    return spoken or "Opening Stack Overflow!"


@skill("open_github")
def open_github(args: dict, spoken: str) -> str:
    url = args.get("username", "")
    _open(f"https://github.com/{url}" if url else "https://github.com")
    return spoken or "Opening GitHub!"


@skill("search_youtube")
def search_youtube(args: dict, spoken: str) -> str:
    query = args.get("query", "")
    if not query:
        from core.voice import take_command
        query = take_command(prompt="What should I search on YouTube?")
    if query:
        encoded = urllib.parse.quote(query)
        _open(f"https://www.youtube.com/results?search_query={encoded}")
        return spoken or f"Searching YouTube for {query}"
    return "I didn't catch what to search for."


@skill("google_search")
def google_search(args: dict, spoken: str) -> str:
    query = args.get("query", "")
    if not query:
        from core.voice import take_command
        query = take_command(prompt="What should I search for?")
    if query:
        encoded = urllib.parse.quote(query)
        _open(f"https://google.com/search?q={encoded}")
        return spoken or f"Here's what I found for {query}"
    return "I didn't catch what to search for."


@skill("maps_location")
def maps_location(args: dict, spoken: str) -> str:
    location = args.get("location", "")
    if not location:
        from core.voice import take_command
        location = take_command(prompt="What location should I show?")
    if location:
        encoded = urllib.parse.quote(location)
        _open(f"https://www.google.com/maps/search/{encoded}")
        return spoken or f"Opening maps for {location}"
    return "I didn't get a location."


@skill("open_vscode")
def open_vscode(args: dict, spoken: str) -> str:
    import subprocess
    try:
        subprocess.Popen(["code", "."])
        return spoken or "Opening VS Code!"
    except FileNotFoundError:
        # Try common Windows paths
        paths = [
            r"C:\Users\harsh\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                os.startfile(p)
                return spoken or "Opening VS Code!"
        return "VS Code not found. Is it installed?"
