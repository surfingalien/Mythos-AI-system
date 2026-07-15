"""
system_control.py
Cross-platform system controls: volume and screen brightness.

Supported platforms:
  - Windows: pycaw (volume), screen_brightness_control (brightness)
  - macOS:   osascript (both)
  - Linux:   amixer (volume), brightnessctl (brightness)

All functions return a human-readable status string suitable for speak().
If a control isn't available, a friendly error message is returned.
"""

import platform
import subprocess
import shutil

_SYSTEM = platform.system().lower()  # 'windows', 'darwin', 'linux'


# ============================================================
# VOLUME
# ============================================================
def volume_up(step: int = 10) -> str:
    """Increase volume by `step` percent (default 10)."""
    try:
        if _SYSTEM == "windows":
            return _windows_volume(delta=step)
        if _SYSTEM == "darwin":
            return _mac_volume(delta=step)
        return _linux_volume(delta=step)
    except Exception as e:
        return f"Volume up failed: {e}"


def volume_down(step: int = 10) -> str:
    """Decrease volume by `step` percent (default 10)."""
    try:
        if _SYSTEM == "windows":
            return _windows_volume(delta=-step)
        if _SYSTEM == "darwin":
            return _mac_volume(delta=-step)
        return _linux_volume(delta=-step)
    except Exception as e:
        return f"Volume down failed: {e}"


def set_volume(value: int) -> str:
    """Set volume to an absolute percentage (0-100)."""
    value = max(0, min(100, int(value)))
    try:
        if _SYSTEM == "windows":
            return _windows_volume(set_to=value)
        if _SYSTEM == "darwin":
            return _mac_volume(set_to=value)
        return _linux_volume(set_to=value)
    except Exception as e:
        return f"Set volume failed: {e}"


def mute_volume() -> str:
    try:
        if _SYSTEM == "windows":
            return _windows_mute()
        if _SYSTEM == "darwin":
            subprocess.run(["osascript", "-e", "set volume with output muted"], check=True)
            return "Muted."
        subprocess.run(["amixer", "-q", "set", "Master", "mute"], check=True)
        return "Muted."
    except Exception as e:
        return f"Mute failed: {e}"


def unmute_volume() -> str:
    try:
        if _SYSTEM == "windows":
            return _windows_mute(unmute=True)
        if _SYSTEM == "darwin":
            subprocess.run(["osascript", "-e", "set volume without output muted"], check=True)
            return "Unmuted."
        subprocess.run(["amixer", "-q", "set", "Master", "unmute"], check=True)
        return "Unmuted."
    except Exception as e:
        return f"Unmute failed: {e}"


# --- Windows volume (pycaw) ---
def _windows_volume(delta: int = 0, set_to: int | None = None) -> str:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    if set_to is not None:
        # 0..100 -> -65..0 dB scale (pycaw uses scalar in dB)
        new_pct = set_to / 100.0
        volume.SetMasterVolumeLevelScalar(new_pct, None)
        return f"Volume set to {set_to} percent."

    current = volume.GetMasterVolumeLevelScalar() * 100
    new_pct = max(0.0, min(1.0, (current + delta) / 100.0))
    volume.SetMasterVolumeLevelScalar(new_pct, None)
    return f"Volume is now {int(new_pct * 100)} percent."


def _windows_mute(unmute: bool = False) -> str:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMute(0 if unmute else 1, None)
    return "Unmuted." if unmute else "Muted."


# --- macOS volume ---
def _mac_volume(delta: int = 0, set_to: int | None = None) -> str:
    if set_to is not None:
        subprocess.run(["osascript", "-e", f"set volume {set_to / 100.0 * 7}"], check=True)
        return f"Volume set to {set_to} percent."
    # Read current (0..7 scale)
    out = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"])
    cur = int(out.decode().strip())
    new = max(0, min(100, cur + delta))
    subprocess.run(["osascript", "-e", f"set volume {new / 100.0 * 7}"], check=True)
    return f"Volume is now {new} percent."


