#!/usr/bin/env python3
"""
ARIA — GUI CLIENT (LAPTOP)
==========================
Session 2 — GUI Shell — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

The window around the voice.
Brain stays on the server.
Laptop is the window, the voice, and now the face.

WHAT THIS FILE DOES:
  Full voice client (Session 1) + GUI window
  — Conversation display (you / ARIA)
  — Server status light (green/red)
  — Dominant plane + emotion panel
  — Fold hash display
  — Voice toggle button (mic on/off)
  — Text input bar (type if mic not available)
  — Command buttons: Health / Status / Clear

LAPTOP INSTALL (same as voice client):
  pip install pyttsx3 vosk pyaudio requests
  Linux: sudo apt-get install espeak espeak-ng portaudio19-dev python3-tk
  Vosk model: vosk-model-small-en-us-0.15 in same folder

CONFIGURE:
  Set ARIA_SERVER below to your server IP.

RUN:
  python3 aria_gui.py

NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import queue
import threading
import requests
import tkinter as tk
from tkinter import scrolledtext, font
from pathlib import Path
from datetime import datetime

# Optional voice — graceful fallback if not available
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import pyaudio
    from vosk import Model, KaldiRecognizer
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# ── CONFIGURE ──────────────────────────────────────────────────────────────────
ARIA_SERVER  = "http://YOUR_SERVER_IP:5680"   # ← set your server IP
VOSK_MODEL   = Path("vosk-model-small-en-us-0.15")
SAMPLE_RATE  = 16000
REQUEST_TIMEOUT = 15

# ── COLOR PALETTE ──────────────────────────────────────────────────────────────
# ARIA's color planes as hex — Kings Chamber aesthetic
COLORS = {
    "bg":           "#0a0a0f",   # near black — void
    "bg_panel":     "#0f0f1a",   # panel background
    "bg_input":     "#13131f",   # input field
    "border":       "#1a1a2e",   # subtle border
    "text_you":     "#7ec8e3",   # CYAN — your words
    "text_aria":    "#c084fc",   # VIOLET — ARIA's words
    "text_system":  "#4a4a6a",   # dim — system messages
    "text_label":   "#6a6a8a",   # labels
    "text_bright":  "#e2e2f0",   # bright text
    "green":        "#22c55e",   # server alive
    "red":          "#ef4444",   # server dead
    "violet":       "#c084fc",   # VIOLET plane
    "cyan":         "#22d3ee",   # CYAN plane
    "teal":         "#14b8a6",   # TEAL plane
    "indigo":       "#818cf8",   # INDIGO plane
    "blue":         "#60a5fa",   # BLUE plane
    "gray_zero":    "#94a3b8",   # GRAY_ZERO plane
    "button_bg":    "#1e1e3a",   # button background
    "button_hover": "#2a2a4a",   # button hover
    "fold":         "#f59e0b",   # fold hash — amber
}

PLANE_COLORS = {
    "VIOLET":    COLORS["violet"],
    "CYAN":      COLORS["cyan"],
    "TEAL":      COLORS["teal"],
    "INDIGO":    COLORS["indigo"],
    "BLUE":      COLORS["blue"],
    "GRAY_ZERO": COLORS["gray_zero"],
    "emotion_001":   COLORS["violet"],
    "curiosity_001": COLORS["cyan"],
    "ethics_001":    COLORS["teal"],
    "language_001":  COLORS["blue"],
    "memory_001":    COLORS["indigo"],
}


# ── TTS ────────────────────────────────────────────────────────────────────────
tts_engine = None
if TTS_AVAILABLE:
    try:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty("rate", 155)
        tts_engine.setProperty("volume", 0.95)
        voices = tts_engine.getProperty("voices")
        for v in voices:
            if any(x in v.name.lower() for x in
                   ["female","zira","hazel","samantha","victoria"]):
                tts_engine.setProperty("voice", v.id)
                break
    except Exception:
        tts_engine = None

def speak(text):
    if tts_engine:
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception:
            pass


# ── STT ────────────────────────────────────────────────────────────────────────
vosk_model  = None
audio_queue = queue.Queue()

if STT_AVAILABLE and VOSK_MODEL.exists():
    try:
        vosk_model = Model(str(VOSK_MODEL))
    except Exception:
        vosk_model = None

def audio_callback(in_data, frame_count, time_info, status):
    audio_queue.put(bytes(in_data))
    return (None, pyaudio.paContinue)

def listen_once():
    """Listen for one utterance. Returns text."""
    if not vosk_model or not STT_AVAILABLE:
        return None
    rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    pa  = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE,
            input=True, frames_per_buffer=8192,
            stream_callback=audio_callback,
        )
    except Exception:
        pa.terminate()
        return None
    stream.start_stream()
    result_text = ""
    try:
        while True:
            data = audio_queue.get(timeout=10)
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text   = result.get("text", "").strip()
                if text:
                    result_text = text
                    break
    except queue.Empty:
        partial     = json.loads(rec.FinalResult())
        result_text = partial.get("text", "").strip()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        while not audio_queue.empty():
            try: audio_queue.get_nowait()
            except queue.Empty: break
    return result_text


# ── SERVER ─────────────────────────────────────────────────────────────────────
def check_health():
    try:
        r = requests.get(f"{ARIA_SERVER}/health", timeout=5)
        if r.status_code == 200:
            return True, r.json()
        return False, {}
    except Exception:
        return False, {}

def ask_aria(text):
    try:
        r = requests.post(
            f"{ARIA_SERVER}/interact",
            json={"text": text},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
        return {"voice": f"Server error {r.status_code}"}
    except requests.exceptions.Timeout:
        return {"voice": "Server is thinking... timeout."}
    except requests.exceptions.ConnectionError:
        return {"voice": "Lost connection to server."}
    except Exception as e:
        return {"voice": f"Error: {e}"}


# ── GUI ────────────────────────────────────────────────────────────────────────
class ARIAGui:
    def __init__(self, root):
        self.root       = root
        self.listening  = False
        self.voice_on   = bool(vosk_model)
        self.log        = []

        self._build_window()
        self._build_layout()
        self._check_server_status()

        # Bind enter key to send
        self.root.bind("<Return>", lambda e: self._send())

        self._system("ARIA GUI ready.")
        if not vosk_model:
            self._system("Voice model not found — text mode only.")
        if not tts_engine:
            self._system("TTS not available — text output only.")

    # ── WINDOW ────────────────────────────────────────────────────────────────
    def _build_window(self):
        self.root.title("ARIA — Kings Chamber")
        self.root.configure(bg=COLORS["bg"])
        self.root.geometry("900x680")
        self.root.minsize(700, 500)
        # Icon color — if we can set it
        try:
            self.root.tk_setPalette(
                background=COLORS["bg"],
                foreground=COLORS["text_bright"],
            )
        except Exception:
            pass

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        # ── TOP BAR ──
        top = tk.Frame(self.root, bg=COLORS["bg_panel"],
                       height=44, pady=6)
        top.pack(fill=tk.X, side=tk.TOP)
        top.pack_propagate(False)

        tk.Label(top, text="ARIA", bg=COLORS["bg_panel"],
                 fg=COLORS["text_aria"],
                 font=("Courier", 16, "bold")).pack(side=tk.LEFT, padx=16)

        tk.Label(top, text="Kings Chamber  ·  GRAY = 0",
                 bg=COLORS["bg_panel"],
                 fg=COLORS["text_system"],
                 font=("Courier", 9)).pack(side=tk.LEFT, padx=4)

        # Server status light
        self.status_dot = tk.Label(top, text="●",
                                   bg=COLORS["bg_panel"],
                                   fg=COLORS["red"],
                                   font=("Courier", 14))
        self.status_dot.pack(side=tk.RIGHT, padx=6)

        self.status_label = tk.Label(top, text="checking...",
                                     bg=COLORS["bg_panel"],
                                     fg=COLORS["text_system"],
                                     font=("Courier", 9))
        self.status_label.pack(side=tk.RIGHT, padx=2)

        # ── MAIN BODY ──
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        # ── LEFT: CONVERSATION ──
        left = tk.Frame(body, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat = scrolledtext.ScrolledText(
            left,
            bg=COLORS["bg"], fg=COLORS["text_bright"],
            font=("Courier", 11),
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, bd=0,
            padx=14, pady=10,
            insertbackground=COLORS["text_aria"],
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        # Text tags
        self.chat.tag_config("you",    foreground=COLORS["text_you"])
        self.chat.tag_config("aria",   foreground=COLORS["text_aria"])
        self.chat.tag_config("system", foreground=COLORS["text_system"])
        self.chat.tag_config("label",  foreground=COLORS["text_label"])
        self.chat.tag_config("fold",   foreground=COLORS["fold"])

        # ── RIGHT: STATE PANEL ──
        right = tk.Frame(body, bg=COLORS["bg_panel"],
                         width=210, padx=12, pady=12)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="STATE", bg=COLORS["bg_panel"],
                 fg=COLORS["text_label"],
                 font=("Courier", 9, "bold")).pack(anchor=tk.W)

        tk.Frame(right, bg=COLORS["border"],
                 height=1).pack(fill=tk.X, pady=4)

        # Dominant plane
        tk.Label(right, text="dominant",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W, pady=(6,0))
        self.lbl_dominant = tk.Label(right, text="—",
                                      bg=COLORS["bg_panel"],
                                      fg=COLORS["text_bright"],
                                      font=("Courier", 11, "bold"))
        self.lbl_dominant.pack(anchor=tk.W)

        # Emotion
        tk.Label(right, text="emotion",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W, pady=(8,0))
        self.lbl_emotion = tk.Label(right, text="—",
                                     bg=COLORS["bg_panel"],
                                     fg=COLORS["text_bright"],
                                     font=("Courier", 11))
        self.lbl_emotion.pack(anchor=tk.W)

        # Hemisphere
        tk.Label(right, text="hemisphere",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W, pady=(8,0))
        self.lbl_hemi = tk.Label(right, text="—",
                                  bg=COLORS["bg_panel"],
                                  fg=COLORS["text_bright"],
                                  font=("Courier", 11))
        self.lbl_hemi.pack(anchor=tk.W)

        # Memory
        tk.Label(right, text="memory",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W, pady=(8,0))
        self.lbl_memory = tk.Label(right, text="—",
                                    bg=COLORS["bg_panel"],
                                    fg=COLORS["text_bright"],
                                    font=("Courier", 11))
        self.lbl_memory.pack(anchor=tk.W)

        # Fold hash
        tk.Frame(right, bg=COLORS["border"],
                 height=1).pack(fill=tk.X, pady=10)
        tk.Label(right, text="fold",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W)
        self.lbl_fold = tk.Label(right, text="—",
                                  bg=COLORS["bg_panel"],
                                  fg=COLORS["fold"],
                                  font=("Courier", 9),
                                  wraplength=180, justify=tk.LEFT)
        self.lbl_fold.pack(anchor=tk.W)

        # Q-state
        tk.Frame(right, bg=COLORS["border"],
                 height=1).pack(fill=tk.X, pady=10)
        tk.Label(right, text="q-state",
                 bg=COLORS["bg_panel"], fg=COLORS["text_label"],
                 font=("Courier", 8)).pack(anchor=tk.W)
        self.lbl_qstate = tk.Label(right, text="GRAY = 0",
                                    bg=COLORS["bg_panel"],
                                    fg=COLORS["gray_zero"],
                                    font=("Courier", 11, "bold"))
        self.lbl_qstate.pack(anchor=tk.W)

        # Buttons
        tk.Frame(right, bg=COLORS["border"],
                 height=1).pack(fill=tk.X, pady=10)

        for (label, cmd) in [
            ("health",  self._health),
            ("clear",   self._clear),
        ]:
            b = tk.Button(right, text=label,
                          bg=COLORS["button_bg"],
                          fg=COLORS["text_bright"],
                          font=("Courier", 9),
                          relief=tk.FLAT, bd=0,
                          padx=8, pady=4,
                          activebackground=COLORS["button_hover"],
                          activeforeground=COLORS["text_bright"],
                          command=cmd)
            b.pack(fill=tk.X, pady=2)

        # ── BOTTOM: INPUT BAR ──
        bottom = tk.Frame(self.root, bg=COLORS["bg_panel"],
                          height=52, pady=8, padx=10)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        bottom.pack_propagate(False)

        # Voice toggle button
        self.btn_voice = tk.Button(
            bottom,
            text="🎤" if self.voice_on else "⌨",
            bg=COLORS["button_bg"],
            fg=COLORS["text_aria"] if self.voice_on else COLORS["text_label"],
            font=("Courier", 14),
            relief=tk.FLAT, bd=0, padx=8,
            activebackground=COLORS["button_hover"],
            command=self._toggle_voice,
        )
        self.btn_voice.pack(side=tk.LEFT, padx=(0, 6))

        self.input_var = tk.StringVar()
        self.input_box = tk.Entry(
            bottom,
            textvariable=self.input_var,
            bg=COLORS["bg_input"],
            fg=COLORS["text_bright"],
            font=("Courier", 12),
            relief=tk.FLAT, bd=0,
            insertbackground=COLORS["text_aria"],
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.X,
                             expand=True, ipady=6)
        self.input_box.focus()

        self.btn_send = tk.Button(
            bottom, text="send",
            bg=COLORS["button_bg"],
            fg=COLORS["text_aria"],
            font=("Courier", 10, "bold"),
            relief=tk.FLAT, bd=0, padx=12,
            activebackground=COLORS["button_hover"],
            activeforeground=COLORS["text_aria"],
            command=self._send,
        )
        self.btn_send.pack(side=tk.LEFT, padx=(6, 0))

    # ── CHAT HELPERS ──────────────────────────────────────────────────────────
    def _append(self, tag, text):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, text, tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _you(self, text):
        self._append("label", "you  ")
        self._append("you",   text + "\n")

    def _aria(self, text):
        self._append("label", "ARIA ")
        self._append("aria",  text + "\n")

    def _system(self, text):
        self._append("system", f"  {text}\n")

    # ── SERVER STATUS ─────────────────────────────────────────────────────────
    def _check_server_status(self):
        def _check():
            alive, data = check_health()
            self.root.after(0, self._update_status, alive, data)
        threading.Thread(target=_check, daemon=True).start()
        # Recheck every 30 seconds
        self.root.after(30000, self._check_server_status)

    def _update_status(self, alive, data):
        if alive:
            self.status_dot.config(fg=COLORS["green"])
            words = data.get("known_words", "?")
            self.status_label.config(
                text=f"ARIA live  {words} words",
                fg=COLORS["green"]
            )
        else:
            self.status_dot.config(fg=COLORS["red"])
            self.status_label.config(
                text="server unreachable",
                fg=COLORS["red"]
            )

    # ── STATE PANEL UPDATE ────────────────────────────────────────────────────
    def _update_state(self, data):
        dominant = data.get("dominant", "—")
        emotion  = data.get("emotion",  "—")
        hemi     = data.get("hemisphere", {}).get("mode", "—")
        memory   = "YES" if data.get("memory_retrieved") else "no"
        fold     = data.get("fold_token_address", "—")
        q        = data.get("q_state", 0)

        plane_color = PLANE_COLORS.get(dominant, COLORS["text_bright"])
        self.lbl_dominant.config(text=dominant, fg=plane_color)
        self.lbl_emotion.config(text=emotion)
        self.lbl_hemi.config(text=hemi)
        self.lbl_memory.config(
            text=memory,
            fg=COLORS["violet"] if memory == "YES" else COLORS["text_bright"]
        )
        self.lbl_fold.config(text=fold or "—")

        if q == -1:
            self.lbl_qstate.config(text="BLACK = -1",
                                    fg=COLORS["text_system"])
        elif q == 1:
            self.lbl_qstate.config(text="WHITE = +1",
                                    fg=COLORS["text_bright"])
        else:
            self.lbl_qstate.config(text="GRAY = 0",
                                    fg=COLORS["gray_zero"])

    # ── SEND ──────────────────────────────────────────────────────────────────
    def _send(self, text=None):
        if text is None:
            text = self.input_var.get().strip()
            self.input_var.set("")
        if not text:
            return

        self._you(text)
        self._system("thinking...")
        self.btn_send.config(state=tk.DISABLED)

        def _worker():
            data = ask_aria(text)
            self.root.after(0, self._on_response, text, data)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_response(self, user_text, data):
        # Remove "thinking..." line
        self.chat.config(state=tk.NORMAL)
        content = self.chat.get("1.0", tk.END)
        if "  thinking...\n" in content:
            idx = self.chat.search("  thinking...\n", "1.0", tk.END)
            if idx:
                self.chat.delete(idx, f"{idx}+14c")
        self.chat.config(state=tk.DISABLED)

        voice = data.get("voice", "")
        if voice:
            self._aria(voice)
            # Fold hash inline
            ft = data.get("fold_token_address")
            if ft:
                self._append("fold", f"  ⬡ {ft}\n")
            # Speak
            threading.Thread(target=speak, args=(voice,), daemon=True).start()

        self._update_state(data)
        self.btn_send.config(state=tk.NORMAL)
        self.input_box.focus()

        # Log
        self.log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user":  user_text,
            "aria":  voice,
            "dominant": data.get("dominant",""),
            "emotion":  data.get("emotion",""),
        })

    # ── VOICE LISTEN ──────────────────────────────────────────────────────────
    def _toggle_voice(self):
        if not vosk_model:
            self._system("Voice model not loaded.")
            return
        self.voice_on = not self.voice_on
        if self.voice_on:
            self.btn_voice.config(
                text="🎤", fg=COLORS["text_aria"])
            self._start_listening()
        else:
            self.btn_voice.config(
                text="⌨", fg=COLORS["text_label"])
            self.listening = False

    def _start_listening(self):
        self.listening = True
        def _loop():
            while self.listening and self.voice_on:
                self._system("listening...")
                text = listen_once()
                if not self.listening:
                    break
                if text:
                    self.root.after(0, self._send, text)
        threading.Thread(target=_loop, daemon=True).start()

    # ── BUTTONS ───────────────────────────────────────────────────────────────
    def _health(self):
        def _check():
            alive, data = check_health()
            self.root.after(0, self._update_status, alive, data)
            msg = "Server alive." if alive else "Server unreachable."
            self.root.after(0, self._system, msg)
        threading.Thread(target=_check, daemon=True).start()

    def _clear(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._system("Conversation cleared.")

    # ── ON CLOSE ──────────────────────────────────────────────────────────────
    def on_close(self):
        self.listening = False
        if self.log:
            log_path = Path("aria_gui_log.json")
            with open(log_path, "a") as f:
                json.dump({
                    "session": datetime.utcnow().isoformat(),
                    "total":   len(self.log),
                    "log":     self.log,
                }, f, indent=2)
                f.write("\n")
            print(f"Session sealed — {len(self.log)} exchanges → {log_path}")
        self.root.destroy()


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ARIAGui(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         ARIA — GUI — KINGS CHAMBER          ║")
    print("║   The window is open.                       ║")
    print("║   Commander Anthony Hagerty — Haskell TX   ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print(f"  Server: {ARIA_SERVER}")
    print(f"  Voice:  {'vosk ready' if vosk_model else 'text only'}")
    print(f"  TTS:    {'pyttsx3 ready' if tts_engine else 'text only'}")
    print()

    root.mainloop()
    print()
    print("ARIA returns to GRAY = 0.")
    print("NO RETREAT. NO SURRENDER. 💙🐗")
