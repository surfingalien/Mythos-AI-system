"""Spotify tools (optional): search and control playback via spotipy.

Requires SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env and the
`spotipy` package. Playback control needs a Spotify Premium account with
an active device (the desktop/mobile app open somewhere).
"""

from __future__ import annotations

from mythos.config import config
from mythos.tools.registry import tool

_client = None


def _spotify():
    global _client
    if _client is None:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        _client = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config.spotify_client_id,
            client_secret=config.spotify_client_secret,
            redirect_uri=config.spotify_redirect_uri,
            scope="user-modify-playback-state user-read-playback-state",
        ))
    return _client


def _available() -> bool:
    if not config.has_spotify:
        return False
    try:
        import spotipy  # noqa: F401
        return True
    except ImportError:
        return False


@tool(
    description="Play a song, artist, album, or playlist on Spotify.",
    parameters={"query": {"type": "string", "description": "What to play"}},
    enabled=_available,
)
def play_spotify(query: str) -> str:
    sp = _spotify()
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        return f"I couldn't find {query} on Spotify."
    track = tracks[0]
    devices = sp.devices().get("devices", [])
    if not devices:
        return ("No active Spotify device found. "
                "Open Spotify on one of your devices and try again.")
    sp.start_playback(device_id=devices[0]["id"], uris=[track["uri"]])
    artists = ", ".join(a["name"] for a in track["artists"])
    return f"Playing {track['name']} by {artists} on Spotify."


@tool(description="Pause Spotify playback.", enabled=_available)
def pause_spotify() -> str:
    _spotify().pause_playback()
    return "Paused Spotify."


@tool(description="Resume Spotify playback.", enabled=_available)
def resume_spotify() -> str:
    _spotify().start_playback()
    return "Resuming Spotify."


@tool(description="Skip to the next Spotify track.", enabled=_available)
def next_spotify_track() -> str:
    _spotify().next_track()
    return "Skipped to the next track."
