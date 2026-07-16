# Mythos AI Assistant

A modern, voice-controlled desktop assistant. Version 2 replaces keyword matching
with an **LLM tool-calling brain**, adds an **offline wake word**, **neural
text-to-speech**, **local Whisper speech-to-text**, **streaming replies with
barge-in**, **long-term memory**, and optional **Spotify / Home Assistant / notes /
MCP** integrations — while still degrading gracefully: every capability is optional,
and the assistant runs with whatever you have installed and configured.

## How it works

```
 wake word ──► listen ──► LLM brain (tool calling, streaming) ──► speak
 openWakeWord   Whisper     OpenAI + 25+ registered tools          edge-tts
 (offline)      (local)     conversation memory + facts store      (neural)
     ▲                                                                │
     └────────────── barge-in: say the wake word to interrupt ◄──────┘
```

Instead of `if 'weather' in query`, capabilities are **tools** — plain Python
functions with JSON schemas (`mythos/tools/`). The LLM picks the right tool,
extracts arguments, chains multiple tools, and asks follow-up questions when
something's missing. "It's way too loud and what's it like outside in Berlin?"
just works. Without an OpenAI key, an offline keyword router still handles the
classics (time, weather, music, volume, ...).

Every audio engine auto-selects the best installed option and falls back:

| Layer | Modern (preferred) | Fallback |
|-------|--------------------|----------|
| Wake word | openWakeWord — offline, instant | Google Web Speech keyword loop |
| Speech-to-text | faster-whisper — local, accurate | Google Web Speech |
| Text-to-speech | edge-tts — natural neural voices | pyttsx3 |

> **Wake-word note:** openWakeWord ships a pretrained model only for
> "hey jarvis". The default wake word is `mythos`, which uses the
> speech-recognition fallback out of the box. For instant offline detection
> either set `WAKE_WORD=jarvis`, or train a custom openWakeWord model for
> "mythos" and point `WAKE_MODEL_PATH` at it.

## Project layout

| Path | Purpose |
|------|---------|
| `mythos/llm.py` | The brain: streaming tool-calling loop, history, sentence splitter |
| `mythos/router.py` | Offline fallback router (no API key needed) |
| `mythos/tools/` | Tool registry + all capabilities (info, media, system, email, memory, notes, Spotify, Home Assistant) |
| `mythos/audio/` | TTS / STT / wake-word engines with auto-fallback |
| `mythos/core/pipeline.py` | Async pipeline: wake → listen → stream → speak, with barge-in |
| `mythos/ui/gui.py` | Dark-themed Tkinter desktop GUI |
| `mythos/ui/web.py` | FastAPI + WebSocket web chat UI |
| `mythos/memory.py` | Persistent facts the assistant remembers across sessions |
| `mythos/mcp_client.py` | Experimental: plug external MCP servers in as tools |
| `tests/` | Unit tests (run offline, no audio hardware needed) |

## Setup

### Quick setup (macOS)

```bash
git clone https://github.com/surfingalien/Mythos-AI-system.git
cd Mythos-AI-system
bash scripts/setup_mac.sh
```

This installs the system dependencies (`portaudio`, `python-tk`, `ffmpeg` via
Homebrew), builds a fresh virtualenv **inside the repo** (never in `$HOME` —
see the note below), and installs all Python dependencies into it using
explicit paths, so it isn't affected by whatever `python`/`pip` happen to
resolve to in your shell. Then run it with the matching helper script —
these also use explicit paths, so they always run the right interpreter:

```bash
bash scripts/run_text.sh   # type-only REPL, no mic needed — try this first
bash scripts/run_gui.sh    # desktop GUI with mic + wake word
bash scripts/run_web.sh    # browser chat UI (kills any stale process on the port first)
```

If anything seems off — wrong Python version, missing packages, port
conflicts — run the diagnostic script before troubleshooting manually:

```bash
bash scripts/doctor.sh
```

It prints exactly which interpreter and virtualenv are active and flags the
most common trap: a **same-named `.venv` in a different location** (e.g. your
home directory) silently shadowing the repo's own venv. Both show an
identical `(.venv)` prompt prefix, so this is easy to miss — `doctor.sh`
compares `$VIRTUAL_ENV` against the repo's actual `.venv` path and warns
if they don't match.

### Manual setup (any OS)

