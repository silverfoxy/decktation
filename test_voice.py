#!/usr/bin/env python3
"""
Simple test script for voice-to-text functionality
"""
import sys
import os

# Add venv to path
plugin_path = os.path.dirname(os.path.abspath(__file__))
python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
venv_site_packages = os.path.join(plugin_path, "venv", "lib", python_version, "site-packages")
sys.path.insert(0, venv_site_packages)
sys.path.insert(0, plugin_path)

from wow_voice_chat import WoWVoiceChat
import time

def test_basic():
    """Test basic recording and transcription"""
    print("=== Testing Voice-to-Text ===")
    print("This will:")
    print("1. Record audio for 5 seconds")
    print("2. Transcribe it using Whisper")
    print("3. Type the result using xdotool")
    print()
    print("NOTE: Open a text editor first (like gedit or Kate)")
    print("      The transcribed text will be typed there.")
    print()
    input("Press Enter when ready to start recording...")

    # Initialize service
    print("\nInitializing... (this may take 30-60 seconds on first run)")
    service = WoWVoiceChat()

    print("\n🎤 Recording for 5 seconds... SPEAK NOW!")
    service.run_once(duration=5)

    print("\n✓ Test complete!")

def test_push_to_talk():
    """Test push-to-talk mode with manual control"""
    print("=== Testing Push-to-Talk Mode ===")
    print("This simulates the Decky plugin behavior.")
    print()
    print("NOTE: Open a text editor first")
    print()
    input("Press Enter to continue...")

    # Initialize service
    print("\nInitializing...")
    service = WoWVoiceChat()

    print("\n✓ Ready!")
    print("\nCommands:")
    print("  1 - Start recording")
    print("  2 - Stop recording (and transcribe)")
    print("  q - Quit")
    print()

    while True:
        cmd = input("Command: ").strip()

        if cmd == "1":
            print("🎤 Recording... speak now!")
            service.start_recording()
        elif cmd == "2":
            print("⏸️  Stopping and transcribing...")
            service.stop_recording()
            print("✓ Done")
        elif cmd == "q":
            if service.is_recording:
                service.stop_recording()
            print("Goodbye!")
            break
        else:
            print("Invalid command")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Basic test (record 5 seconds)")
    print("2. Push-to-talk mode (manual control)")
    print()

    choice = input("Choice (1 or 2): ").strip()

    if choice == "1":
        test_basic()
    elif choice == "2":
        test_push_to_talk()
    else:
        print("Invalid choice")
