"""
MAX 2.0 — PC Automation & App Control Skill
Open/close/switch apps, type text, control system, clipboard.
"""
import os
import platform
import subprocess
import time
from skills.router import skill
from core.logger import log

# Map of common app names → executable paths / commands
_APP_MAP = {
    # Browsers
    "chrome":        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":       r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    # System
    "notepad":       "notepad.exe",
    "calculator":    "calc.exe",
    "paint":         "mspaint.exe",
    "task manager":  "taskmgr.exe",
    "taskmgr":       "taskmgr.exe",
    "explorer":      "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd":           "cmd.exe",
    "command prompt":"cmd.exe",
    "terminal":      "wt.exe",            # Windows Terminal
    "powershell":    "powershell.exe",
    "control panel": "control.exe",
    "settings":      "ms-settings:",
    "snipping tool": "SnippingTool.exe",
    "camera":        "microsoft.windows.camera:",
    "clock":         "ms-clock:",
    "photos":        "ms-photos:",
    "store":         "ms-windows-store:",
    "mail":          "outlookmail:",
    # Office
    "word":          r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":         r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":    r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "outlook":       r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    "onenote":       r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE",
    # Dev
    "vscode":        r"C:\Users\harsh\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vs code":       r"C:\Users\harsh\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "visual studio code": r"C:\Users\harsh\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    # Social/Media
    "spotify":       os.path.join(os.environ.get("APPDATA", ""), r"Spotify\Spotify.exe"),
    "discord":       os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Discord\Update.exe"),
    "whatsapp":      os.path.join(os.environ.get("LOCALAPPDATA", ""), r"WhatsApp\WhatsApp.exe"),
    "telegram":      os.path.join(os.environ.get("APPDATA", ""), r"Telegram Desktop\Telegram.exe"),
    "zoom":          os.path.join(os.environ.get("APPDATA", ""), r"Zoom\bin\Zoom.exe"),
    "teams":         os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Teams\current\Teams.exe"),
}


def _launch(app_name: str) -> bool:
    """
    Try to launch an app. Resolution order:
    1. Known path from _APP_MAP
    2. ms-protocol:// / URI shortcuts
    3. Try as a direct exe in PATH
    4. PowerShell Start-Process (finds any installed app by name) ← most powerful
    5. Windows 'start' shell command
    """
    key = app_name.lower().strip()

    # 1. Lookup in map
    exe = _APP_MAP.get(key, "")
    if exe:
        if exe.endswith(":") or exe.startswith("ms-"):   # URI protocol
            os.startfile(exe)
            return True
        if os.path.exists(exe):
            subprocess.Popen([exe])
            return True

    # 2. Try as a bare executable (covers apps in PATH: notepad, calc, etc.)
    try:
        subprocess.Popen(app_name, shell=False)
        return True
    except Exception:
        pass

    # 3. PowerShell Start-Process — searches registered apps, Start Menu, PATH
    try:
        result = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command",
             f'Start-Process "{app_name}"'],
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=6
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # 4. Windows shell 'start' command (last resort)
    try:
        subprocess.Popen(f'start "" "{app_name}"', shell=True)
        return True
    except Exception:
        pass

    return False



@skill("open_app")
def open_app(args: dict, spoken: str) -> str:
    app = args.get("app", "") or args.get("name", "")
    if not app:
        from core.voice import take_command
        app = take_command(prompt="Which app should I open?")
    if not app:
        return "I didn't catch an app name."

    log.info(f"Opening app: {app}")
    if _launch(app):
        return spoken or f"Opening {app}!"
    return spoken or f"I couldn't find {app}. Make sure it's installed."


@skill("close_app")
def close_app(args: dict, spoken: str) -> str:
    app = args.get("app", "") or args.get("name", "")
    if not app:
        from core.voice import take_command
        app = take_command(prompt="Which app should I close?")
    if not app:
        return "Which app should I close?"

    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(app)
        if windows:
            for w in windows:
                w.close()
            return spoken or f"Closed {app}."
        # Fallback: taskkill
        subprocess.run(["taskkill", "/F", "/IM", f"{app}.exe"], capture_output=True)
        return spoken or f"Closed {app}."
    except ImportError:
        subprocess.run(["taskkill", "/F", "/IM", f"{app}.exe"], capture_output=True)
        return spoken or f"Attempted to close {app}."
    except Exception as e:
        log.error(f"Close app error: {e}")
        return f"Couldn't close {app}: {e}"


