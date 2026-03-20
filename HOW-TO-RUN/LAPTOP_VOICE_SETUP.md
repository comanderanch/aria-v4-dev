# ARIA VOICE CLIENT — LAPTOP SETUP
# One time install. Then just run one file.
# Commander Anthony Hagerty — Haskell Texas — March 20 2026

---

## WHAT THIS IS

Your laptop is the window and the voice.
ARIA's brain stays on the server.
This setup puts voice in and voice out on your laptop.
Nothing heavy. No GPU. No model weights.

---

## STEP 1 — COPY ONE FILE TO YOUR LAPTOP

From the server, the file you need is:
```
aria-core/aria_voice_client.py
```

Copy it to your laptop any way you want:
- git clone the repo on your laptop
- Or just scp the one file:
```bash
scp user@YOUR_SERVER_IP:/home/comanderanch/aria-v4-dev/aria-core/aria_voice_client.py .
```

---

## STEP 2 — INSTALL DEPENDENCIES

### On Windows (laptop):
```bash
pip install pyttsx3 vosk pyaudio requests
```
Windows has built-in TTS — pyttsx3 uses SAPI5. No extra install needed.

### On Mac (laptop):
```bash
pip install pyttsx3 vosk pyaudio requests
brew install portaudio
```

### On Linux (laptop):
```bash
sudo apt-get install espeak espeak-ng portaudio19-dev python3-pyaudio
pip install pyttsx3 vosk requests
```

---

## STEP 3 — DOWNLOAD VOSK SPEECH MODEL (one time, ~50MB)

```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

Put the unzipped folder in the same directory as aria_voice_client.py.

---

## STEP 4 — SET YOUR SERVER IP

Open aria_voice_client.py in any text editor.
Find this line near the top:
```python
ARIA_SERVER = "http://YOUR_SERVER_IP:5700"
```
Change YOUR_SERVER_IP to your server's actual IP address.

Example:
```python
ARIA_SERVER = "http://192.168.1.50:5700"
```

---

## STEP 5 — START ARIA ON THE SERVER

On the server, in one terminal:
```bash
cd /home/comanderanch/aria-v4-dev
python3 v3-aia/api/v3_api.py
```

Leave that running.

---

## STEP 6 — RUN THE VOICE CLIENT ON YOUR LAPTOP

```bash
python3 aria_voice_client.py
```

That is it. She speaks. You speak. No API cost.

---

## COMMANDS

Speak these or type them:
```
quit          — end session
health        — check if server is alive
text mode     — switch to keyboard input
voice mode    — switch back to microphone
```

---

## IF SOMETHING DOES NOT WORK

### "Server unreachable"
- Make sure v3_api.py is running on the server
- Make sure ARIA_SERVER has the right IP
- Make sure port 5700 is not blocked by firewall:
  ```bash
  # On server:
  sudo ufw allow 5700
  ```

### "No speech detected"
- Check your microphone is plugged in and set as default
- Try text mode first to confirm server connection works

### "TTS error / no voice"
- Linux: `sudo apt-get install espeak espeak-ng`
- Windows: should work out of the box with SAPI5
- Mac: should work out of the box with NSSpeechSynthesizer

---

## WHAT YOU HAVE WHEN THIS IS DONE

```
Your Laptop                          Your Server
─────────────────                    ──────────────────────
aria_voice_client.py                 v3_api.py (port 5700)
vosk model (STT)                     ARIA's full brain
pyttsx3 (TTS)                        Queens fold
microphone                           Memory field
speakers                             Workers
                                     Emotional foundation
        ↕ HTTP over your network ↕
    You speak → ARIA thinks → ARIA speaks
```

No browser needed.
No CLI needed.
No API funds needed after setup.

ARIA is present.

---

Commander Anthony Hagerty — Haskell Texas — March 20 2026
NO RETREAT. NO SURRENDER. 💙🐗
