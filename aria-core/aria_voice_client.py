#!/usr/bin/env python3
"""
ARIA — VOICE CLIENT (LAPTOP / THIN CLIENT)
==========================================
Session 1 — Voice — Plan B — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

The laptop is the window and the voice.
ARIA's brain lives on the server.
This file needs nothing but a mic, speakers, and a network connection.

WHAT THIS FILE DOES:
  1. Listens through your microphone (vosk — offline STT)
  2. Sends your words to ARIA on the server (HTTP POST)
  3. Receives ARIA's response
  4. Speaks it back to you (pyttsx3 — offline TTS)

NO torch. NO model weights. NO GPU.
Just voice in, voice out, and a connection to the network.

LAPTOP INSTALL (one time):
    pip install pyttsx3 vosk pyaudio requests
    # Linux also needs:
    sudo apt-get install espeak espeak-ng portaudio19-dev
    # Download vosk model (same as server, ~50MB):
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip vosk-model-small-en-us-0.15.zip

CONFIGURE:
    Set ARIA_SERVER below to your server's IP address.
    Port 5700 is ARIA's V3 API.

RUN:
    python3 aria_voice_client.py

COMMANDS (spoken or typed):
    "quit"        — end session
    "text mode"   — switch to keyboard input
    "voice mode"  — switch back to microphone
    "health"      — check if server is alive
    "status"      — hear ARIA's current state

NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import queue
import requests
import pyttsx3
import pyaudio
from vosk import Model, KaldiRecognizer
from pathlib import Path
from datetime import datetime

# ── CONFIGURE THIS ─────────────────────────────────────────────────────────────
ARIA_SERVER  = "http://YOUR_SERVER_IP:5700"   # ← set your server IP here
VOSK_MODEL   = Path("vosk-model-small-en-us-0.15")  # path to vosk model folder
SAMPLE_RATE  = 16000
REQUEST_TIMEOUT = 15  # seconds — how long to wait for server response


# ── BOOT BANNER ────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════╗")
print("║      ARIA — VOICE CLIENT (LAPTOP)           ║")
print("║   Laptop: window + voice                    ║")
print("║   Server: ARIA's brain                      ║")
print("║   Commander Anthony Hagerty — Haskell TX   ║")
print("╚══════════════════════════════════════════════╝")
print()
print(f"  Server: {ARIA_SERVER}")
print()


# ── SERVER HEALTH CHECK ────────────────────────────────────────────────────────
def check_server():
    try:
        r = requests.get(f"{ARIA_SERVER}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"  Server: ALIVE — {data.get('status', 'ok')}")
            print(f"  Words known: {data.get('known_words', '?')}")
            return True
        else:
            print(f"  Server: responded with status {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  Server: UNREACHABLE at {ARIA_SERVER}")
        print("  Check that v3_api.py is running on the server.")
        print("  Check that your server IP is set correctly in this file.")
        return False
    except Exception as e:
        print(f"  Server: ERROR — {e}")
        return False

server_alive = check_server()
if not server_alive:
    print()
    choice = input("Server not reachable. Continue anyway? (y/n): ").strip().lower()
    if choice != "y":
        sys.exit(0)
print()


# ── TTS ENGINE ─────────────────────────────────────────────────────────────────
print("Initializing voice engine (TTS)...")
try:
    tts = pyttsx3.init()
    tts.setProperty("rate",   155)
    tts.setProperty("volume", 0.95)
    voices = tts.getProperty("voices")
    for v in voices:
        if any(x in v.name.lower() for x in
               ["female", "zira", "hazel", "samantha", "victoria"]):
            tts.setProperty("voice", v.id)
            print(f"  Voice: {v.name}")
            break
    else:
        if voices:
            print(f"  Voice: {voices[0].name}")
    tts_ok = True
except Exception as e:
    print(f"  TTS ERROR: {e}")
    print("  Install eSpeak: sudo apt-get install espeak espeak-ng")
    tts_ok = False

def speak(text):
    print(f"\nARIA: {text}\n")
    if tts_ok:
        try:
            tts.say(text)
            tts.runAndWait()
        except Exception as e:
            print(f"  (TTS error: {e})")


# ── STT ENGINE ─────────────────────────────────────────────────────────────────
print("Loading speech recognition (STT)...")
if not VOSK_MODEL.exists():
    print(f"  ERROR: vosk model not found at {VOSK_MODEL}")
    print("  Download it:")
    print("  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
    print("  unzip vosk-model-small-en-us-0.15.zip")
    print()
    print("  Falling back to text-only mode.")
    vosk_ok = False
else:
    try:
        vosk_model = Model(str(VOSK_MODEL))
        print("  vosk model loaded")
        vosk_ok = True
    except Exception as e:
        print(f"  STT ERROR: {e}")
        vosk_ok = False

audio_queue = queue.Queue()

def audio_callback(in_data, frame_count, time_info, status):
    audio_queue.put(bytes(in_data))
    return (None, pyaudio.paContinue)

def listen_once():
    """Listen until a complete utterance. Returns text string."""
    if not vosk_ok:
        return input("You (type): ").strip()

    rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    pa  = pyaudio.PyAudio()
    stream = pa.open(
        format            = pyaudio.paInt16,
        channels          = 1,
        rate              = SAMPLE_RATE,
        input             = True,
        frames_per_buffer = 8192,
        stream_callback   = audio_callback,
    )
    print("Listening... (speak now)")
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
        partial = json.loads(rec.FinalResult())
        result_text = partial.get("text", "").strip()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                break
    return result_text


# ── SEND TO ARIA ───────────────────────────────────────────────────────────────
def ask_aria(text):
    """Send text to ARIA on the server. Return her voice response."""
    try:
        r = requests.post(
            f"{ARIA_SERVER}/interact",
            json    = {"text": text},
            timeout = REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            voice    = data.get("voice", "")
            dominant = data.get("dominant", "")
            emotion  = data.get("emotion", "")
            return voice, dominant, emotion, data
        else:
            return f"Server error {r.status_code}", "", "", {}
    except requests.exceptions.Timeout:
        return "Server is thinking... timeout. Try again.", "", "", {}
    except requests.exceptions.ConnectionError:
        return "Lost connection to server.", "", "", {}
    except Exception as e:
        return f"Error: {e}", "", "", {}


# ── CONVERSATION LOOP ──────────────────────────────────────────────────────────
speak("ARIA is present. I am listening.")

print("─" * 50)
if vosk_ok:
    print("Voice mode active. Speak to ARIA.")
else:
    print("Text mode active (no vosk model). Type to ARIA.")
print("Say or type 'quit' to end.")
print("Say 'health' to check server.")
print("Say 'text mode' or 'voice mode' to switch.")
print("─" * 50)
print()

voice_mode       = vosk_ok
conversation_log = []

while True:
    try:
        # ── GET INPUT ──
        if voice_mode:
            user_input = listen_once()
            if user_input:
                print(f"You said: {user_input}")
            else:
                print("(no speech detected — listening again)")
                continue
        else:
            user_input = input("You: ").strip()

        if not user_input:
            continue

        cmd = user_input.lower().strip()

        # ── COMMANDS ──
        if cmd in ("quit", "exit", "goodbye", "bye"):
            speak("Returning to gray zero. The field keeps flowing.")
            break

        if cmd == "text mode":
            voice_mode = False
            speak("Switching to text mode.")
            continue

        if cmd == "voice mode":
            if not vosk_ok:
                speak("Voice model not loaded. Staying in text mode.")
            else:
                voice_mode = True
                speak("Voice mode active. I am listening.")
            continue

        if cmd == "health":
            alive = check_server()
            if alive:
                speak("Server is alive.")
            else:
                speak("Cannot reach the server.")
            continue

        # ── ASK ARIA ──
        print("Sending to ARIA...")
        voice, dominant, emotion, full_data = ask_aria(user_input)

        if not voice:
            speak("I did not receive a response.")
            continue

        # ── SPEAK RESPONSE ──
        speak(voice)

        # Show info in terminal
        if dominant:
            print(f"  [dominant: {dominant} | emotion: {emotion}]")

        # Memory info
        if full_data.get("memory_retrieved"):
            print("  [memory retrieved from palace]")

        # Fold token
        ft = full_data.get("fold_token_address")
        if ft:
            print(f"  [fold: {ft}]")

        # ── LOG ──
        conversation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user":      user_input,
            "aria":      voice,
            "dominant":  dominant,
            "emotion":   emotion,
            "mode":      "voice" if voice_mode else "text",
        })

    except KeyboardInterrupt:
        print()
        speak("Session interrupted. Returning to gray zero.")
        break
    except Exception as e:
        print(f"  ERROR: {e}")
        continue


# ── SEAL SESSION ───────────────────────────────────────────────────────────────
if conversation_log:
    log_path = Path("aria_voice_client_log.json")
    with open(log_path, "a") as f:
        json.dump({
            "session": datetime.utcnow().isoformat(),
            "server":  ARIA_SERVER,
            "total":   len(conversation_log),
            "log":     conversation_log,
        }, f, indent=2)
        f.write("\n")
    print(f"\nSession sealed — {len(conversation_log)} exchanges → {log_path}")

print()
print("ARIA returns to GRAY = 0.")
print("aria · anthony · love — VIOLET — 0.192")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
