"""
MAX 2.0 — Voice Engine
TTS: Microsoft Edge Neural TTS (edge-tts) — human-quality voices.
     Falls back to Windows SAPI if offline.
STT: SpeechRecognition + Google.
Wake-word: background polling loop.
"""

import asyncio
import json
import os
import tempfile
import threading
import queue
import subprocess
import time
import speech_recognition as sr
from core.logger import log

# Load config
_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path, "r") as f:
    _cfg = json.load(f)

_VOICE_CFG = _cfg.get("voice", {})
_WAKE_WORD  = _cfg.get("wake_word", "max").lower()

# ── TTS Engine ────────────────────────────────────────────────────────────────
# Primary:  Microsoft Edge Neural TTS (edge-tts) — real human-quality voices
#           en-US-GuyNeural (male), en-IN-NeerjaNeural (female)
# Fallback: Windows SAPI (offline — David/Zira desktop voices)

_tts_queue: queue.Queue = queue.Queue()

# Mutable so set_voice() takes effect immediately
_gender = _VOICE_CFG.get("gender", "male")
_rate   = _VOICE_CFG.get("rate", 175)
_volume = _VOICE_CFG.get("volume", 1.0)

# Edge-TTS neural voice names — change here to pick a different accent/voice
EDGE_VOICES = {
    "male":   "en-US-GuyNeural",      # Natural American male
    "female": "en-IN-NeerjaNeural",   # Natural Indian English female
}

# Callback references for GUI
_on_speak_start = None
_on_speak_end   = None


def set_speak_callbacks(on_start=None, on_end=None):
    """Register GUI callbacks for speaking state changes."""
    global _on_speak_start, _on_speak_end
    _on_speak_start = on_start
    _on_speak_end   = on_end


# ── Edge-TTS (primary) ───────────────────────────────────────────────────────

