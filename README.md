# M.A.X — Machine Autonomous eXpert

M.A.X is a voice-controlled personal AI assistant built in Python. It uses the Groq LLM (LLaMA 3.3 70B) for natural language understanding and intent routing, a custom Tkinter HUD for the interface, and a modular skills architecture that handles everything from web browsing and Spotify playback to system control and email.

---

## Features

- Voice wake-word detection ("Hey MAX")
- Groq LLM brain for intent detection and general conversation
- Persistent conversation memory and personal notes
- Voice-activated reminders
- Spotify integration
- REST API via FastAPI
- Modular skills system — easy to extend
- Rotating log system
- Iron Man-style HUD built with Tkinter

---

## Requirements

- Python 3.10 or higher
- Windows (PyAudio dependency; Linux/macOS require manual audio setup)
- A Groq API key (free at [console.groq.com](https://console.groq.com))

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/harshitk8406/MAX.git
cd MAX
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

On Windows, if PyAudio fails to install via pip, install it manually from the bundled wheel:

```bash
pip install PyAudio-0.2.11-cp38-cp38-win_amd64.whl
```

**3. Configure**

Copy the example config and fill in your API keys:

```bash
copy config.example.json config.json
```

Open `config.json` and set the following fields:

| Field | Description | Required |
|---|---|---|
| `user.name` | Your name | Yes |
| `groq.api_key` | Groq API key | Yes |
| `news.api_key` | NewsAPI key | No |
| `weather.api_key` | OpenWeatherMap key | No |
| `spotify.*` | Spotify Developer app credentials | No |
| `email.*` | Gmail address and app password | No |

**4. Run**

```bash
python main.py
```

---

## Voice Commands

| Command | Action |
|---|---|
| "Hey MAX" | Wake MAX from standby |
| "What's the weather?" | Current weather |
| "Tell me the news" | Top headlines |
| "Play [song] on Spotify" | Spotify playback |
| "Search YouTube for [query]" | YouTube search |
| "Remember that [thing]" | Save a note |
| "Set a reminder for [time]" | Timed reminder |
| "What's the CPU usage?" | System stats |
| "Take a screenshot" | Screen capture |
| "Define [word]" | Dictionary lookup |
| "Look up [topic] on Wikipedia" | Wikipedia search |
| "Open [app]" | Launch an application |
| "Send an email to [contact]" | Compose and send email |
| "Generate an image of [prompt]" | AI image generation |
| "Over and Out" | End session |
| "Goodbye MAX" | Shut down |

For anything not listed above, MAX passes the query directly to the Groq LLM for a conversational response.

---

## REST API

When running, MAX exposes a local REST API at `http://localhost:8000`.

**Send a query:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What time is it?"}'
```

**Get command history:**

```bash
curl http://localhost:8000/history
```

**Get saved notes:**

```bash
curl http://localhost:8000/notes
```

**Get pending reminders:**

```bash
curl http://localhost:8000/reminders
```

Interactive Swagger docs are available at `http://localhost:8000/docs`.

---

## Project Structure

```
MAX/
├── main.py                  # Entry point — wires GUI, voice, brain, skills, API
├── config.example.json      # Config template (copy to config.json and fill in keys)
├── core/
│   ├── brain.py             # Groq LLM integration and intent parsing
│   ├── voice.py             # TTS, STT, and wake-word detection
│   ├── memory.py            # Persistent conversation memory and notes
│   └── logger.py            # Rotating log system
├── skills/
│   ├── router.py            # Skill dispatcher
│   ├── browser.py           # Web browsing and search
│   ├── system.py            # System control (volume, lock, screenshots)
│   ├── pc_control.py        # App launch and window management
│   ├── weather.py           # Weather via OpenWeatherMap
│   ├── news.py              # Top headlines via NewsAPI
│   ├── wiki.py              # Wikipedia search
│   ├── web_research.py      # Autonomous web fetch and LLM summarization
│   ├── calendar_skill.py    # Reminders and scheduling
│   ├── notes.py             # Personal notes
│   ├── jokes.py             # Joke fetcher
│   ├── dictionary.py        # Word definitions
│   ├── email_skill.py       # Gmail send and read
│   ├── spotify.py           # Spotify playback control
│   ├── youtube_skill.py     # YouTube play, download, transcript
│   ├── messaging.py         # WhatsApp and desktop notifications
│   ├── image_gen.py         # AI image generation via Pollinations.ai
│   └── files.py             # File management
├── gui/
│   └── app.py               # Tkinter HUD (arc reactor animation, chat, controls)
├── api/
│   └── server.py            # FastAPI REST server
└── logs/                    # Rotating log files (git-ignored)
```

---

## Getting API Keys

- **Groq** (required) — [console.groq.com](https://console.groq.com) — Free tier, very fast inference
- **NewsAPI** (optional) — [newsapi.org](https://newsapi.org) — Free tier
- **OpenWeatherMap** (optional) — [openweathermap.org/api](https://openweathermap.org/api) — Free tier
- **Spotify** (optional) — [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
- **Gmail** (optional) — Use an App Password, not your main account password

---

## License

MIT
