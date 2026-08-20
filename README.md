# M.A.X 2.0

<h1 align="center">
  <br>◈ M.A.X 2.0◈<br>
  <sub>Machine Autonomous eXpert</sub>
</h1>

<div align="center">
  <img src="jarvis1.jpg" width="600"/>
</div>

## ✨ What's New in 2.0

| Feature | Status |
|---------|--------|
| 🧠 Groq LLM (LLaMA 3.3 70B) AI Brain | ✅ |
| 🖥️ Iron Man HUD GUI (animated ring, waveform) | ✅ |
| 🗣️ Wake-word detection ("Hey MAX") | ✅ |
| 📝 Persistent memory & notes | ✅ |
| ⏰ Voice-activated reminders | ✅ |
| 🎵 Spotify integration | ✅ |
| 🌐 REST API (FastAPI) | ✅ |
| 📋 Rotating log system | ✅ |
| 🔧 Modular skills architecture | ✅ |
| ❌ Face recognition | Removed |

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

> **PyAudio on Windows**: Download the `.whl` from the project directory and install:
> ```bash
> pip install PyAudio-0.2.11-cp38-cp38-win_amd64.whl
> ```

### 2. Configure MAX

Copy the example config and fill in your API keys:
```bash
copy config.example.json config.json
```

Edit `config.json` and set:
- `groq.api_key` → Your [Groq API key](https://console.groq.com) (**required**)
- `news.api_key` → Your [NewsAPI key](https://newsapi.org) (optional)
- `weather.api_key` → Your [OpenWeatherMap key](https://openweathermap.org/api) (optional)
- `spotify.*` → Your [Spotify Developer app](https://developer.spotify.com) credentials (optional)
- `email.*` → Your Gmail + app password (optional)
- `user.name` → Your name

### 3. Run MAX
```bash
python main.py
```

## 🎯 Voice Commands

| Say... | Action |
|--------|--------|
| **"Hey MAX"** | Wake up MAX |
| **"What's the weather?"** | Current weather |
| **"Tell me the news"** | Top headlines |
| **"Play [song] on Spotify"** | Spotify playback |
| **"Search YouTube for [query]"** | YouTube search |
| **"Remember that [thing]"** | Save a note |
| **"Set a reminder for 10 minutes"** | Timed reminder |
| **"Tell me a joke"** | Random joke |
| **"What's the CPU usage?"** | System stats |
| **"Take a screenshot"** | Screen capture |
| **"Define [word]"** | Dictionary lookup |
| **"Look up [topic] on Wikipedia"** | Wikipedia search |
| **"Goodbye MAX"** | Shut down |

> **Anything else?** MAX uses the Groq LLM to answer any question!

## 🌐 REST API

When running, MAX exposes a REST API at `http://localhost:8000`:

```bash
# Ask MAX a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What time is it?"}'

# Get command history
curl http://localhost:8000/history

# Get notes
curl http://localhost:8000/notes
```

Interactive docs: `http://localhost:8000/docs`

## 📁 Project Structure

```
M.A.X/
├── main.py              # 🚀 Entry point
├── config.json          # ⚙️ Your settings (git-ignored)
├── core/
│   ├── brain.py         # 🧠 Groq LLM integration
│   ├── voice.py         # 🎙️ TTS + STT + wake-word
│   ├── memory.py        # 💾 Persistent memory
│   └── logger.py        # 📋 Logging system
├── skills/
│   ├── browser.py       # 🌐 Web browsing
│   ├── system.py        # 💻 System control
│   ├── weather.py       # ⛅ Weather
│   ├── news.py          # 📰 News
│   ├── wiki.py          # 📖 Wikipedia
│   ├── notes.py         # 📝 Notes & reminders
│   ├── jokes.py         # 😂 Jokes
│   ├── dictionary.py    # 📚 Dictionary
│   ├── email_skill.py   # 📧 Email
│   └── spotify.py       # 🎵 Spotify
├── gui/
│   └── app.py           # 🖥️ Iron Man HUD
├── api/
│   └── server.py        # 🌐 FastAPI REST server
└── logs/                # 📋 Rotating logs
```

## 🔑 Getting API Keys

1. **Groq** (required): [console.groq.com](https://console.groq.com) — Free tier, very fast
2. **NewsAPI** (optional): [newsapi.org](https://newsapi.org) — Free tier
3. **OpenWeatherMap** (optional): [openweathermap.org](https://openweathermap.org/api) — Free
4. **Spotify** (optional): [developer.spotify.com](https://developer.spotify.com/dashboard)