# --- Linux volume (amixer) ---
def _linux_volume(delta: int = 0, set_to: int | None = None) -> str:
    if set_to is not None:
        subprocess.run(["amixer", "-q", "set", "Master", f"{set_to}%"], check=True)
        return f"Volume set to {set_to} percent."
    # amixer supports relative like "5%+"
    sign = "+" if delta >= 0 else "-"
    subprocess.run(["amixer", "-q", "set", "Master", f"{abs(delta)}%{sign}"], check=True)
    return f"Volume adjusted by {delta} percent."


# ============================================================
# BRIGHTNESS
# ============================================================
def brightness_up(step: int = 10) -> str:
    try:
        if _SYSTEM == "windows":
            return _win_brightness(delta=step)
        if _SYSTEM == "darwin":
            return _mac_brightness(delta=step)
        return _linux_brightness(delta=step)
    except Exception as e:
        return f"Brightness up failed: {e}"


def brightness_down(step: int = 10) -> str:
    try:
        if _SYSTEM == "windows":
            return _win_brightness(delta=-step)
        if _SYSTEM == "darwin":
            return _mac_brightness(delta=-step)
        return _linux_brightness(delta=-step)
    except Exception as e:
        return f"Brightness down failed: {e}"


def set_brightness(value: int) -> str:
    value = max(0, min(100, int(value)))
    try:
        if _SYSTEM == "windows":
            return _win_brightness(set_to=value)
        if _SYSTEM == "darwin":
            return _mac_brightness(set_to=value)
        return _linux_brightness(set_to=value)
    except Exception as e:
        return f"Set brightness failed: {e}"


def _win_brightness(delta: int = 0, set_to: int | None = None) -> str:
    import screen_brightness_control as sbc
    if set_to is not None:
        sbc.set_brightness(set_to)
        return f"Brightness set to {set_to} percent."
    cur = sbc.get_brightness()[0]
    new = max(0, min(100, cur + delta))
    sbc.set_brightness(new)
    return f"Brightness is now {new} percent."


def _mac_brightness(delta: int = 0, set_to: int | None = None) -> str:
    # macOS has no public CLI; use a small AppleScript shim.
    if set_to is not None:
        # 0..100 -> 0..1 (rounded to 16 steps internally by macOS)
        v = set_to / 100.0
    else:
        # Read current via system_profiler is expensive; approximate by adjusting
        v = None
    if v is not None:
        subprocess.run(["osascript", "-e",
                        f"tell application \"System Events\" to set brightness of (every window) to {v}"], check=False)
        return f"Brightness set to approximately {set_to} percent."
    # Without a reliable read, just nudge via keyboard. Fall through:
    return "Brightness adjustment on macOS is limited; use the keyboard keys."


def _linux_brightness(delta: int = 0, set_to: int | None = None) -> str:
    if shutil.which("brightnessctl") is None:
        return "brightnessctl not installed on this Linux system."
    if set_to is not None:
        subprocess.run(["brightnessctl", "set", f"{set_to}%"], check=True)
        return f"Brightness set to {set_to} percent."
    sign = "+" if delta >= 0 else "-"
    subprocess.run(["brightnessctl", "set", f"{abs(delta)}%{sign}"], check=True)
    return f"Brightness adjusted by {delta} percent."


# ============================================================
# Convenience: detect what's available
# ============================================================
def capabilities() -> dict:
    """Returns a dict of feature -> bool, so the GUI can show what's supported."""
    caps = {"volume": False, "brightness": False}
    try:
        if _SYSTEM == "windows":
            import pycaw  # noqa
            caps["volume"] = True
        elif _SYSTEM == "darwin":
            caps["volume"] = True
        elif shutil.which("amixer"):
            caps["volume"] = True
    except Exception:
        pass
    try:
        if _SYSTEM == "windows":
            import screen_brightness_control  # noqa
            caps["brightness"] = True
        elif _SYSTEM == "darwin":
            caps["brightness"] = True
        elif shutil.which("brightnessctl"):
            caps["brightness"] = True
    except Exception:
        pass
    return caps
