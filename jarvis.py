"""
jarvis.py
Jarvis AI Assistant — enhanced edition.

Features:
  - Tkinter GUI with live conversation log, status indicator, and Start/Stop
  - Wake word detection ("Jarvis") running in a background thread
  - All original commands (Wikipedia, Google, YouTube, time, weather, news, OpenAI)
  - NEW: System controls — volume up/down/mute/set, brightness up/down/set
  - NEW: Email sending — by contact name or direct address, via SMTP
  - NEW: Config via .env file (no hardcoded API keys)

Run:
    python jarvis.py
"""

import datetime
import os
import queue
import threading
import webbrowser

import pywhatkit
import requests
import speech_recognition as sr
import tkinter as tk
import wikipedia
from openai import OpenAI
from tkinter import scrolledtext, messagebox

import system_control
import email_sender
from config import config


# ============================================================
# TEXT-TO-SPEECH (lazy-init in worker thread; pyttsx3 is not
# always safe to share across threads)
# ============================================================
class Speaker:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()

    def _ensure(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            voices = self._engine.getProperty('voices')
            if voices:
                # Index 0 is usually male on Windows; tweak as needed
                self._engine.setProperty('voice', voices[0].id)

    def speak(self, text: str):
        self._ensure()
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()


# ============================================================
# API INTEGRATIONS
# ============================================================
def ask_openai(prompt: str) -> str:
    if not config.has_openai:
        return ("My OpenAI integration isn't configured, sir. "
                "Please set OPENAI_API_KEY in your .env file.")
    try:
        client = OpenAI(api_key=config.openai_api_key)
        response = client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system",
                 "content": f"You are {config.assistant_name}, a highly advanced AI assistant. "
                            "Keep responses concise and spoken."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "I'm having trouble connecting to my neural network right now."


def get_weather(city: str) -> str:
    if not config.has_weather:
        return ("Weather lookups aren't configured, sir. "
                "Please set WEATHER_API_KEY in your .env file.")
    try:
        url = (f"http://api.openweathermap.org/data/2.5/weather?q={city}"
               f"&appid={config.weather_api_key}&units=metric")
        response = requests.get(url, timeout=10).json()
        if response.get("cod") == 200:
            temp = response['main']['temp']
            desc = response['weather'][0]['description']
            return (f"The current temperature in {city} is {temp} degrees "
                    f"Celsius with {desc}.")
        return "I couldn't find that city, sir."
    except Exception:
        return "I couldn't fetch the weather right now."


def get_news() -> str:
    if not config.has_news:
        return ("News isn't configured, sir. Please set NEWS_API_KEY in your .env file.")
    try:
        url = (f"https://newsapi.org/v2/top-headlines?country={config.news_country}"
               f"&apiKey={config.news_api_key}")
        response = requests.get(url, timeout=10).json()
        articles = response.get("articles", [])[:5]
        if not articles:
            return "No headlines available right now."
        headlines = [a['title'] for a in articles]
        return "Here are today's top headlines. " + ". ".join(headlines)
    except Exception:
        return "I couldn't fetch the news right now."


# ============================================================
# ASSISTANT WORKER (runs in a background thread)
# ============================================================
class JarvisWorker(threading.Thread):
    def __init__(self, msg_queue: queue.Queue):
        super().__init__(daemon=True)
        self.msg_queue = msg_queue
        self.speaker = Speaker()
        self._stop_flag = threading.Event()
        self._wake_event = threading.Event()

    # --- queue helpers ---
    def _log(self, who: str, text: str):
        self.msg_queue.put(("log", who, text))

    def _status(self, status: str):
        self.msg_queue.put(("status", status))

    def _say(self, text: str):
        self._log(config.assistant_name, text)
        self.speaker.speak(text)

    # --- speech input ---
    def _listen(self, phrase_time_limit=None) -> str:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.pause_threshold = 1
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)
            except Exception:
                return "none"
        try:
            text = recognizer.recognize_google(audio, language='en-in')
            return text.lower()
        except sr.UnknownValueError:
            return "none"
        except sr.RequestError:
            return "none"

    # --- wake word loop ---
    def _wait_for_wake(self) -> bool:
        """Blocks until wake word is heard or stop is requested."""
        recognizer = sr.Recognizer()
        self._log("System", f"Waiting for wake word ('{config.wake_word}')...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            while not self._stop_flag.is_set():
                try:
                    audio = recognizer.listen(source, phrase_time_limit=3)
                    text = recognizer.recognize_google(audio, language='en-in').lower()
                    if config.wake_word in text:
                        return True
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    # Sleep briefly to avoid busy loop if network is down
                    self._stop_flag.wait(2.0)
                    continue
                except Exception:
                    continue
        return False

    # --- main command router ---
    def _handle_command(self, query: str):
        q = query.lower().strip()

        # Wikipedia
        if 'wikipedia' in q:
            self._say('Searching Wikipedia...')
            topic = q.replace("wikipedia", "").strip()
            try:
                results = wikipedia.summary(topic, sentences=2)
                self._say("According to Wikipedia.")
                self._say(results)
            except Exception:
                self._say("Sorry, I couldn't find that on Wikipedia.")
            return

        # Google Search
        if 'google search' in q:
            from googlesearch import search
            term = q.replace("google search", "").strip()
            self._say(f"Searching Google for {term}.")
            try:
                results = list(search(term, num_results=3))
            except Exception:
                results = []
            if results:
                self._say("I found some results. Opening the first link.")
                webbrowser.open(results[0])
            else:
                self._say("No results found.")
            return

        # Play music / song on YouTube
        if 'play music' in q or 'play song' in q:
            song = q.replace("play", "").replace("music", "").replace("song", "").strip()
            self._say(f"Playing {song}.")
            try:
                pywhatkit.playonyt(song)
            except Exception as e:
                self._say(f"Couldn't play that: {e}")
            return

        # Open browsers
        if 'open chrome' in q:
            self._say("Opening Google Chrome.")
            os.system("start chrome" if os.name == "nt" else "google-chrome"
                      if os.name == "posix" else "open -a 'Google Chrome'")
            return
        if 'open edge' in q:
            self._say("Opening Microsoft Edge.")
            os.system("start msedge" if os.name == "nt" else "open -a 'Microsoft Edge'")
            return

        # Time
        if 'the time' in q or "what time" in q:
            str_time = datetime.datetime.now().strftime("%I:%M %p")
            self._say(f"Sir, the time is {str_time}.")
            return

        # Weather
        if 'weather' in q:
            if 'in' in q:
                city = q.split("in")[-1].strip()
            else:
                city = config.default_city
            self._say(f"Checking the weather in {city}.")
            self._say(get_weather(city))
            return

        # News
        if 'news' in q:
            self._say("Fetching the news.")
            self._say(get_news())
            return

        # ----- NEW: System controls (volume) -----
        if 'mute' in q:
            self._say(system_control.mute_volume())
            return
        if 'unmute' in q:
            self._say(system_control.unmute_volume())
            return
        if 'volume up' in q or 'increase volume' in q or 'louder' in q:
            self._say(system_control.volume_up(10))
            return
        if 'volume down' in q or 'decrease volume' in q or 'quieter' in q:
            self._say(system_control.volume_down(10))
            return
        if 'set volume' in q:
            val = _extract_number(q)
            if val is not None:
                self._say(system_control.set_volume(val))
            else:
                self._say("Please say a number between 0 and 100.")
            return

        # ----- NEW: System controls (brightness) -----
        if 'brightness up' in q or 'increase brightness' in q or 'brighter' in q:
            self._say(system_control.brightness_up(10))
            return
        if 'brightness down' in q or 'decrease brightness' in q or 'dimmer' in q:
            self._say(system_control.brightness_down(10))
            return
        if 'set brightness' in q:
            val = _extract_number(q)
            if val is not None:
                self._say(system_control.set_brightness(val))
            else:
                self._say("Please say a number between 0 and 100.")
            return

        # ----- NEW: Email -----
        if 'send email' in q or 'email to' in q or 'mail to' in q:
            self._handle_email(q)
            return
        if 'list contacts' in q or 'my contacts' in q:
            self._say(email_sender.list_contacts())
            return

        # Exit
        if (f"{config.wake_word} quit" in q
                or 'shut down' in q
                or 'exit' in q
                or 'goodbye' in q):
            self._say("Shutting down. Have a good day, sir.")
            self.msg_queue.put(("exit",))
            return

        # OpenAI fallback
        self._say("Let me think about that...")
        self._say(ask_openai(q))

    # ----- NEW: Email flow -----
    def _handle_email(self, q: str):
        # Try "send email to <name>"
        recipient_address = None
        for sep in ("email to", "mail to", "send email to"):
            if sep in q:
                name = q.split(sep)[-1].strip()
                # If name is in contacts, use it
                addr = config.contacts.get(name.lower().strip())
                if addr:
                    recipient_address = addr
                    self._say(f"Sending an email to {name}.")
                break

        if not recipient_address:
            self._say("What is the recipient's email address?")
            addr_input = self._listen(phrase_time_limit=10)
            if addr_input in ("none", ""):
                self._say("I didn't catch that. Cancelling the email.")
                return
            # Voice may produce "john at example dot com" etc.
            recipient_address = _normalize_email(addr_input)
            self._log("User", recipient_address)

        self._say("What is the subject?")
        subject = self._listen(phrase_time_limit=15)
        if subject in ("none", ""):
            self._say("No subject given. Cancelling.")
            return
        self._log("User", subject)

        self._say("What is the message?")
        body = self._listen(phrase_time_limit=30)
        if body in ("none", ""):
            self._say("No message given. Cancelling.")
            return
        self._log("User", body)

        self._say("Sending the email now.")
        result = email_sender.send_email(recipient_address, subject, body)
        self._say(result)

    # --- thread entry ---
    def run(self):
        self._say(f"{config.assistant_name} online. Say my name when you need me.")
        while not self._stop_flag.is_set():
            self._status("IDLE")
            if not self._wait_for_wake():
                break  # stop requested
            self._status("LISTENING")
            self._say("Yes sir?")
            query = self._listen()
            self._log("User", query)
            if query in ("none", ""):
                continue
            self._status("PROCESSING")
            try:
                self._handle_command(query)
            except Exception as e:
                self._say(f"An error occurred: {e}")
        self._status("OFFLINE")


def _extract_number(text: str) -> int | None:
    """Pull the first integer out of a spoken command."""
    import re
    m = re.search(r'\b(\d{1,3})\b', text)
    if m:
        return int(m.group(1))
    # Word-number fallback
    words = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
             "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
             "hundred": 100}
    for w, v in words.items():
        if w in text:
            return v
    return None


