# Jarvis AI Assistant

A voice-controlled desktop assistant with an always-listening wake word, a dark-themed
Tkinter GUI, and hands-free access to Wikipedia, Google, YouTube music, weather, news,
system controls (volume/brightness), email, and an OpenAI fallback for everything else.

## Project layout

| File | Purpose |
|------|---------|
| `jarvis.py` | Main entry — Tkinter GUI (Start/Stop/Config buttons, live conversation log, colour-coded status dot) + threaded assistant that handles all voice commands |
| `config.py` | Loads all keys/settings from `.env` (via python-dotenv) and exposes a `Config` singleton with `has_openai`/`has_email`/etc. flags + a contacts dict |
| `system_control.py` | Cross-platform volume (pycaw / osascript / amixer) and brightness (screen_brightness_control / osascript / brightnessctl) with graceful fallbacks and a `capabilities()` check |
| `email_sender.py` | SMTP send (port 465 SSL or 587 STARTTLS), contact lookup, helpful errors (e.g. Gmail App Password hint) |
| `.env.example` | Configuration template — copy to `.env` and fill in your keys |
| `requirements.txt` | Dependencies, with Windows-only packages behind platform markers |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Notes:
- **PyAudio** needs PortAudio. On Windows, `pip install pyaudio` usually just works.
  On macOS: `brew install portaudio` first. On Debian/Ubuntu:
  `sudo apt install portaudio19-dev python3-pyaudio`.
- **Linux system controls** use CLI tools, not pip packages:
  `sudo apt install alsa-utils brightnessctl`.

### 2. Configure your keys

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Where to get it | Needed for |
|----------|-----------------|------------|
| `OPENAI_API_KEY` | platform.openai.com | ChatGPT fallback answers |
| `WEATHER_API_KEY` | openweathermap.org | Weather reports |
| `NEWS_API_KEY` | newsapi.org | News briefing |
| `EMAIL_ADDRESS` / `EMAIL_PASSWORD` | Gmail App Password (myaccount.google.com/apppasswords) | Sending email |

Everything is optional — Jarvis starts fine with missing keys and simply tells you
which feature isn't configured when you ask for it. Use the **⚙ CONFIG CHECK** button
in the GUI to see what's active.

### 3. Run

```bash
python jarvis.py
```

Click **START**, wait for "Jarvis online", then say **"Jarvis"** followed by a command.

## Voice commands

| Say... | Jarvis does... |
|--------|----------------|
| "Jarvis" | Wake word — answers "Yes sir?" and listens for a command |
| "... wikipedia" | Reads a two-sentence Wikipedia summary aloud (no browser) |
| "google search ..." | Searches Google in the background, opens the top result |
| "play music/song ..." | Plays the song on YouTube via pywhatkit |
| "open chrome" / "open edge" | Launches the browser (Windows, macOS, Linux) |
| "what's the time" | Speaks the current time |
| "weather in \<city\>" | Current temperature + conditions (defaults to `DEFAULT_CITY`) |
| "news" | Reads the top five headlines |
| "volume up / down", "set volume to 50", "mute", "unmute" | System volume |
| "brightness up / down", "set brightness to 80" | Screen brightness |
| "send email to \<name\>" | Emails a contact (asks for subject and body by voice) |
| "send email" | Asks for recipient address, subject, and body by voice |
| "list contacts" | Reads out the contact names from `config.py` |
| "jarvis quit" / "shut down" / "goodbye" | Shuts the assistant down |
| anything else | Answered by OpenAI (if configured) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `PyAudio` fails to install | Install PortAudio first (see Setup step 1) |
| Mic never hears the wake word | Check your OS default input device; speak within ~3 seconds of the "Waiting for wake word" log line |
| "I'm having trouble connecting to my neural network" | `OPENAI_API_KEY` missing/invalid, or no internet |
| Email says "Authentication failed" | Gmail requires an **App Password**, not your account password |
| Volume/brightness "not available" | Linux: install `alsa-utils` / `brightnessctl`; Windows: ensure `pycaw` / `screen-brightness-control` installed |
| No speech output on Linux | `pyttsx3` needs espeak: `sudo apt install espeak libespeak1` |

## Customising

- **Wake word / name / default city**: set `WAKE_WORD`, `ASSISTANT_NAME`,
  `DEFAULT_CITY` in `.env`.
- **Contacts**: edit the `contacts` dict in `config.py` (lowercase names → addresses).
- **News country**: set `NEWS_COUNTRY` (e.g. `in`, `gb`, `us`) in `.env`.
- **OpenAI model**: set `OPENAI_MODEL` (default `gpt-3.5-turbo`).
