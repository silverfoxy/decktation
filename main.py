import os
import sys
import json
import logging
import traceback
import threading
import subprocess
import time
from pathlib import Path

# The decky plugin module is located at decky-loader/plugin
import decky_plugin

# Setup logging first
logging.basicConfig(
    filename="/tmp/decktation.log",
    format="Decktation: %(asctime)s %(levelname)s %(message)s",
    filemode="w+",
    force=True,
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

plugin_path = os.environ["DECKY_PLUGIN_DIR"]

# Add bundled dependencies to Python path
lib_path = os.path.join(plugin_path, "lib")
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)
    logger.info(f"Added lib path: {lib_path}")
else:
    logger.error(f"Lib path does not exist: {lib_path}")

# Add our service to Python path
sys.path.insert(0, plugin_path)

# Debug: Log Python environment
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"sys.path (first 5): {sys.path[:5]}")
logger.info(f"Current working directory: {os.getcwd()}")

# Import our voice chat service
WoWVoiceChat = None
try:
    from wow_voice_chat import WoWVoiceChat
    logger.info("Successfully imported WoWVoiceChat")
except ImportError as e:
    logger.error(f"Failed to import WoWVoiceChat: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# File paths for subprocess communication
STATE_FILE = "/tmp/decktation_l5"
PID_FILE = "/tmp/decktation_listener.pid"
# Config in user home directory for persistence and write access
CONFIG_DIR = os.path.expanduser("~/.config/decktation")
os.makedirs(CONFIG_DIR, exist_ok=True)
BUTTON_CONFIG_FILE = os.path.join(CONFIG_DIR, "button_config.json")
PRESETS_FILE = os.path.join(plugin_path, "game_presets.json")

# Load game presets
_game_presets = {}
try:
    with open(PRESETS_FILE, 'r') as f:
        _game_presets = json.load(f)
    logger.info(f"Loaded {len(_game_presets)} game presets: {list(_game_presets.keys())}")
except Exception as e:
    logger.error(f"Failed to load game presets: {e}")


class Plugin:
    # Class variables (shared state)
    voice_service = None
    listener_process = None
    poll_thread = None
    poll_running = False
    controller_enabled = False
    recording_start_count = 0  # Increments each time recording starts

    @staticmethod
    def check_ydotoold():
        """Check if ydotoold is running"""
        try:
            result = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True, timeout=2)
            if result.returncode == 0:
                logger.info("ydotoold is running")
                return True
            else:
                logger.warning("ydotoold is NOT running - keyboard input will not work")
                return False
        except Exception as e:
            logger.error(f"Failed to check ydotoold: {e}")
            return False

    @staticmethod
    def start_controller_listener():
        """Start the external controller listener process"""
        try:
            # Kill any existing listener
            Plugin.stop_controller_listener()

            listener_script = os.path.join(plugin_path, "controller_listener.py")
            if not os.path.exists(listener_script):
                logger.error(f"Controller listener script not found: {listener_script}")
                return False

            # Start the listener as a subprocess using Decky's Python
            Plugin.listener_process = subprocess.Popen(
                [sys.executable, listener_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            logger.info(f"Started controller listener (PID {Plugin.listener_process.pid})")

            # Give it a moment to start
            time.sleep(0.5)

            # Check if it's still running
            if Plugin.listener_process.poll() is not None:
                output = Plugin.listener_process.stdout.read()
                logger.error(f"Controller listener exited immediately: {output}")
                return False

            return True
        except Exception as e:
            logger.error(f"Failed to start controller listener: {e}")
            return False

    @staticmethod
    def stop_controller_listener():
        """Stop the external controller listener process"""
        try:
            # Kill by PID file
            if os.path.exists(PID_FILE):
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 9)
                    logger.info(f"Killed old listener process {pid}")
                except:
                    pass

            # Kill our subprocess if we have one
            if Plugin.listener_process:
                Plugin.listener_process.kill()
                Plugin.listener_process = None

            # Clean up files
            for f in [STATE_FILE, PID_FILE]:
                if os.path.exists(f):
                    os.remove(f)
        except Exception as e:
            logger.error(f"Error stopping controller listener: {e}")

    @staticmethod
    def poll_button_state():
        """Poll the state file for button presses"""
        logger.info("Button state polling started")
        last_state = False
        last_recording_state = False
        health_check_counter = 0

        while Plugin.poll_running:
            try:
                if not Plugin.controller_enabled:
                    time.sleep(0.1)
                    continue

                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE, 'r') as f:
                        state = f.read().strip() == "1"

                    # Detect state change
                    if state and not last_state:
                        # Button pressed - cancel pending send if one is waiting
                        if Plugin.voice_service and Plugin.voice_service.pending_text:
                            cancelled = Plugin.voice_service.cancel_pending()
                            if cancelled:
                                logger.info("Pending send cancelled by button press")
                        elif Plugin.voice_service and not Plugin.voice_service.is_recording:
                            logger.info("Button combo pressed - starting recording")
                            Plugin.voice_service.start_recording()
                            Plugin.recording_start_count += 1
                    elif not state and last_state:
                        # Button released
                        logger.info("Button combo released - stopping recording")
                        if Plugin.voice_service and Plugin.voice_service.is_recording:
                            Plugin.voice_service.stop_recording()

                    last_state = state

                # Log recording state changes for notification debugging
                current_recording = Plugin.voice_service.is_recording if Plugin.voice_service else False
                if current_recording != last_recording_state:
                    logger.info(f"Recording state changed: {last_recording_state} -> {current_recording}")
                    last_recording_state = current_recording

                # Periodically check if listener process is still alive, restart if dead
                health_check_counter += 1
                if health_check_counter >= 20:  # Every ~1 second (20 * 50ms)
                    health_check_counter = 0
                    if Plugin.listener_process and Plugin.listener_process.poll() is not None:
                        logger.warning("Controller listener died, restarting...")
                        Plugin.start_controller_listener()

                time.sleep(0.05)  # 50ms polling interval
            except Exception as e:
                logger.error(f"Error polling button state: {e}")
                time.sleep(0.1)

        logger.info("Button state polling stopped")

    async def _main(self):
        """Initialize the plugin"""
        try:
            logger.info("Initializing Decktation plugin")

            # Check if ydotoold is running for keyboard simulation
            Plugin.check_ydotoold()

            if WoWVoiceChat is None:
                logger.error("WoWVoiceChat not available - dependencies may be missing")
                return

            # Load active game preset
            active_game = "wow"
            try:
                if os.path.exists(BUTTON_CONFIG_FILE):
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        saved_config = json.load(f)
                    active_game = saved_config.get("game", "wow")
            except Exception as e:
                logger.error(f"Error reading active game from config: {e}")

            active_preset = _game_presets.get(active_game, _game_presets.get("wow", {}))
            logger.info(f"Active game preset: {active_game}")

            confirm_mode = False
            try:
                if os.path.exists(BUTTON_CONFIG_FILE):
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        saved_config = json.load(f)
                    confirm_mode = saved_config.get("confirmMode", False)
            except Exception as e:
                logger.error(f"Error reading confirm mode from config: {e}")

            # Initialize the voice service with lazy model loading
            context_file = f"{plugin_path}/wow_context.json"

            Plugin.voice_service = WoWVoiceChat(
                context_file=context_file,
                lazy_load=True,
                test_mode=False,
                test_audio_file=None,
                preset=active_preset,
                confirm_delay=2.0 if confirm_mode else 0
            )
            logger.info("Voice service initialized (model will load on first use)")

            # Restore enabled state from config
            try:
                if os.path.exists(BUTTON_CONFIG_FILE):
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        saved_config = json.load(f)
                    Plugin.controller_enabled = saved_config.get("enabled", False)
                    if Plugin.controller_enabled:
                        logger.info("Restored enabled state from config")
            except Exception as e:
                logger.error(f"Error restoring enabled state: {e}")

            # Start the external controller listener
            if Plugin.start_controller_listener():
                # Start polling thread
                Plugin.poll_running = True
                Plugin.poll_thread = threading.Thread(target=Plugin.poll_button_state, daemon=True)
                Plugin.poll_thread.start()
                logger.info("Controller input ready (using external listener)")
            else:
                logger.error("Failed to start controller listener")

        except Exception as e:
            logger.error(f"Failed to initialize: {traceback.format_exc()}")
        return

    async def _unload(self):
        """Cleanup when plugin unloads"""
        logger.info("Unloading Decktation plugin")
        try:
            Plugin.poll_running = False
            Plugin.stop_controller_listener()
            if Plugin.voice_service and Plugin.voice_service.is_recording:
                Plugin.voice_service.stop_recording()
        except Exception as e:
            logger.error(f"Error during unload: {traceback.format_exc()}")
        return

    async def set_enabled(self, enabled: bool):
        """Enable or disable controller listening"""
        Plugin.controller_enabled = enabled
        logger.info(f"Controller listening {'enabled' if enabled else 'disabled'}")
        # Persist enabled state to config
        try:
            config = {"buttons": ["L1", "R1"], "showNotifications": True}
            if os.path.exists(BUTTON_CONFIG_FILE):
                with open(BUTTON_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            config["enabled"] = enabled
            with open(BUTTON_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logger.error(f"Error saving enabled state: {e}")
        return {"success": True}

    async def get_button_config(self):
        """Get current button configuration and settings"""
        try:
            if os.path.exists(BUTTON_CONFIG_FILE):
                with open(BUTTON_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Ensure fields exist for backward compatibility
                    if "showNotifications" not in config:
                        config["showNotifications"] = True
                    if "enabled" not in config:
                        config["enabled"] = False
                    if "game" not in config:
                        config["game"] = "wow"
                    if "confirmMode" not in config:
                        config["confirmMode"] = False
                    return {"success": True, "config": config}
            else:
                # Default: L1+R1, notifications enabled, not enabled, wow preset, no confirm
                return {"success": True, "config": {"buttons": ["L1", "R1"], "showNotifications": True, "enabled": False, "game": "wow", "confirmMode": False}}
        except Exception as e:
            logger.error(f"Error getting button config: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_button_config(self, buttons: list, showNotifications: bool = True):
        """Set button configuration and settings, restart listener"""
        try:
            # Validate buttons list
            if not isinstance(buttons, list) or len(buttons) == 0:
                return {"success": False, "error": "buttons must be a non-empty list"}

            # Remove duplicates while preserving order
            seen = set()
            unique_buttons = []
            for btn in buttons:
                if btn not in seen:
                    seen.add(btn)
                    unique_buttons.append(btn)

            # Preserve existing fields (game, enabled) when updating button config
            config = {"buttons": ["L1", "R1"], "showNotifications": True, "enabled": False, "game": "wow"}
            if os.path.exists(BUTTON_CONFIG_FILE):
                try:
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                except Exception:
                    pass

            config["buttons"] = unique_buttons
            config["showNotifications"] = showNotifications

            with open(BUTTON_CONFIG_FILE, 'w') as f:
                json.dump(config, f)

            combo_str = "+".join(unique_buttons)
            logger.info(f"Button config updated: {combo_str}, notifications: {showNotifications}")

            # Always restart controller listener so new config takes effect immediately
            Plugin.stop_controller_listener()
            Plugin.start_controller_listener()

            return {"success": True}
        except Exception as e:
            logger.error(f"Error setting button config: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_confirm_mode(self, enabled: bool):
        """Enable or disable the confirm-before-sending delay"""
        try:
            config = {"buttons": ["L1", "R1"], "showNotifications": True, "enabled": False, "game": "wow", "confirmMode": False}
            if os.path.exists(BUTTON_CONFIG_FILE):
                try:
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                except Exception:
                    pass
            config["confirmMode"] = enabled
            with open(BUTTON_CONFIG_FILE, 'w') as f:
                json.dump(config, f)

            if Plugin.voice_service:
                Plugin.voice_service.confirm_delay = 2.0 if enabled else 0

            logger.info(f"Confirm mode {'enabled' if enabled else 'disabled'}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error setting confirm mode: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def get_presets(self):
        """Get all available game presets"""
        try:
            presets = [{"id": k, "name": v["name"]} for k, v in _game_presets.items()]
            return {"success": True, "presets": presets}
        except Exception as e:
            logger.error(f"Error getting presets: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def get_active_preset(self):
        """Get the currently active game preset id"""
        try:
            game = "wow"
            if os.path.exists(BUTTON_CONFIG_FILE):
                with open(BUTTON_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                game = config.get("game", "wow")
            return {"success": True, "game": game}
        except Exception as e:
            logger.error(f"Error getting active preset: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_active_preset(self, game: str):
        """Switch to a different game preset"""
        try:
            if game not in _game_presets:
                return {"success": False, "error": f"Unknown preset: {game}"}

            # Save to config
            config = {"buttons": ["L1", "R1"], "showNotifications": True, "enabled": False, "game": "wow"}
            if os.path.exists(BUTTON_CONFIG_FILE):
                try:
                    with open(BUTTON_CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                except Exception:
                    pass
            config["game"] = game
            with open(BUTTON_CONFIG_FILE, 'w') as f:
                json.dump(config, f)

            # Update running voice service
            if Plugin.voice_service:
                Plugin.voice_service.set_preset(_game_presets[game])

            logger.info(f"Switched game preset to: {game}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error setting active preset: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def start_recording(self):
        """Start recording audio"""
        try:
            if Plugin.voice_service is None:
                logger.error("Voice service not initialized")
                return {"success": False, "error": "Service not initialized"}

            logger.info("Starting recording")
            Plugin.voice_service.start_recording()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error starting recording: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def stop_recording(self):
        """Stop recording and transcribe"""
        try:
            if Plugin.voice_service is None:
                logger.error("Voice service not initialized")
                return {"success": False, "error": "Service not initialized"}

            logger.info("Stopping recording")
            Plugin.voice_service.stop_recording()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error stopping recording: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def is_recording(self):
        """Check if currently recording"""
        try:
            if Plugin.voice_service is None:
                return {"recording": False}
            return {"recording": Plugin.voice_service.is_recording}
        except Exception as e:
            logger.error(f"Error checking recording status: {traceback.format_exc()}")
            return {"recording": False}

    async def update_context(self, context: dict):
        """Update WoW context for better transcription"""
        try:
            logger.info(f"Updating context: {context}")
            context_file = f"{plugin_path}/wow_context.json"

            with open(context_file, 'w') as f:
                json.dump(context, f)

            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating context: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def get_status(self):
        """Get plugin status"""
        try:
            model_ready = False
            model_loading = False
            if Plugin.voice_service:
                model_ready = Plugin.voice_service.is_model_ready()
                model_loading = Plugin.voice_service.model_loading

            return {
                "success": True,
                "service_ready": Plugin.voice_service is not None,
                "model_ready": model_ready,
                "model_loading": model_loading,
                "recording": Plugin.voice_service.is_recording if Plugin.voice_service else False,
                "recording_start_count": Plugin.recording_start_count,
                "pending_text": Plugin.voice_service.pending_text or "" if Plugin.voice_service else "",
                "pending_delay": Plugin.voice_service._confirm_delay_for(Plugin.voice_service.pending_text) if Plugin.voice_service and Plugin.voice_service.pending_text else 0,
                "confirm_mode": Plugin.voice_service.confirm_delay > 0 if Plugin.voice_service else False,
            }
        except Exception as e:
            logger.error(f"Error getting status: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def load_model(self):
        """Explicitly load the Whisper model (called when user enables dictation)"""
        try:
            if Plugin.voice_service is None:
                return {"success": False, "error": "Service not initialized"}

            logger.info("Loading Whisper model...")
            success = Plugin.voice_service._load_model()
            if success:
                logger.info("Model loaded successfully")
            else:
                logger.error(f"Model load failed: {Plugin.voice_service.model_load_error}")

            return {"success": success, "error": Plugin.voice_service.model_load_error}
        except Exception as e:
            logger.error(f"Error loading model: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def get_last_transcription(self):
        """Get the last transcription result for UI display"""
        try:
            if Plugin.voice_service is None:
                return {"success": False, "error": "Service not initialized"}

            result = Plugin.voice_service.get_last_transcription()
            return {"success": True, "transcription": result}
        except Exception as e:
            logger.error(f"Error getting last transcription: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
