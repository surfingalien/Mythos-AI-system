"""Media tools: play music on YouTube, launch browsers/apps."""

from __future__ import annotations

import platform
import subprocess

from mythos.tools.registry import tool

_BROWSER_COMMANDS: dict[str, tuple[str, dict[str, list[str]]]] = {
    "chrome": ("Google Chrome", {
        "Windows": ["cmd", "/c", "start", "", "chrome"],
        "Darwin": ["open", "-a", "Google Chrome"],
        "Linux": ["google-chrome"],
    }),
    "edge": ("Microsoft Edge", {
        "Windows": ["cmd", "/c", "start", "", "msedge"],
        "Darwin": ["open", "-a", "Microsoft Edge"],
        "Linux": ["microsoft-edge"],
    }),
    "firefox": ("Firefox", {
        "Windows": ["cmd", "/c", "start", "", "firefox"],
        "Darwin": ["open", "-a", "Firefox"],
        "Linux": ["firefox"],
    }),
}


@tool(
    description="Play a song or video on YouTube.",
    parameters={"song": {"type": "string", "description": "Song, artist, or video name"}},
)
def play_on_youtube(song: str) -> str:
    import pywhatkit

    pywhatkit.playonyt(song)
    return f"Playing {song} on YouTube."


@tool(
    description="Open a web browser application (chrome, edge, or firefox).",
    parameters={"browser": {
        "type": "string",
        "enum": ["chrome", "edge", "firefox"],
        "description": "Which browser to open",
    }},
)
def open_browser(browser: str) -> str:
    entry = _BROWSER_COMMANDS.get(browser.lower().strip())
    if entry is None:
        return f"I don't know the browser {browser}."
    label, commands = entry
    cmd = commands.get(platform.system())
    if not cmd:
        return f"I don't know how to open {label} on this system."
    try:
        subprocess.Popen(cmd)
        return f"Opening {label}."
    except FileNotFoundError:
        return f"{label} doesn't seem to be installed."
    except Exception as e:
        return f"I couldn't open {label}: {e}"