def _normalize_email(spoken: str) -> str:
    """Convert spoken email forms to a normal address."""
    s = spoken.lower().strip()
    s = s.replace(" at ", "@").replace(" dot ", ".")
    s = s.replace(" underscore ", "_").replace(" dash ", "-")
    s = s.replace(" ", "")
    return s


# ============================================================
# GUI
# ============================================================
class JarvisGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.msg_queue: queue.Queue = queue.Queue()
        self.worker: JarvisWorker | None = None

        root.title(f"{config.assistant_name} AI Assistant")
        root.geometry("720x560")
        root.minsize(560, 420)
        root.configure(bg="#0f0f1a")

        self._build_styles()
        self._build_header()
        self._build_log()
        self._build_controls()
        self._build_status_bar()

        # Poll the queue ~30 times/sec
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
        # Tag styles
        self.log.tag_config("jarvis", foreground=self.accent, font=("Consolas", 11, "bold"))
        self.log.tag_config("user", foreground="#7ab8ff", font=("Consolas", 11, "bold"))
        self.log.tag_config("system", foreground=self.muted, font=("Consolas", 10, "italic"))

    def _build_controls(self):
        bar = tk.Frame(self.root, bg=self.bg)
        bar.pack(fill="x", padx=16, pady=(0, 8))

        self.start_btn = tk.Button(bar, text="▶  START", command=self.start,
                                   bg=self.accent, fg="#000000",
                                   activebackground="#00cc7a", activeforeground="#000000",
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
                                      relief="flat", padx=12, pady=8, cursor="hand2")
        self.settings_btn.pack(side="right")

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg="#000000")
        bar.pack(fill="x", side="bottom")
        self.status_dot = tk.Label(bar, text="●", fg="#555555", bg="#000000",
                                   font=("Consolas", 14))
        self.status_dot.pack(side="left", padx=(10, 4))
        self.status_label = tk.Label(bar, text="OFFLINE", fg=self.muted, bg="#000000",
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
                elif kind == "exit":
                    self.stop()
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
        self.worker = JarvisWorker(self.msg_queue)
        self.worker.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop(self):
        if self.worker:
            self.worker._stop_flag.set()
            self._append_log("System", "Stop requested. Finishing current task...")
            self.worker = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("OFFLINE")

    def show_config(self):
        caps = system_control.capabilities()
        info = (
            f"Assistant name : {config.assistant_name}\n"
            f"Wake word      : '{config.wake_word}'\n"
            f"Default city   : {config.default_city}\n"
            f"News country   : {config.news_country}\n"
            f"OpenAI model   : {config.openai_model}\n\n"
            f"API keys configured:\n"
            f"  OpenAI  : {'YES' if config.has_openai else 'NO'}\n"
            f"  Weather : {'YES' if config.has_weather else 'NO'}\n"
            f"  News    : {'YES' if config.has_news else 'NO'}\n"
            f"  Email   : {'YES' if config.has_email else 'NO'}\n\n"
            f"System controls available:\n"
            f"  Volume     : {'YES' if caps['volume'] else 'NO'}\n"
            f"  Brightness : {'YES' if caps['brightness'] else 'NO'}\n\n"
            f"Contacts: {', '.join(config.contacts.keys()) or 'none'}\n\n"
            f"To configure API keys, edit the .env file in this folder.\n"
            f"(Copy .env.example to .env if you haven't already.)"
        )
        messagebox.showinfo("Configuration", info)


# ============================================================
# MAIN
# ============================================================
def main():
    root = tk.Tk()
    app = JarvisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
