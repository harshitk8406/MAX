"""
MAX 2.0 — Spotify Skill
Control Spotify playback via spotipy (Spotify Web API).
Requires client_id, client_secret in config.json.
"""
import json
import os
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_SP_CFG = _cfg.get("spotify", {})
_CLIENT_ID = _SP_CFG.get("client_id", "")
_CLIENT_SECRET = _SP_CFG.get("client_secret", "")
_REDIRECT_URI = _SP_CFG.get("redirect_uri", "http://localhost:8888/callback")
_SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

_sp = None


def _get_spotify():
    """Lazy-init Spotify client."""
    global _sp
    if _sp is not None:
        return _sp

    if not _CLIENT_ID or _CLIENT_ID == "YOUR_SPOTIFY_CLIENT_ID":
        return None

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        auth = SpotifyOAuth(
            client_id=_CLIENT_ID,
            client_secret=_CLIENT_SECRET,
            redirect_uri=_REDIRECT_URI,
            scope=_SCOPE,
            open_browser=True,
            cache_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".spotify_cache")
        )
        _sp = spotipy.Spotify(auth_manager=auth)
        log.info("Spotify client initialized")
        return _sp
    except ImportError:
        log.warning("spotipy not installed. Run: pip install spotipy")
        return None
    except Exception as e:
        log.error(f"Spotify init error: {e}")
        return None


@skill("spotify_play")
def spotify_play(args: dict, spoken: str) -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify isn't configured yet. Add your Spotify credentials to config.json."

    track = args.get("track", "")
    artist = args.get("artist", "")

    try:
        if track:
            query = f"track:{track}"
            if artist:
                query += f" artist:{artist}"
            results = sp.search(q=query, limit=1, type="track")
            items = results.get("tracks", {}).get("items", [])
            if items:
                uri = items[0]["uri"]
                sp.start_playback(uris=[uri])
                name = items[0]["name"]
                art = items[0]["artists"][0]["name"]
                return spoken or f"Playing {name} by {art} on Spotify!"
            return f"I couldn't find {track} on Spotify."
        else:
            sp.start_playback()
            return spoken or "Resuming Spotify!"
    except Exception as e:
        log.error(f"Spotify play error: {e}")
        return "Spotify playback failed. Make sure Spotify is open on a device."


@skill("spotify_pause")
def spotify_pause(args: dict, spoken: str) -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.pause_playback()
        return spoken or "Paused Spotify."
    except Exception as e:
        log.error(f"Spotify pause error: {e}")
        return "Couldn't pause Spotify."


@skill("spotify_next")
def spotify_next(args: dict, spoken: str) -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify isn't configured."
    try:
        sp.next_track()
        return spoken or "Skipped to next track!"
    except Exception as e:
        log.error(f"Spotify next error: {e}")
        return "Couldn't skip track."


@skill("youtube_download")
def youtube_download(args: dict, spoken: str) -> str:
    """Launch the YouTube downloader GUI."""
    base = os.path.dirname(os.path.dirname(__file__))
    dl_script = os.path.join(base, "youtube_downloader.py")
    if os.path.exists(dl_script):
        import subprocess
        subprocess.Popen(["python", dl_script])
        return spoken or "Opening YouTube Downloader!"
    return "YouTube downloader not found."


@skill("general_chat")
def general_chat(args: dict, spoken: str) -> str:
    """Fallback — just return the LLM-generated spoken text."""
    return spoken
