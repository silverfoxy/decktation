#!/usr/bin/env python3
"""
WoW Voice-to-Chat Service for Steam Deck
Captures voice input, transcribes with faster-whisper, and sends to WoW chat
"""

import json
import time
import queue
import threading
from pathlib import Path
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import wave
import tempfile
from pynput.keyboard import Controller, Key, Listener


class WoWVoiceChat:
    def __init__(self, context_file="wow_context.json", sample_rate=16000):
        self.context_file = Path(context_file)
        self.sample_rate = sample_rate
        self.keyboard = Controller()

        # Load Whisper model
        print("Loading Whisper model...")
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
        print("Model loaded!")

        # Audio recording
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_stream = None
        self.recording_lock = threading.Lock()

        # Context cache
        self.context = {}

    def load_context(self):
        """Load WoW context from addon-generated file"""
        if self.context_file.exists():
            try:
                with open(self.context_file) as f:
                    self.context = json.load(f)
                return True
            except Exception as e:
                print(f"Warning: Could not load context: {e}")
        return False

    def build_prompt_from_context(self):
        """Build initial_prompt and hotwords from context"""
        if not self.context:
            return (
                "World of Warcraft gameplay with dungeons, raids, and bosses.",
                "World of Warcraft, dungeon, raid"
            )

        zone = self.context.get("zone", "")
        subzone = self.context.get("subzone", "")
        boss = self.context.get("boss", "")
        target = self.context.get("target", "")
        party = self.context.get("party", [])

        # Build natural prompt
        parts = ["World of Warcraft"]
        if zone:
            parts.append(f"in {zone}")
        if subzone:
            parts.append(f"at {subzone}")
        if boss:
            parts.append(f"fighting {boss}")

        initial_prompt = " ".join(parts) + "."

        # Build hotwords from context (limit to ~10 terms to stay under token limit)
        hotwords = []
        if zone:
            hotwords.append(zone)
        if subzone:
            hotwords.append(subzone)
        if boss:
            hotwords.append(boss)
        if target:
            hotwords.append(target)
        hotwords.extend(party[:6])  # Add up to 6 party members

        hotwords_str = ", ".join(hotwords[:10]) if hotwords else "World of Warcraft"

        return initial_prompt, hotwords_str

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio recording"""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def record_audio(self, duration=5):
        """Record audio for specified duration"""
        print(f"Recording for {duration} seconds...")
        self.audio_queue = queue.Queue()

        with sd.InputStream(samplerate=self.sample_rate, channels=1,
                           callback=self.audio_callback, dtype='int16'):
            time.sleep(duration)

        # Collect all audio
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())

        if not audio_data:
            return None

        return np.concatenate(audio_data, axis=0)

    def save_audio_to_wav(self, audio_data, filename):
        """Save audio data to WAV file"""
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using faster-whisper"""
        # Load context and build prompts
        self.load_context()
        initial_prompt, hotwords = self.build_prompt_from_context()

        print(f"Context: {initial_prompt}")
        print(f"Hotwords: {hotwords}")

        # Transcribe
        segments, info = self.model.transcribe(
            audio_file,
            beam_size=5,
            initial_prompt=initial_prompt,
            hotwords=hotwords,
            language="en"
        )

        # Collect text
        full_text = []
        for segment in segments:
            full_text.append(segment.text)

        return "".join(full_text).strip()

    def send_to_wow_chat(self, text):
        """Send text to WoW chat by simulating keyboard input"""
        if not text:
            return

        print(f"Sending to chat: {text}")

        # Press Enter to open chat
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
        time.sleep(0.1)

        # Type the text
        self.keyboard.type(text)
        time.sleep(0.1)

        # Press Enter to send
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)

    def run_once(self, duration=5):
        """Record, transcribe, and send to chat once"""
        # Record audio
        audio_data = self.record_audio(duration)
        if audio_data is None:
            print("No audio recorded")
            return

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_file = f.name
            self.save_audio_to_wav(audio_data, temp_file)

        try:
            # Transcribe
            print("Transcribing...")
            text = self.transcribe_audio(temp_file)
            print(f"Transcribed: {text}")

            # Send to chat
            if text:
                self.send_to_wow_chat(text)
        finally:
            # Cleanup
            Path(temp_file).unlink(missing_ok=True)

    def run_continuous(self, duration=5, pause=1):
        """Run continuously, recording and transcribing"""
        print("Starting continuous voice-to-chat service...")
        print(f"Recording {duration}s clips with {pause}s pause between")
        print("Press Ctrl+C to stop")

        try:
            while True:
                self.run_once(duration)
                time.sleep(pause)
        except KeyboardInterrupt:
            print("\nStopping service...")

    def start_recording(self):
        """Start recording audio (for push-to-talk)"""
        with self.recording_lock:
            if self.is_recording:
                return

            print("Recording started...")
            self.is_recording = True
            self.audio_queue = queue.Queue()

            # Start audio stream
            self.recording_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self.audio_callback,
                dtype='int16'
            )
            self.recording_stream.start()

    def stop_recording(self):
        """Stop recording and process audio (for push-to-talk)"""
        with self.recording_lock:
            if not self.is_recording:
                return

            print("Recording stopped...")
            self.is_recording = False

            # Stop audio stream
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
                self.recording_stream = None

            # Collect all audio
            audio_data = []
            while not self.audio_queue.empty():
                audio_data.append(self.audio_queue.get())

            if not audio_data:
                print("No audio recorded")
                return

            audio = np.concatenate(audio_data, axis=0)

            # Save to temp file and transcribe
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
                self.save_audio_to_wav(audio, temp_file)

            try:
                print("Transcribing...")
                text = self.transcribe_audio(temp_file)
                print(f"Transcribed: {text}")

                if text:
                    self.send_to_wow_chat(text)
            finally:
                Path(temp_file).unlink(missing_ok=True)

    def run_push_to_talk_keyboard(self, ptt_key='`'):
        """Run in push-to-talk mode with keyboard key"""
        print(f"Push-to-talk mode: Hold '{ptt_key}' to record, release to transcribe")
        print("Press Ctrl+C to stop")

        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char == ptt_key:
                    self.start_recording()
            except AttributeError:
                pass

        def on_release(key):
            try:
                if hasattr(key, 'char') and key.char == ptt_key:
                    self.stop_recording()
            except AttributeError:
                pass

        with Listener(on_press=on_press, on_release=on_release) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\nStopping service...")

    def run_daemon_mode(self, control_file="wow_voice_control.json"):
        """Run as daemon, controlled by external file (for Decky integration)"""
        control_path = Path(control_file)
        print(f"Daemon mode: Watching {control_file} for commands")
        print("Commands: {\"recording\": true/false}")
        print("Press Ctrl+C to stop")

        last_state = False

        try:
            while True:
                if control_path.exists():
                    try:
                        with open(control_path) as f:
                            control = json.load(f)
                            recording = control.get("recording", False)

                            if recording and not last_state:
                                # Start recording
                                self.start_recording()
                                last_state = True
                            elif not recording and last_state:
                                # Stop recording
                                self.stop_recording()
                                last_state = False
                    except Exception as e:
                        print(f"Error reading control file: {e}")

                time.sleep(0.1)  # Check 10 times per second
        except KeyboardInterrupt:
            print("\nStopping service...")
            if self.is_recording:
                self.stop_recording()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WoW Voice-to-Chat Service")
    parser.add_argument("--context", default="wow_context.json",
                       help="Path to WoW context JSON file")
    parser.add_argument("--mode", choices=["once", "continuous", "push-to-talk", "daemon"],
                       default="once",
                       help="Recording mode (default: once)")
    parser.add_argument("--duration", type=int, default=5,
                       help="Recording duration in seconds for 'once' and 'continuous' modes (default: 5)")
    parser.add_argument("--pause", type=int, default=1,
                       help="Pause between recordings in continuous mode (default: 1)")
    parser.add_argument("--ptt-key", default="`",
                       help="Push-to-talk key for 'push-to-talk' mode (default: `)")
    parser.add_argument("--control-file", default="wow_voice_control.json",
                       help="Control file path for 'daemon' mode (default: wow_voice_control.json)")

    args = parser.parse_args()

    service = WoWVoiceChat(context_file=args.context)

    if args.mode == "once":
        service.run_once(duration=args.duration)
    elif args.mode == "continuous":
        service.run_continuous(duration=args.duration, pause=args.pause)
    elif args.mode == "push-to-talk":
        service.run_push_to_talk_keyboard(ptt_key=args.ptt_key)
    elif args.mode == "daemon":
        service.run_daemon_mode(control_file=args.control_file)
