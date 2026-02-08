#!/usr/bin/env python3
"""
WoW Voice-to-Chat Service for Steam Deck
Captures voice input, transcribes with faster-whisper, and sends to WoW chat
"""

import os
import json
import time
import queue
import threading
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import wave
import tempfile


class WoWVoiceChat:
    def __init__(self, context_file="wow_context.json", sample_rate=44100, default_channel="say", lazy_load=False, test_mode=False, test_audio_file=None):
        self.context_file = Path(context_file)
        self.sample_rate = sample_rate  # Recording sample rate
        self.whisper_sample_rate = 16000  # Whisper expects 16kHz
        self.default_channel = default_channel

        # Test mode: use static audio file instead of recording
        self.test_mode = test_mode
        self.test_audio_file = test_audio_file

        # Lazy model loading - only load when needed
        self.model = None
        self.model_loading = False
        self.model_load_error = None

        # Last transcription result (for UI display)
        self.last_transcription = None
        self.last_transcription_time = None

        if not lazy_load:
            self._load_model()

        # Audio recording
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_stream = None
        self.recording_lock = threading.Lock()

        # Context cache
        self.context = {}

        # Chat channel mappings
        self.channel_commands = {
            "say": "/s ",
            "party": "/p ",
            "raid": "/raid ",
            "guild": "/g ",
            "officer": "/o ",
            "yell": "/y ",
            "instance": "/i ",
            "whisper": "/w ",
        }

    def _load_model(self):
        """Load the Whisper model (can be called lazily)"""
        if self.model is not None:
            return True
        if self.model_loading:
            return False

        self.model_loading = True
        try:
            print("Loading Whisper model...")
            self.model = WhisperModel("base", device="cpu", compute_type="int8")
            print("Model loaded!")
            self.model_load_error = None
            return True
        except Exception as e:
            print(f"Failed to load model: {e}")
            self.model_load_error = str(e)
            return False
        finally:
            self.model_loading = False

    def is_model_ready(self):
        """Check if model is loaded and ready"""
        return self.model is not None

    def get_last_transcription(self):
        """Get the last transcription result"""
        return {
            "text": self.last_transcription or "",
            "timestamp": self.last_transcription_time or 0
        }

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
        # Use a comprehensive initial prompt with WoW vocabulary
        # This is more effective than hotwords for domain-specific terms
        base_prompt = (
            "World of Warcraft gameplay discussion. "
            "Playing as orc warrior, tauren druid, blood elf paladin, undead warlock, troll shaman, or night elf hunter. "
            "Discussing enhancement shaman, restoration druid, protection warrior, holy paladin, arcane mage, shadow priest, affliction warlock. "
            "Running mythic dungeons, heroic raids, doing quests in Azeroth, Orgrimmar, Stormwind, Ironforge. "
            "Fighting bosses like Lich King, Ragnaros, Illidan, pulling trash mobs, need tank healer and DPS. "
            "Using abilities, cooldowns, buffs, debuffs, interrupts, dispels, cleave and AOE damage."
        )

        zone = self.context.get("zone", "")
        subzone = self.context.get("subzone", "")
        boss = self.context.get("boss", "")
        target = self.context.get("target", "")
        party = self.context.get("party", [])

        # Add dynamic context to the prompt
        dynamic_parts = []
        if zone:
            dynamic_parts.append(f"Currently in {zone}")
        if subzone:
            dynamic_parts.append(f"at {subzone}")
        if boss:
            dynamic_parts.append(f"fighting {boss}")
        if party:
            dynamic_parts.append(f"with party members {', '.join(party[:5])}")

        if dynamic_parts:
            initial_prompt = base_prompt + " " + " ".join(dynamic_parts) + "."
        else:
            initial_prompt = base_prompt

        # Keep hotwords simple - just the most relevant current context
        hotwords = []
        if zone:
            hotwords.append(zone)
        if boss:
            hotwords.append(boss)
        if target:
            hotwords.append(target)
        hotwords_str = ", ".join(hotwords) if hotwords else None

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
        """Save audio data to WAV file, resampling to 16kHz for Whisper"""
        # Flatten audio data if needed (may be 2D from callback)
        audio_data = audio_data.flatten()

        # Resample from recording rate to Whisper rate (16kHz)
        if self.sample_rate != self.whisper_sample_rate:
            # Simple linear interpolation resampling
            duration = len(audio_data) / self.sample_rate
            new_length = int(duration * self.whisper_sample_rate)
            indices = np.linspace(0, len(audio_data) - 1, new_length)
            audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data.astype(np.float32)).astype(np.int16)

        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.whisper_sample_rate)
            wf.writeframes(audio_data.tobytes())

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using faster-whisper"""
        # Ensure model is loaded
        if not self._load_model():
            print("Model not ready, cannot transcribe")
            return ""

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

    def parse_channel_and_text(self, text):
        """
        Parse channel prefix from text
        Supports formats like:
        - "party let's go" -> (party, "let's go")
        - "party: pull boss" -> (party, "pull boss")
        - "Party, I need mana" -> (party, "I need mana")
        - "hello world" -> (default_channel, "hello world")
        """
        text = text.strip()

        # Check for channel prefix at start (case-insensitive)
        for channel_name in self.channel_commands.keys():
            # Match various separators: "party:", "party,", "party ", "party."
            prefixes = [
                f"{channel_name}:",
                f"{channel_name},",
                f"{channel_name}.",
                f"{channel_name} ",
            ]

            for prefix in prefixes:
                if text.lower().startswith(prefix):
                    # Extract the message after the prefix
                    message = text[len(prefix):].strip()
                    return channel_name, message

        # No channel prefix found, use default
        return self.default_channel, text

    def auto_detect_channel(self):
        """Auto-detect best channel based on context"""
        # If in raid, default to raid chat
        if self.context.get("party") and len(self.context.get("party", [])) > 5:
            return "raid"
        # If in party, default to party chat
        elif self.context.get("party") and len(self.context.get("party", [])) > 1:
            return "party"
        # Otherwise use say
        else:
            return "say"

    def send_to_wow_chat(self, text, channel=None):
        """
        Send text to WoW chat by simulating keyboard input using xdotool

        Args:
            text: The text to send
            channel: Optional channel override (say, party, raid, guild, etc.)
                    If None, will parse from text or use default
        """
        if not text:
            return

        # Parse channel from text if not explicitly provided
        if channel is None:
            channel, text = self.parse_channel_and_text(text)

        # Get the channel command
        channel_cmd = self.channel_commands.get(channel, "/s ")

        # Build full message
        full_message = f"{channel_cmd}{text}"

        import logging
        logger = logging.getLogger()
        logger.info(f"Sending to {channel}: {text}")
        logger.info(f"Full message: {full_message}")

        # Use full path to ydotool since plugin environment may not have nix in PATH
        ydotool = "/home/deck/.nix-profile/bin/ydotool"

        # Set socket path - ydotoold running as root uses /tmp/.ydotool_socket
        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = "/tmp/.ydotool_socket"

        try:
            # Press Enter to open chat (keycode 28 = Enter)
            result = subprocess.run([ydotool, "key", "28:1", "28:0"], capture_output=True, text=True, env=env)
            if result.returncode != 0:
                logger.error(f"ydotool key failed: {result.stderr}")
            time.sleep(0.1)

            # Type the full message with channel command
            result = subprocess.run([ydotool, "type", "--", full_message], capture_output=True, text=True, env=env)
            if result.returncode != 0:
                logger.error(f"ydotool type failed: {result.stderr}")
            time.sleep(0.1)

            # Press Enter to send
            result = subprocess.run([ydotool, "key", "28:1", "28:0"], capture_output=True, text=True, env=env)
            if result.returncode != 0:
                logger.error(f"ydotool key failed: {result.stderr}")
        except Exception as e:
            logger.error(f"ydotool error: {e}")

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

            self.is_recording = True

            # TEST MODE: Skip actual recording
            if self.test_mode:
                print(f"[TEST MODE] Recording started (will use {self.test_audio_file})")
                return

            print("Recording started...")
            self.audio_queue = queue.Queue()

            # Get default sample rate from device
            device_info = sd.query_devices(sd.default.device[0], 'input')
            self.sample_rate = int(device_info['default_samplerate'])
            print(f"Using sample rate: {self.sample_rate}")

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

            self.is_recording = False

            # TEST MODE: Use static audio file instead of recorded audio
            if self.test_mode:
                print(f"[TEST MODE] Recording stopped, using {self.test_audio_file}")
                if self.test_audio_file and Path(self.test_audio_file).exists():
                    try:
                        print("[TEST MODE] Transcribing...")
                        text = self.transcribe_audio(self.test_audio_file)
                        print(f"[TEST MODE] Transcribed: {text}")
                        if text:
                            self.send_to_wow_chat(text)
                    except Exception as e:
                        print(f"[TEST MODE] Error: {e}")
                else:
                    print(f"[TEST MODE] Test audio file not found: {self.test_audio_file}")
                return

            print("Recording stopped...")

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

                # Store last transcription result
                self.last_transcription = text
                self.last_transcription_time = time.time()

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
    parser.add_argument("--channel", choices=["say", "party", "raid", "guild", "officer", "yell", "instance", "auto"],
                       default="say",
                       help="Default chat channel (default: say). Use 'auto' to detect from context or voice prefix")
    parser.add_argument("--duration", type=int, default=5,
                       help="Recording duration in seconds for 'once' and 'continuous' modes (default: 5)")
    parser.add_argument("--pause", type=int, default=1,
                       help="Pause between recordings in continuous mode (default: 1)")
    parser.add_argument("--ptt-key", default="`",
                       help="Push-to-talk key for 'push-to-talk' mode (default: `)")
    parser.add_argument("--control-file", default="wow_voice_control.json",
                       help="Control file path for 'daemon' mode (default: wow_voice_control.json)")

    args = parser.parse_args()

    # Handle auto-detection
    default_channel = args.channel
    if default_channel == "auto":
        # Will auto-detect per-message based on context
        default_channel = "say"  # Fallback

    service = WoWVoiceChat(context_file=args.context, default_channel=default_channel)

    if args.mode == "once":
        service.run_once(duration=args.duration)
    elif args.mode == "continuous":
        service.run_continuous(duration=args.duration, pause=args.pause)
    elif args.mode == "push-to-talk":
        service.run_push_to_talk_keyboard(ptt_key=args.ptt_key)
    elif args.mode == "daemon":
        service.run_daemon_mode(control_file=args.control_file)