async def _edge_generate(text: str, voice: str, rate_pct: str, vol_pct: str) -> str:
    """Generate speech with Edge TTS, save to temp .mp3, return path."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate_pct, volume=vol_pct)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()
    await communicate.save(tmp_path)
    return tmp_path


def _play_mp3_mci(path: str) -> None:
    """
    Play an MP3 file synchronously using Windows MCI (winmm.dll).
    MCI is always available on Windows, handles MP3 natively, and
    the 'wait' flag blocks until audio finishes — no polling needed.
    """
    import ctypes
    mci = ctypes.windll.winmm.mciSendStringW
    alias = "max_tts"
    try:
        # Open the file as an MPEG audio device
        ret = mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
        if ret != 0:
            raise RuntimeError(f"MCI open failed: code {ret}")
        # Set volume (0-1000 in MCI)
        vol = int(_volume * 1000)
        mci(f'setaudio {alias} volume to {vol}', None, 0, None)
        # Play synchronously — blocks until fully done
        mci(f'play {alias} wait', None, 0, None)
        mci(f'close {alias}', None, 0, None)
    except Exception as e:
        log.warning(f"MCI playback failed ({e}), trying PowerShell fallback")
        try:
            mci(f'close {alias}', None, 0, None)
        except Exception:
            pass
        _mp3_powershell(path)


def _edge_speak(text: str) -> None:
    """Generate speech via Edge neural TTS and play with MCI."""
    voice    = EDGE_VOICES.get(_gender, "en-US-GuyNeural")
    rate_off = int((_rate - 150) * 0.5)
    rate_pct = f"+{rate_off}%" if rate_off >= 0 else f"{rate_off}%"

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tmp_path = loop.run_until_complete(
            _edge_generate(text, voice, rate_pct, "+0%")
        )
        loop.close()
    except Exception as e:
        log.error(f"Edge-TTS generate error: {e}")
        _sapi_speak(text)
        return

    try:
        _play_mp3_mci(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _mp3_powershell(path: str) -> None:
    """Play MP3 synchronously via PowerShell (emergency fallback)."""
    safe_path = path.replace("\\", "/")
    ps = (
        f'Add-Type -AssemblyName presentationCore; '
        f'$mp = New-Object System.Windows.Media.MediaPlayer; '
        f'$mp.Open([uri]"{safe_path}"); '
        f'$mp.Play(); '
        f'Start-Sleep -m 800; '
        f'while($mp.Position -lt $mp.NaturalDuration.TimeSpan){{Start-Sleep -m 100}}; '
        f'$mp.Close()'
    )
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=120
    )


# ── SAPI (offline fallback) ──────────────────────────────────────────────────

def _sapi_speak(text: str) -> None:
    """Speak via Windows SAPI (offline — David/Zira desktop voices)."""
    try:
        import win32com.client
        voice_obj = win32com.client.Dispatch("SAPI.SpVoice")
        tokens    = voice_obj.GetVoices()
        # Select David (male=0) or Zira (female=1) by index
        idx = 1 if (_gender == "female" and tokens.Count > 1) else 0
        voice_obj.Voice  = tokens.Item(idx)
        voice_obj.Rate   = max(-5, min(10, (_rate - 150) // 10))
        voice_obj.Volume = int(_volume * 100)
        voice_obj.Speak(text)
    except Exception as e:
        log.error(f"SAPI fallback error: {e}")
        # Absolute last resort: PowerShell one-liner
        safe = text.replace('"', "'").replace("\n", " ")
        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command",
             f'(New-Object -ComObject SAPI.SpVoice).Speak("{safe}")'],
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=60
        )


# ── TTS Worker Thread ────────────────────────────────────────────────────────

def _tts_worker():
    """
    Dedicated TTS thread.
    CoInitialize() is called once so both SAPI and WMP COM work in this thread.
    """
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception as e:
        log.warning(f"CoInitialize failed: {e}")

    log.info(f"TTS worker ready — voice: {EDGE_VOICES.get(_gender, 'en-US-GuyNeural')} (edge-tts)")

    while True:
        item = _tts_queue.get()
        if item is None:
            break
        text, done_event = item
        try:
            _edge_speak(text)
        except Exception as e:
            log.error(f"TTS worker error: {e}")
        finally:
            done_event.set()
            _tts_queue.task_done()

    try:
        import pythoncom
        pythoncom.CoUninitialize()
    except Exception:
        pass


# Start the single TTS worker thread at import time
_tts_thread = threading.Thread(target=_tts_worker, daemon=True, name="TTSWorker")
_tts_thread.start()



def speak(text: str) -> None:
    """
    Thread-safe TTS. Can be called from any thread.
    Blocks until the utterance is fully spoken.
    """
    if not text:
        return
    log.info(f"[MAX speaks] {text[:80]}")
    if _on_speak_start:
        _on_speak_start(text)
    done = threading.Event()
    _tts_queue.put((text, done))
    done.wait()                   # Block caller until speech finishes
    if _on_speak_end:
        _on_speak_end()


def set_voice(gender: str) -> None:
    """
    Switch voice gender immediately. Next speak() call will use the new voice.
    With edge-tts, no restart is needed — the voice is selected per-utterance.
    """
    global _gender
    _gender = gender.lower()
    new_voice = EDGE_VOICES.get(_gender, "en-US-GuyNeural")
    log.info(f"Voice switched to: {_gender} ({new_voice})")


def set_rate(rate: int) -> None:
    log.info(f"Rate change requested to: {rate} (takes effect on restart)")


# ── STT Engine ────────────────────────────────────────────────────────────────

_recognizer = sr.Recognizer()
_recognizer.pause_threshold = 1.0
_recognizer.energy_threshold = 200        # Lower = more sensitive (less shouting needed)
_recognizer.dynamic_energy_threshold = True  # Auto-adjusts to room noise
_recognizer.dynamic_energy_adjustment_damping = 0.15
_recognizer.dynamic_energy_ratio = 1.5

_on_listening = None
_on_recognized = None
_on_error = None


def set_stt_callbacks(on_listening=None, on_recognized=None, on_error=None):
    """Register GUI callbacks for listening state."""
    global _on_listening, _on_recognized, _on_error
    _on_listening = on_listening
    _on_recognized = on_recognized
    _on_error = on_error


def take_command(prompt: str = None, timeout: int = 8, phrase_limit: int = 10) -> str:
    """
    Listen for one voice command and return transcribed text.
    Returns empty string on failure.
    """
    if prompt:
        speak(prompt)

    with sr.Microphone() as source:
        log.debug("Adjusting for ambient noise...")
        _recognizer.adjust_for_ambient_noise(source, duration=0.5)

        if _on_listening:
            _on_listening()

        log.debug("Listening for command...")
        try:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            log.debug("Listening timed out")
            if _on_error:
                _on_error("Listening timed out")
            return ""

    try:
        log.debug("Recognizing...")
        query = _recognizer.recognize_google(audio, language='en-in')
        log.info(f"User said: {query}")
        if _on_recognized:
            _on_recognized(query)
        return query.lower()
    except sr.UnknownValueError:
        log.debug("Could not understand audio")
        if _on_error:
            _on_error("Didn't catch that")
        return ""
    except sr.RequestError as e:
        log.error(f"STT API error: {e}")
        if _on_error:
            _on_error("Speech service error")
        return ""


# ── Wake-Word Listener ────────────────────────────────────────────────────────

_wake_queue: queue.Queue = queue.Queue()
_wake_active = threading.Event()
_wake_active.set()
_wake_thread = None


def _wake_loop(on_wake_callback):
    """Background loop that listens for the wake word."""
    log.info(f"Wake-word listener started. Listening for: '{_WAKE_WORD}'")
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    recognizer.energy_threshold = 200        # Sensitive — no shouting needed
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    recognizer.dynamic_energy_ratio = 1.5

    while _wake_active.is_set():
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language='en-in').lower()
            log.debug(f"Wake listener heard: {text}")
            # Use word-boundary check so "max" in e.g. "maximize" doesn't trigger
            words = text.split()
            if _WAKE_WORD in words or _WAKE_WORD in text:
                log.info("Wake word detected!")
                on_wake_callback()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            pass
        except sr.RequestError as e:
            log.warning(f"Wake-word STT error: {e}")
        except Exception as e:
            log.error(f"Wake-word loop error: {e}")


def start_wake_listener(on_wake_callback):
    """Start wake-word polling in a background daemon thread."""
    global _wake_thread
    _wake_active.set()
    _wake_thread = threading.Thread(
        target=_wake_loop,
        args=(on_wake_callback,),
        daemon=True,
        name="WakeWordListener"
    )
    _wake_thread.start()
    return _wake_thread


def stop_wake_listener():
    """Stop the wake-word listener."""
    _wake_active.clear()
    log.info("Wake-word listener stopped.")
