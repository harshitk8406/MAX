"""
MAX 2.0 — System Skills
CPU/battery status, screenshot, shutdown, volume, app launcher.
"""
import os
import json
import datetime
import platform
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
os.makedirs(_SCREENSHOTS_DIR, exist_ok=True)


@skill("cpu_status")
def cpu_status(args: dict, spoken: str) -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        ram_used = round(ram.used / (1024**3), 1)
        ram_total = round(ram.total / (1024**3), 1)
        battery = psutil.sensors_battery()
        bat_info = ""
        if battery:
            charging = "charging" if battery.power_plugged else "on battery"
            bat_info = f" Battery is at {int(battery.percent)}% and {charging}."
        return (spoken or
                f"CPU is at {cpu}% usage. RAM is {ram_used} of {ram_total} gigabytes used.{bat_info}")
    except ImportError:
        return "psutil is not installed. Run pip install psutil."
    except Exception as e:
        log.error(f"CPU status error: {e}")
        return "Couldn't fetch system stats right now."


@skill("screenshot")
def take_screenshot(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(_SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
        img = pyautogui.screenshot()
        img.save(path)
        log.info(f"Screenshot saved: {path}")
        return spoken or f"Screenshot saved to the screenshots folder."
    except ImportError:
        return "pyautogui is not installed."
    except Exception as e:
        log.error(f"Screenshot error: {e}")
        return "Failed to take screenshot."


@skill("time")
def tell_time(args: dict, spoken: str) -> str:
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d")
    return spoken or f"It's {time_str} on {date_str}."


@skill("shutdown")
def shutdown_system(args: dict, spoken: str) -> str:
    import sys
    delay = args.get("delay", 30)
    if platform.system() == "Windows":
        os.system(f'shutdown /s /t {delay}')
    else:
        os.system('poweroff')
    return spoken or f"Initiating shutdown in {delay} seconds."


@skill("play_music")
def play_music(args: dict, spoken: str) -> str:
    folder = _cfg.get("music", {}).get("folder", "")
    song = args.get("song", "")

    if song and folder:
        import glob
        matches = glob.glob(os.path.join(folder, f"*{song}*"))
        if matches:
            os.startfile(matches[0])
            return spoken or f"Playing {os.path.basename(matches[0])}"

    if folder and os.path.isdir(folder):
        import random, glob
        songs = glob.glob(os.path.join(folder, "*.mp3")) + \
                glob.glob(os.path.join(folder, "*.flac")) + \
                glob.glob(os.path.join(folder, "*.wav"))
        if songs:
            chosen = random.choice(songs)
            os.startfile(chosen)
            return spoken or f"Playing {os.path.basename(chosen)}"

    return "I couldn't find any music files. Update your music folder in config.json."


@skill("volume_up")
def volume_up(args: dict, spoken: str) -> str:
    try:
        if platform.system() == "Windows":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            current = volume.GetMasterVolumeLevelScalar()
            new_vol = min(1.0, current + 0.1)
            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return spoken or f"Volume increased to {int(new_vol*100)}%."
    except Exception as e:
        log.warning(f"Volume control: {e}")
    # Fallback using pyautogui keys
    try:
        import pyautogui
        pyautogui.press('volumeup', presses=3)
        return spoken or "Volume turned up!"
    except Exception:
        return "Volume control not available."


@skill("volume_down")
def volume_down(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        pyautogui.press('volumedown', presses=3)
        return spoken or "Volume turned down!"
    except Exception:
        return "Volume control not available."


@skill("switch_voice")
def switch_voice(args: dict, spoken: str) -> str:
    gender = args.get("gender", "male").lower()
    from core.voice import set_voice
    set_voice(gender)
    name = "FRIDAY" if gender == "female" else "MAX"
    return spoken or f"Switched to {name} mode. How's this?"


@skill("file_manager")
def file_manager(args: dict, spoken: str) -> str:
    action = args.get("action", "open")
    path = args.get("path", os.path.expanduser("~"))

    if action == "open" and os.path.exists(path):
        os.startfile(path)
        return spoken or f"Opening {path}"
    elif action == "list" and os.path.isdir(path):
        files = os.listdir(path)[:10]
        file_list = ", ".join(files)
        return spoken or f"Here are the files in that folder: {file_list}"
    return spoken or "I couldn't find that path."
