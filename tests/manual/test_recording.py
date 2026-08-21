import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "src"))


# Mock decky_plugin
class MockDecky:
    DECKY_PLUGIN_DIR = "."


sys.modules["decky_plugin"] = MockDecky()

os.environ["DECKY_PLUGIN_DIR"] = "."

# Now test importing and initializing
from wow_voice_chat import WoWVoiceChat

print("Creating WoWVoiceChat...")
svc = WoWVoiceChat(context_file="wow_context.json")
print("Service created successfully")
print(f"Recording: {svc.is_recording}")
