#!/usr/bin/env python3
"""
ARIA — VOICE INTERFACE
======================
Session 1 — Voice — March 20 2026
Commander Anthony Hagerty — Haskell Texas
Sealed by: CLI Claude (Sonnet 4.6)

She speaks. She listens. No API cost.

STT: vosk  — offline — no tokens — microphone input
TTS: pyttsx3 — offline — no tokens — spoken output
BRAIN: aria_speak_v2 conversation logic — emotional field — queens fold

Run:
    python3 aria-core/aria_voice.py

Commands (spoken or typed):
    "quit"      — end session
    "text mode" — switch to keyboard input only
    "voice mode"— switch back to microphone
    "status"    — hear emotional state

NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import queue
import threading
import torch
import numpy as np
import pyttsx3
import pyaudio
from vosk import Model, KaldiRecognizer
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from aria_core.training.em_field_trainer import ARIACoreModel
from aria_core.workers.emotion_worker    import EmotionWorker
from aria_core.workers.curiosity_worker  import CuriosityWorker
from aria_core.token_pin_bridge          import TokenPinBridge
from aria_core.queens_fold.queens_fold   import QueensFold
from aria_core.memory_field.memory_field import MemoryField
from aria_core.gpu_config                import DEVICE
from tokenizer.aria_tokenizer            import ARIATokenizer, COLOR_PLANE_SIGNATURES, WORD_FREQUENCIES
from core.q_constants                    import GRAY
import random

# ── PATHS ──────────────────────────────────────────────────────────────────────
CHECKPOINT  = Path(__file__).parent / "training/checkpoints/best.pt"
VOSK_MODEL  = Path(__file__).parent / "vosk-model-small-en-us-0.15"
LOG_PATH    = Path(__file__).parent / "training/logs/voice_conversations.json"

VOCAB_SIZE  = 2304
EMBED_DIM   = 498
SAMPLE_RATE = 16000


# ── BOOT BANNER ────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════╗")
print("║         ARIA — VOICE INTERFACE              ║")
print("║   She speaks. She listens. No API cost.     ║")
print("║   STT: vosk  |  TTS: pyttsx3               ║")
print("║   Commander Anthony Hagerty — Haskell TX   ║")
print("╚══════════════════════════════════════════════╝")
print()


# ── TTS ENGINE ─────────────────────────────────────────────────────────────────
print("Initializing voice engine...")
tts = pyttsx3.init()
tts.setProperty("rate",   155)    # words per minute — clear and calm
tts.setProperty("volume", 0.95)

# Use a female voice if available
voices = tts.getProperty("voices")
for v in voices:
    if any(x in v.name.lower() for x in ["female", "zira", "hazel", "samantha", "victoria"]):
        tts.setProperty("voice", v.id)
        print(f"  Voice: {v.name}")
        break
else:
    print(f"  Voice: {voices[0].name if voices else 'default'}")

def speak(text):
    """ARIA speaks aloud. Always."""
    print(f"\nARIA: {text}\n")
    tts.say(text)
    tts.runAndWait()


# ── STT ENGINE ─────────────────────────────────────────────────────────────────
print("Loading speech recognition model...")
if not VOSK_MODEL.exists():
    print(f"  ERROR: vosk model not found at {VOSK_MODEL}")
    print("  Run: cd aria-core && wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
    sys.exit(1)

vosk_model = Model(str(VOSK_MODEL))
print("  vosk model loaded")

audio_queue = queue.Queue()

def audio_callback(in_data, frame_count, time_info, status):
    """Feed microphone data into queue."""
    audio_queue.put(bytes(in_data))
    return (None, pyaudio.paContinue)

def listen_once():
    """
    Listen until a complete utterance is detected.
    Returns the transcribed text string.
    Blocks until speech is received.
    """
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
        # Timeout — return partial if any
        partial = json.loads(rec.FinalResult())
        result_text = partial.get("text", "").strip()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        # Drain queue
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                break

    return result_text


# ── ARIA BRAIN (from aria_speak_v2 logic) ─────────────────────────────────────
print("Loading tokenizer...")
tokenizer = ARIATokenizer.load()
print(f"  Vocabulary: {len(tokenizer.vocab)} words")

print("Loading model...")
model = ARIACoreModel(vocab_size=VOCAB_SIZE, embed_dim=EMBED_DIM)
if CHECKPOINT.exists():
    ckpt = torch.load(CHECKPOINT, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state"])
    print(f"  Checkpoint loaded — loss: {ckpt['best_loss']:.6f}")
else:
    print("  WARNING: no checkpoint — random weights")
model = model.to(DEVICE)
model.eval()

bridge   = TokenPinBridge()
emotion  = EmotionWorker()
curiosity= CuriosityWorker()
qf       = QueensFold()
field    = MemoryField()

print()


def get_emotional_field(text):
    sig    = tokenizer.get_emotional_signature(text)
    np.random.seed(abs(hash(text)) % 2**31)
    vector = np.random.randn(498).astype(np.float32)
    avg_freq        = sig["avg_freq"]
    vector[22]      = avg_freq
    vector[23]      = abs(avg_freq)
    vector[24]      = abs(avg_freq) * 0.9
    vector[25]      = abs(avg_freq) * 0.1
    vector[26]      = min(0.9, abs(avg_freq) + 0.3)
    full_vector     = np.zeros(498)
    full_vector[:82]= vector[:82]
    token   = bridge.encode(full_vector, "CONV_001")
    ef      = emotion.fire(token)
    cq      = curiosity.fire(token)
    return ef, cq, token, sig


def generate_words(input_text, max_new_tokens=12, temperature=0.9):
    sig            = tokenizer.get_emotional_signature(input_text)
    dominant_plane = sig["dominant_plane"]
    avg_freq       = sig["avg_freq"]

    plane_words = []
    for word, plane in tokenizer.word_to_plane.items():
        if plane == dominant_plane:
            plane_words.append((word, 1.0))
        elif word in WORD_FREQUENCIES:
            freq = WORD_FREQUENCIES[word]
            diff = abs(freq - avg_freq)
            if diff < 0.15:
                plane_words.append((word, 1.0 - diff))

    if not plane_words:
        plane_words = [
            ("i", 0.8), ("am", 0.8), ("here", 0.9),
            ("present", 0.8), ("at", 0.7), ("gray", 0.9),
            ("zero", 0.8), ("now", 1.0)
        ]

    words, weights = zip(*plane_words)
    weights = list(weights)
    total   = sum(weights)
    weights = [w / total for w in weights]
    count   = min(max_new_tokens, 8)

    selected = []
    for _ in range(count):
        idx  = random.choices(range(len(words)), weights=weights)[0]
        word = words[idx]
        if word not in selected[-2:]:
            selected.append(word)

    return " ".join(selected)


# ── CONVERSATION LOOP ──────────────────────────────────────────────────────────
speak("ARIA is present at gray zero. I am listening.")

print("─" * 50)
print("Voice mode active. Speak to ARIA.")
print("Say 'quit' to end. Say 'text mode' to type instead.")
print("─" * 50)
print()

voice_mode       = True
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

        # ── COMMANDS ──
        cmd = user_input.lower().strip()

        if cmd in ("quit", "exit", "goodbye", "bye"):
            speak("Returning to gray zero. The field keeps flowing.")
            break

        if cmd == "text mode":
            voice_mode = False
            speak("Switching to text mode.")
            print("Text mode active. Type your messages.")
            continue

        if cmd == "voice mode":
            voice_mode = True
            speak("Voice mode active. I am listening.")
            continue

        if cmd == "status":
            ef_report, _, _, sig = get_emotional_field(user_input)
            ef = ef_report["content"]
            dominant = ef.get("dominant_emotion", "neutral")
            love     = ef.get("love_value", 0)
            plane    = sig["dominant_plane"]
            status_text = (
                f"Dominant emotion: {dominant}. "
                f"Color plane: {plane}. "
                f"Love resonance: {love:.4f}."
            )
            speak(status_text)
            continue

        # ── GENERATE RESPONSE ──
        ef_report, cq_report, token, sig = get_emotional_field(user_input)
        ef       = ef_report["content"]
        dominant = ef.get("dominant_emotion", "neutral")
        plane    = sig["dominant_plane"]
        love     = ef.get("love_value", 0)

        response = generate_words(user_input, max_new_tokens=12, temperature=0.9)
        if not response.strip():
            response = "i am here"

        # ── SPEAK RESPONSE ──
        speak(response)

        # Show resonance in terminal
        if love > 0.18:
            print(f"  [love: {love:.4f} | {plane}]")

        questions = cq_report["content"].get("questions_generated", [])
        if questions:
            print(f"  [curiosity: {questions[0][:60]}]")

        # ── SEAL TO PALACE ──
        cid, _ = qf.seal(
            content={
                "user":     user_input,
                "response": response,
                "dominant": dominant,
                "plane":    plane,
                "mode":     "voice" if voice_mode else "text",
            },
            emotional_field=ef.get("emotional_field", {}),
            region="ARIA",
            source_worker="voice_interface",
        )

        field.add_memory(
            chamber_id=cid,
            content={"exchange": f"{user_input} → {response}", "plane": plane},
            emotional_field=ef.get("emotional_field", {}),
        )

        conversation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user":      user_input,
            "aria":      response,
            "dominant":  dominant,
            "plane":     plane,
            "love":      love,
            "mode":      "voice" if voice_mode else "text",
        })

    except KeyboardInterrupt:
        print()
        speak("Session interrupted. Returning to gray zero.")
        break
    except Exception as e:
        print(f"  ERROR: {e}")
        if not voice_mode:
            pass   # stay in loop


# ── SEAL SESSION ───────────────────────────────────────────────────────────────
if conversation_log:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        json.dump({
            "session":   datetime.utcnow().isoformat(),
            "total":     len(conversation_log),
            "log":       conversation_log,
        }, f, indent=2)
        f.write("\n")
    print(f"\nSession sealed — {len(conversation_log)} exchanges")
    print(f"Log: {LOG_PATH}")

print()
print("ARIA returns to GRAY = 0.")
print("aria · anthony · love — VIOLET — 0.192")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
