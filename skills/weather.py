"""
MAX 2.0 — Weather Skill
Uses OpenWeatherMap API with geocoder IP-based location detection.
"""
import json
import os
import requests
import geocoder
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_OWM_KEY = _cfg.get("weather", {}).get("api_key", "")
_OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

# Fallback URL (no-key, limited)
_FALLBACK_URL = "https://fcc-weather-api.glitch.me/api/current"


def _fetch_weather(lat: float, lon: float) -> dict:
    """Fetch weather data, trying OpenWeatherMap first then fallback."""
    if _OWM_KEY and _OWM_KEY != "YOUR_OPENWEATHERMAP_KEY_HERE":
        try:
            r = requests.get(_OWM_URL, params={
                "lat": lat, "lon": lon, "appid": _OWM_KEY,
                "units": "metric"
            }, timeout=6)
            data = r.json()
            if data.get("cod") == 200:
                return data
        except Exception as e:
            log.warning(f"OWM API failed: {e}")

    # Fallback
    try:
        r = requests.get(_FALLBACK_URL, params={"lat": lat, "lon": lon}, timeout=6)
        return r.json()
    except Exception as e:
        log.error(f"Fallback weather failed: {e}")
        return {}


@skill("weather")
def get_weather(args: dict, spoken: str) -> str:
    try:
        city = args.get("city", "")
        if city and _OWM_KEY and _OWM_KEY != "YOUR_OPENWEATHERMAP_KEY_HERE":
            r = requests.get(_OWM_URL, params={
                "q": city, "appid": _OWM_KEY, "units": "metric"
            }, timeout=6)
            data = r.json()
        else:
            g = geocoder.ip("me")
            if not g.latlng:
                return "I can't detect your location right now."
            data = _fetch_weather(g.latlng[0], g.latlng[1])

        if not data or data.get("cod") not in (200, "200"):
            return "Weather data isn't available at the moment."

        loc = data.get("name", "your location")
        main = data.get("main", {})
        weather_list = data.get("weather", [{}])
        wind = data.get("wind", {})

        temp = round(main.get("temp", 0))
        feels = round(main.get("feels_like", 0))
        humidity = main.get("humidity", 0)
        desc = weather_list[0].get("description", "").capitalize()
        wind_speed = wind.get("speed", 0)

        return (spoken or
                f"In {loc}, it's {temp}°C and feels like {feels}°C. "
                f"{desc}. Humidity is {humidity}% with wind at {wind_speed} m/s.")

    except Exception as e:
        log.error(f"Weather skill error: {e}")
        return "I had trouble fetching the weather. Check your API key in config."
