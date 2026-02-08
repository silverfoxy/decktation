import sys

sys.path.insert(0, ".")


# Mock decky_plugin
class MockDecky:
    DECKY_PLUGIN_DIR = "."


sys.modules["decky_plugin"] = MockDecky()

import os

os.environ["DECKY_PLUGIN_DIR"] = "."

# Now test importing and initializing
from wow_voice_chat import WoWVoiceChat

print("Creating WoWVoiceChat...")
svc = WoWVoiceChat(context_file="wow_context.json")
print("Service created successfully")
print(f"Recording: {svc.is_recording}")
