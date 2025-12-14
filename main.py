import os
import sys
import logging
import traceback
import subprocess
from pathlib import Path

# The decky plugin module is located at decky-loader/plugin
import decky_plugin

logging.basicConfig(
    filename="/tmp/decktation.log",
    format="Decktation: %(asctime)s %(levelname)s %(message)s",
    filemode="w+",
    force=True,
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

plugin_path = os.environ["DECKY_PLUGIN_DIR"]

# Add our service to Python path
sys.path.insert(0, plugin_path)


def install_dependencies():
    """Install Python dependencies if not already installed"""
    try:
        # Check if dependencies are already installed
        import faster_whisper
        import sounddevice
        import numpy
        import pynput
        logger.info("All dependencies already installed")
        return True
    except ImportError:
        logger.info("Dependencies missing, installing...")

        try:
            # Install dependencies
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--target", plugin_path,
                "--upgrade",
                "faster-whisper",
                "sounddevice",
                "numpy",
                "pynput"
            ])
            logger.info("Dependencies installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False


# Import our voice chat service
WoWVoiceChat = None
try:
    from wow_voice_chat import WoWVoiceChat
except ImportError as e:
    logger.error(f"Failed to import WoWVoiceChat: {e}")


class Plugin:
    voice_service = None
    dependencies_installed = False

    async def _main(self):
        """Initialize the plugin"""
        try:
            logger.info("Initializing Decktation plugin")

            # Install dependencies on first run
            if not self.dependencies_installed:
                logger.info("Checking dependencies...")
                self.dependencies_installed = install_dependencies()

                if not self.dependencies_installed:
                    logger.error("Failed to install dependencies")
                    return

                # Re-import after installation
                global WoWVoiceChat
                if WoWVoiceChat is None:
                    from wow_voice_chat import WoWVoiceChat

            # Initialize the voice service
            context_file = f"{plugin_path}/wow_context.json"
            self.voice_service = WoWVoiceChat(context_file=context_file)

            logger.info("Voice service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize: {traceback.format_exc()}")
        return

    async def _unload(self):
        """Cleanup when plugin unloads"""
        logger.info("Unloading Decktation plugin")
        try:
            if self.voice_service and self.voice_service.is_recording:
                self.voice_service.stop_recording()
        except Exception as e:
            logger.error(f"Error during unload: {traceback.format_exc()}")
        return

    async def start_recording(self):
        """Start recording audio"""
        try:
            if self.voice_service is None:
                logger.error("Voice service not initialized")
                return {"success": False, "error": "Service not initialized"}

            logger.info("Starting recording")
            self.voice_service.start_recording()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error starting recording: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def stop_recording(self):
        """Stop recording and transcribe"""
        try:
            if self.voice_service is None:
                logger.error("Voice service not initialized")
                return {"success": False, "error": "Service not initialized"}

            logger.info("Stopping recording")
            self.voice_service.stop_recording()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error stopping recording: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def is_recording(self):
        """Check if currently recording"""
        try:
            if self.voice_service is None:
                return {"recording": False}
            return {"recording": self.voice_service.is_recording}
        except Exception as e:
            logger.error(f"Error checking recording status: {traceback.format_exc()}")
            return {"recording": False}

    async def update_context(self, context: dict):
        """Update WoW context for better transcription"""
        try:
            logger.info(f"Updating context: {context}")
            context_file = f"{plugin_path}/wow_context.json"

            import json
            with open(context_file, 'w') as f:
                json.dump(context, f)

            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating context: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def get_status(self):
        """Get plugin status including dependency installation"""
        try:
            return {
                "success": True,
                "dependencies_installed": self.dependencies_installed,
                "service_ready": self.voice_service is not None,
                "recording": self.voice_service.is_recording if self.voice_service else False
            }
        except Exception as e:
            logger.error(f"Error getting status: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
