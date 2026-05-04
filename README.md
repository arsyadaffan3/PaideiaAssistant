Paideia
> *Named after the ancient Greek concept of education and formation of the ideal citizen.*
A personal AI assistant running 24/7 on a home server. Paideia is designed to be modular — multiple interfaces (Telegram bot, terminal UI, voice) all sharing a common utility layer.
---
Hardware
ASUS PN41 Mini PC
Intel Pentium Silver N6005 @ 2.0GHz
16GB DDR4 RAM
256GB NVMe SSD
Windows 11 Home
Running continuously as a home server
---
Architecture
```
utils.py      ← shared API logic (all interfaces import from here)
telebot.py    ← Telegram bot interface
tui.py        ← terminal dashboard interface
voice.py      ← voice interface (wake word, STT, TTS)
```
Any new interface just imports `utils.py` — no duplication.
---
Interfaces
Telegram Bot (`telebot.py`)
Commands available over Telegram:
Command	Description
`/start`	Show help menu
`/stats`	PN41 system stats (CPU, RAM, disk, network)
`/today`	Google Calendar schedule
`/prayer`	Prayer times (Aladhan API)
`/weather`	Current weather (Open-Meteo)
`/8ball`	Magic 8-ball
`/terra`	Ask the local LLM (Ollama)
`/shutdown`	Shut down the PN41
Plain text	Chat with Aether (cloud LLM via Groq)
Includes a 7:00 AM morning briefing with prayer times, schedule, and a quote — delivered automatically via APScheduler.
Terminal UI (`tui.py`)
A live terminal dashboard with:
Real-time system stats (CPU, RAM, disk, network) with progress bars
Weather, prayer times, and calendar schedule
In-terminal AI chat (prefix with `l:` to use the local model)
Refreshes every 5 seconds for stats, 5 minutes for external data
Voice Interface (`voice.py`)
Wake word: "hello"
Mic input via `sounddevice` + `numpy`
Speech-to-text via Google STT
Response via Groq API
Text-to-speech via Windows SAPI (`win32com.client`) — deeper male voice
---
AI Models
Name	Type	Backend	Personality
Aether	Cloud	Groq (`llama-3.3-70b-versatile`)	Sharp, dystopian, direct
Terra	Local	Ollama (self-hosted)	Compact, offline-capable
---
APIs & Libraries
APIs: Groq, Google Calendar (OAuth2), Aladhan (prayer times), Open-Meteo (weather), ZenQuotes
Libraries: `python-telegram-bot`, `sounddevice`, `numpy`, `speech_recognition`, `win32com.client` (pywin32), `psutil`, `APScheduler`, `google-api-python-client`
---
Setup
Clone the repo and install dependencies:
```bash
   pip install -r requirements.txt
   ```
Create a `.env` file:
```env
   TELEGRAM_TOKEN=your_token
   CHAT_ID=your_chat_id
   GROQ_API_KEY=your_groq_key
   GROQ_MODEL=llama-3.3-70b-versatile
   OLLAMA_MODEL=your_local_model
   ```
Add `credentials.json` from Google Cloud Console for Calendar access.
Run an interface:
```bash
   python telebot.py   # Telegram bot
   python tui.py       # Terminal dashboard
   python voice.py     # Voice interface
   ```
---
Notes
`token.json` is auto-generated after first Google Calendar auth. Delete it to re-authenticate.
Voice interface uses `sounddevice` — not PyAudio (incompatible with Python 3.13+).
TTS uses Windows SAPI via `win32com.client` — not pyttsx3 (unreliable on Windows alongside sounddevice).
The PN41 is also used as a personal file archive; no processes are designed to stress the hardware.
