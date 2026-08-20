"""
MAX 2.0 — Messaging Skill
WhatsApp via pywhatkit, clipboard, system notifications.
"""
import os
import json
import webbrowser
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)


@skill("whatsapp_message")
def whatsapp_message(args: dict, spoken: str) -> str:
    phone = args.get("phone", "") or args.get("number", "")
    contact = args.get("contact", "") or args.get("name", "") or args.get("to", "")
    message = args.get("message", "") or args.get("text", "") or args.get("content", "")

    if not message:
        from core.voice import take_command
        message = take_command(prompt=f"What should I say to {contact or 'them'}?")
    if not message:
        return "What should I send?"

    # If no phone number, open WhatsApp Web so user can select contact manually
    if not phone:
        log.info(f"No phone number for {contact}. Opening WhatsApp Web.")
        webbrowser.open("https://web.whatsapp.com")
        return (spoken or
                f"I don't have a phone number for {contact}. I've opened WhatsApp Web — "
                f"select the contact and send: '{message}'")

    # Ensure phone has country code
    if phone and not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")  # Default: India (+91)

    try:
        import pywhatkit as pwk
        import datetime
        now = datetime.datetime.now()
        # Schedule 1 minute from now (pywhatkit requires a future time)
        send_time = now + datetime.timedelta(minutes=1)
        pwk.sendwhatmsg(
            phone, message,
            send_time.hour, send_time.minute,
            wait_time=15, tab_close=True, close_time=5
        )
        return (spoken or
                f"WhatsApp message to {contact or phone} scheduled! It'll send in about a minute.")
    except ImportError:
        return "pywhatkit is not installed. Run: pip install pywhatkit"
    except Exception as e:
        log.error(f"WhatsApp error: {e}")
        # Fallback to opening WhatsApp Web
        webbrowser.open("https://web.whatsapp.com")
        return f"Opened WhatsApp Web. Please send manually: '{message}'"


@skill("whatsapp_open")
def whatsapp_open(args: dict, spoken: str) -> str:
    """Open WhatsApp Web in browser."""
    webbrowser.open("https://web.whatsapp.com")
    return spoken or "Opening WhatsApp Web!"


@skill("send_notification")
def send_notification(args: dict, spoken: str) -> str:
    """Show a Windows toast notification."""
    title = args.get("title", "MAX")
    message = args.get("message", "") or args.get("content", "")
    if not message:
        from core.voice import take_command
        message = take_command(prompt="What should the notification say?")
    if not message:
        return "What should the notification say?"
    try:
        import subprocess
        # PowerShell toast notification
        ps_cmd = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.Visible = $true
        $notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -s 5
        $notify.Dispose()
        '''
        subprocess.Popen(["powershell", "-Command", ps_cmd],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return spoken or f"Notification sent: {message}"
    except Exception as e:
        log.error(f"Notification error: {e}")
        return f"Couldn't send notification: {e}"
