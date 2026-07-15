"""Dark-themed Tkinter GUI driving the async assistant pipeline.

The pipeline runs inside a background thread with its own asyncio event
loop; the GUI communicates with it through a thread-safe queue.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from jarvis import system_control
from jarvis.config import config
from jarvis.core.pipeline import Pipeline


class JarvisGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.msg_queue: queue.Queue = queue.Queue()
        self.pipeline: Pipeline | None = None
        self.worker: threading.Thread | None = None

        root.title(f"{config.assistant_name} AI Assistant")
        root.geometry("720x560")
        root.minsize(560, 420)
        root.configure(bg="#0f0f1a")

        self._build_styles()
        self._build_header()
        self._build_log()
        self._build_controls()
        self._build_status_bar()

        self.root.after(33, self._drain_queue)

    # ---------- UI builders ----------
    def _build_styles(self):
        self.bg = "#0f0f1a"
        self.panel = "#1a1a2e"
        self.accent = "#00ff9c"
        self.muted = "#7a7a99"
        self.text_color = "#e6e6f0"

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.bg)
        header.pack(fill="x", padx=16, pady=(14, 6))
        title = tk.Label(header, text=f"◉  {config.assistant_name.upper()}  AI",
                         fg=self.accent, bg=self.bg,
                         font=("Consolas", 22, "bold"))
        title.pack(anchor="w")
        subtitle = tk.Label(header,
                            text="Voice assistant • wake word active • say my name",
                            fg=self.muted, bg=self.bg,
                            font=("Consolas", 10))
        subtitle.pack(anchor="w")

    def _build_log(self):
        frame = tk.Frame(self.root, bg=self.panel, highlightbackground="#2a2a4a",
                         highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=16, pady=8)
        self.log = scrolledtext.ScrolledText(
            frame, wrap="word", bg=self.panel, fg=self.text_color,
            insertbackground=self.text_color,
            font=("Consolas", 11), padx=12, pady=10, relief="flat",
            state="disabled"
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("jarvis", foreground=self.accent,
                            font=("Consolas", 11, "bold"))
        self.log.tag_config("user", foreground="#7ab8ff",
                            font=("Consolas", 11, "bold"))
        self.log.tag_config("system", foreground=self.muted,
                            font=("Consolas", 10, "italic"))

    def _build_controls(self):
        bar = tk.Frame(self.root, bg=self.bg)
        bar.pack(fill="x", padx=16, pady=(0, 8))

        self.start_btn = tk.Button(bar, text="▶  START", command=self.start,
                                   bg=self.accent, fg="#000000",
                                   activebackground="#00cc7a",
                                   activeforeground="#000000",
                                   font=("Consolas", 11, "bold"),
                                   relief="flat", padx=18, pady=8, cursor="hand2")
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(bar, text="■  STOP", command=self.stop,
                                  bg="#3a3a55", fg=self.text_color,
                                  activebackground="#555577",
                                  font=("Consolas", 11, "bold"),
                                  relief="flat", padx=18, pady=8,
                                  state="disabled", cursor="hand2")
        self.stop_btn.pack(side="left", padx=(8, 0))

        self.settings_btn = tk.Button(bar, text="⚙  CONFIG CHECK",
                                      command=self.show_config,
                                      bg="#2a2a4a", fg=self.text_color,
                                      activebackground="#3a3a5a",
                                      font=("Consolas", 10),
                                      relief="flat", padx=12, pady=8,
                                      cursor="hand2")
        self.settings_btn.pack(side="right")

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg="#000000")
        bar.pack(fill="x", side="bottom")
        self.status_dot = tk.Label(bar, text="●", fg="#555555", bg="#000000",
                                   font=("Consolas", 14))
        self.status_dot.pack(side="left", padx=(10, 4))
        self.status_label = tk.Label(bar, text="OFFLINE", fg=self.muted,
                                     bg="#000000",
                                     font=("Consolas", 10, "bold"))
        self.status_label.pack(side="left", pady=4)

    # ---------- queue processing ----------
    def _drain_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]
                if kind == "log":
                    _, who, text = msg
                    self._append_log(who, text)
                elif kind == "status":
                    self._set_status(msg[1])
                    if msg[1] == "OFFLINE":
                        self._reset_buttons()
        except queue.Empty:
            pass
        self.root.after(33, self._drain_queue)

    def _append_log(self, who: str, text: str):
        self.log.config(state="normal")
        who_lower = who.lower()
        if config.assistant_name.lower() in who_lower:
            tag = "jarvis"
            prefix = f"{config.assistant_name}: "
        elif "user" in who_lower:
            tag = "user"
            prefix = "You: "
        else:
            tag = "system"
            prefix = f"[{who}] "
        self.log.insert("end", prefix, tag)
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_status(self, status: str):
        colors = {
            "OFFLINE":    ("#555555", self.muted),
            "IDLE":       ("#ffcc00", "#ffcc00"),
            "LISTENING":  ("#00ff9c", "#00ff9c"),
            "PROCESSING": ("#7ab8ff", "#7ab8ff"),
        }
        dot_fg, label_fg = colors.get(status, ("#555555", self.muted))
        self.status_dot.config(fg=dot_fg)
        self.status_label.config(text=status, fg=label_fg)

    # ---------- actions ----------
    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self._append_log("System", "Booting up...")
        self.pipeline = Pipeline(
            config,
            on_log=lambda who, text: self.msg_queue.put(("log", who, text)),
            on_status=lambda status: self.msg_queue.put(("status", status)),
        )
        self.worker = threading.Thread(
            target=lambda: asyncio.run(self.pipeline.run()), daemon=True)
        self.worker.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop(self):
        if self.pipeline:
            self.pipeline.request_stop()
            self._append_log("System", "Stop requested. Finishing current task...")

    def _reset_buttons(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pipeline = None
        self.worker = None

    def show_config(self):
        caps = system_control.capabilities()
        info = (
            f"Assistant name : {config.assistant_name}\n"
            f"Wake word      : '{config.wake_word}'\n"
            f"Default city   : {config.default_city}\n"
            f"News country   : {config.news_country}\n"
            f"OpenAI model   : {config.openai_model}\n\n"
            f"API keys configured:\n"
            f"  OpenAI    : {'YES' if config.has_openai else 'NO'}\n"
            f"  Weather   : {'YES' if config.has_weather else 'NO'}\n"
            f"  News      : {'YES' if config.has_news else 'NO'}\n"
            f"  Email     : {'YES' if config.has_email else 'NO'}\n"
            f"  Spotify   : {'YES' if config.has_spotify else 'NO'}\n"
            f"  Home Asst : {'YES' if config.has_hass else 'NO'}\n\n"
            f"System controls available:\n"
            f"  Volume     : {'YES' if caps['volume'] else 'NO'}\n"
            f"  Brightness : {'YES' if caps['brightness'] else 'NO'}\n\n"
            f"Contacts: {', '.join(config.contacts.keys()) or 'none'}\n\n"
            f"To configure API keys, edit the .env file in this folder.\n"
            f"(Copy .env.example to .env if you haven't already.)"
        )
        messagebox.showinfo("Configuration", info)


def main() -> None:
    root = tk.Tk()
    JarvisGUI(root)
    root.mainloop()
