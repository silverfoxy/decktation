#!/usr/bin/env python3
"""
Quick test to verify xdotool typing works
"""
import subprocess
import time

print("=== Testing xdotool ===")
print()
print("INSTRUCTIONS:")
print("1. Open a text editor (Kate, Firefox, anything)")
print("2. Click inside the text field to focus it")
print("3. Come back here and press Enter")
print()
input("Press Enter when your text editor is open and focused...")

print("\nYou have 10 seconds to switch to the text editor window!")
print("The text will NOT appear in this terminal.")
print()

for i in range(10, 0, -1):
    print(f"Typing in {i} seconds...", end='\r')
    time.sleep(1)

print("\n⌨️  Typing now into the active window...")
subprocess.run(["xdotool", "type", "Hello from xdotool!"], check=False)
time.sleep(1)

print("\n✓ Done!")
print()
print("Did you see 'Hello from xdotool!' appear in your text editor?")
print("(It will NOT appear in this terminal)")