```bash
# Recommended full desktop install
pip install -r requirements.txt

# Or pick your pieces via extras
pip install -e ".[llm,audio,commands]"          # core voice assistant
pip install -e ".[llm,audio,commands,whisper]"  # + local speech-to-text
pip install -e ".[web]"                         # + web UI
```

Notes:
- **PyAudio** needs PortAudio: `brew install portaudio` (macOS) or
  `sudo apt install portaudio19-dev` (Debian/Ubuntu). Windows usually just works.
- **Neural TTS playback** needs one of `ffplay` (ffmpeg), `mpv`, or `afplay`.
- **Linux system controls**: `sudo apt install alsa-utils brightnessctl`.

Then configure:

```bash
cp .env.example .env   # then edit — every key is optional
```

| Variable | Enables |
|----------|---------|
| `OPENAI_API_KEY` | The LLM brain (natural language, tool chaining, memory) |
| `WEATHER_API_KEY` | Weather (openweathermap.org) |
| `NEWS_API_KEY` | News briefings (newsapi.org) |
| `EMAIL_ADDRESS` + `EMAIL_PASSWORD` | Email (Gmail App Password) |
| `CONTACTS` | Named recipients, e.g. `john:john@example.com,boss:boss@co.com` |
| `SPOTIFY_CLIENT_ID/SECRET` | Spotify playback (`pip install spotipy`, Premium) |
| `HASS_URL` + `HASS_TOKEN` | Home Assistant smart-home control |
| `NOTES_DIR` | "Search my notes for ..." over a folder of .md/.txt files |
| `ASSISTANT_NAME` / `WAKE_WORD` | Rename the assistant / change the trigger word |

## Run

```bash
python -m mythos            # desktop GUI (default)
python -m mythos --headless # voice only, no GUI (Raspberry Pi etc.)
python -m mythos --web      # browser chat UI at http://127.0.0.1:8765
python -m mythos --text     # type-only REPL — test with zero audio hardware
```

Say **"mythos"**, then speak naturally. While Mythos is talking, say the wake
word again to **interrupt it**.

## Example commands

With the LLM brain there's no fixed grammar — these are just illustrations:

- "What's the weather like in Berlin, and should I take a jacket?"
- "Play Bohemian Rhapsody" / "Skip this track" (Spotify) 
- "Turn off the living room lights" (Home Assistant)
- "Send an email to John saying I'll be ten minutes late"
- "Remember that my parking spot is level 3, row F" → later: "Where did I park?"
- "Search my notes for the pizza dough recipe"
- "Set the volume to forty and dim the screen"
- "What's on Wikipedia about Alan Turing?"
- "Shut down" / "goodbye" — exits

## Development

```bash
pip install -e ".[dev]"
ruff check .    # lint
pytest -q       # tests (39, all offline — CI runs them on 3.10 & 3.12)
```

Adding a capability is one function:

```python
from mythos.tools.registry import tool

@tool(description="Roll an N-sided die.",
      parameters={"sides": {"type": "integer", "description": "Number of sides"}})
def roll_die(sides: int) -> str:
    import random
    return f"You rolled a {random.randint(1, sides)}."
```

Drop it in a module under `mythos/tools/`, import it from `mythos/tools/__init__.py`,
and the LLM can use it immediately.

### MCP servers (experimental)

Create `mcp_servers.json` and `pip install mcp` to give Mythos tools from any
[MCP](https://modelcontextprotocol.io) server:

```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/me/documents"]
  }
}
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `PyAudio` fails to install | Install PortAudio first (see Setup) |
| Robotic voice | Install `edge-tts` and `ffmpeg` (for `ffplay`) — check the engine line logged at startup |
| Wake word sluggish/unreliable | The default "mythos" wake word uses the online fallback; set `WAKE_WORD=jarvis` for offline openWakeWord, or supply `WAKE_MODEL_PATH` |
| Poor transcription | Install `faster-whisper` (`STT_ENGINE=whisper`, try `WHISPER_MODEL=small`) |
| "I can handle that better with an OpenAI key" | Set `OPENAI_API_KEY` in `.env` to unlock the LLM brain |
| Email "Authentication failed" | Gmail needs an **App Password**, not your account password |
| Volume/brightness unavailable (Linux) | `sudo apt install alsa-utils brightnessctl` |
| No speech output on Linux | `sudo apt install espeak libespeak1` (pyttsx3 fallback) |