@skill("switch_window")
def switch_window(args: dict, spoken: str) -> str:
    app = args.get("app", "") or args.get("name", "")
    if not app:
        from core.voice import take_command
        app = take_command(prompt="Which window should I switch to?")
    if not app:
        return "Which window should I switch to?"

    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(app)
        if windows:
            win = windows[0]
            win.activate()
            return spoken or f"Switched to {win.title}."
        return f"No window found matching '{app}'."
    except ImportError:
        # Fallback: Alt+Tab simulation
        import pyautogui
        pyautogui.hotkey('alt', 'tab')
        return spoken or "Switched to the next window."
    except Exception as e:
        return f"Window switch failed: {e}"


@skill("type_text")
def type_text(args: dict, spoken: str) -> str:
    text = args.get("text", "") or args.get("content", "")
    if not text:
        from core.voice import take_command
        text = take_command(prompt="What should I type?")
    if not text:
        return "What should I type?"
    try:
        import pyautogui
        time.sleep(0.5)  # Brief delay so focus settles
        pyautogui.write(text, interval=0.03)
        return spoken or f"Typed: {text[:40]}"
    except Exception as e:
        return f"Typing failed: {e}"


@skill("copy_clipboard")
def copy_clipboard(args: dict, spoken: str) -> str:
    """Copy currently selected text to clipboard."""
    try:
        import pyautogui
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.3)
        import subprocess
        result = subprocess.run(['powershell', '-command', 'Get-Clipboard'], capture_output=True, text=True)
        content = result.stdout.strip()[:100]
        return spoken or f"Copied to clipboard: {content}" if content else "Clipboard is empty or copy failed."
    except Exception as e:
        return f"Clipboard error: {e}"


@skill("lock_screen")
def lock_screen(args: dict, spoken: str) -> str:
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return spoken or "Locking your screen now."
    except Exception as e:
        return f"Couldn't lock screen: {e}"


@skill("minimize_all")
def minimize_all(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        pyautogui.hotkey('win', 'd')
        return spoken or "Minimized all windows. You've got a clean desktop now."
    except Exception as e:
        return f"Couldn't minimize windows: {e}"


@skill("increase_volume")
def increase_volume(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        pyautogui.press('volumeup', presses=5)
        return spoken or "Volume increased!"
    except Exception as e:
        return f"Volume control failed: {e}"


@skill("decrease_volume")
def decrease_volume(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        pyautogui.press('volumedown', presses=5)
        return spoken or "Volume decreased!"
    except Exception as e:
        return f"Volume control failed: {e}"


@skill("mute_volume")
def mute_volume(args: dict, spoken: str) -> str:
    try:
        import pyautogui
        pyautogui.press('volumemute')
        return spoken or "Toggled mute."
    except Exception as e:
        return f"Mute failed: {e}"


@skill("take_screenshot")
def take_screenshot(args: dict, spoken: str) -> str:
    try:
        import pyautogui, datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.expanduser("~\\Desktop"), f"max_screenshot_{ts}.png")
        img = pyautogui.screenshot()
        img.save(path)
        return spoken or f"Screenshot saved to your Desktop as max_screenshot_{ts}.png"
    except Exception as e:
        return f"Screenshot failed: {e}"


@skill("empty_recycle_bin")
def empty_recycle_bin(args: dict, spoken: str) -> str:
    try:
        import winreg
        subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                       capture_output=True)
        return spoken or "Recycle bin emptied!"
    except Exception as e:
        return f"Couldn't empty recycle bin: {e}"


@skill("restart_explorer")
def restart_explorer(args: dict, spoken: str) -> str:
    """Restart Windows Explorer (fixes frozen taskbar/desktop)."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True)
        time.sleep(1)
        subprocess.Popen("explorer.exe")
        return spoken or "Restarted Windows Explorer. Your taskbar should be back."
    except Exception as e:
        return f"Couldn't restart Explorer: {e}"
