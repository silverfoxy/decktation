import os
import sys
import json
import logging
import asyncio
import traceback
import threading
import subprocess
import time
import shutil
from pathlib import Path

# Decky API v1 uses ``decky``. Keep the old module name as a compatibility
# fallback for stable loader versions that predate the rename.
try:
    import decky
except ImportError:  # pragma: no cover - depends on the installed Decky version
    import decky_plugin as decky

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
dependency_paths = [
    os.path.join(plugin_path, "lib"),  # Legacy GitHub release layout
    # Insert the marketplace runtime last so it takes precedence over stale
    # legacy packages when an existing installation is replaced in place.
    os.path.join(plugin_path, "bin", "python"),
]
for dependency_path in dependency_paths:
    if os.path.exists(dependency_path):
        sys.path.insert(0, dependency_path)
        logger.info(f"Added dependency path: {dependency_path}")

# sounddevice normally searches only system library paths on Linux. Store
# builds bundle PortAudio in bin/lib so the plugin works on clean SteamOS
# installations without modifying the read-only operating system.
bundled_portaudio = os.path.join(plugin_path, "bin", "lib", "libportaudio.so.2")
if os.path.isfile(bundled_portaudio):
    import ctypes.util

    system_find_library = ctypes.util.find_library

    def find_bundled_library(name):
        if name == "portaudio":
            return bundled_portaudio
        return system_find_library(name)

    ctypes.util.find_library = find_bundled_library
    logger.info(f"Using bundled PortAudio: {bundled_portaudio}")

# Add our service to Python path
sys.path.insert(0, plugin_path)

# Import diagnostics support without connecting to Sentry. Collection is
# opt-in and is initialized only after the persisted user preference is read.
telemetry = False
telemetry_available = False
plugin_version = "unknown"
try:
    from telemetry import (
        breadcrumb as telemetry_breadcrumb,
        capture_error as telemetry_capture_error,
        flush as telemetry_flush,
        finish_dictation_trace as telemetry_finish_dictation,
        initialize as initialize_telemetry,
        set_enabled as telemetry_set_enabled,
        start_dictation_trace as telemetry_start_dictation,
    )

    with open(os.path.join(plugin_path, "plugin.json"), "r") as version_file:
        plugin_version = json.load(version_file).get("version", "unknown")
    telemetry_available = True
except Exception as e:
    logger.error(f"Failed to import diagnostics: {e}")

# Read consent before importing optional voice dependencies so startup import
# failures can be captured for users who have opted in.
decky_user_home = getattr(decky, "DECKY_USER_HOME", "/home/deck")
CONFIG_DIR = getattr(
    decky,
    "DECKY_SETTINGS_DIR",
    os.path.join(decky_user_home, "homebrew", "settings", "decktation"),
)
os.makedirs(CONFIG_DIR, exist_ok=True)
BUTTON_CONFIG_FILE = os.path.join(CONFIG_DIR, "button_config.json")

if telemetry_available:
    try:
        if os.path.exists(BUTTON_CONFIG_FILE):
            with open(BUTTON_CONFIG_FILE, "r") as diagnostics_config_file:
                diagnostics_config = json.load(diagnostics_config_file)
            telemetry = bool(diagnostics_config.get("shareDiagnostics", False))
        if telemetry:
            initialize_telemetry(plugin_version)
            telemetry_breadcrumb("plugin.initializing")
    except Exception as e:
        telemetry = False
        logger.error(f"Failed to initialize diagnostics: {e}")

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
    if telemetry:
        telemetry_capture_error("voice_service.import_failed", e)

# File paths for subprocess communication
STATE_FILE = "/tmp/decktation_l5"
PREVIEW_FILE = "/tmp/decktation_button_preview"
PID_FILE = "/tmp/decktation_listener.pid"
CONTROLLER_TYPE_FILE = "/tmp/decktation_controller_type"
# Decktation owns this socket and never modifies a system ydotool service.
YDOTOOL_SOCKET = "/tmp/decktation-ydotool.sock"

PRESETS_FILE = os.path.join(plugin_path, "game_presets.json")
if not os.path.exists(PRESETS_FILE):
    # Decky's builder installs the contents of defaults/ at the plugin root.
    # Keep source-tree execution useful for tests and local development.
    PRESETS_FILE = os.path.join(plugin_path, "defaults", "game_presets.json")

DEFAULT_BUTTON_CONFIG = {
    "buttons": ["L1", "R1"],
    "showNotifications": True,
    "enabled": False,
    "game": "wow",
    "confirmMode": False,
    "manualSend": False,
    "shareDiagnostics": False,
    "modelSize": "base",
    "transcriptionLanguage": "auto",
}

SUPPORTED_WHISPER_MODEL_SIZES = {"base", "small", "medium"}

SUPPORTED_WHISPER_LANGUAGES = {
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br",
    "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu",
    "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr",
    "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km",
    "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk",
    "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc",
    "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl",
    "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th",
    "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue",
    "zh",
}


def _normalize_transcription_language(language):
    language = (language or "auto").strip().lower()
    if language in ("", "auto"):
        return "auto"
    if language not in SUPPORTED_WHISPER_LANGUAGES:
        raise ValueError(f"Unsupported transcription language: {language}")
    return language


def _normalize_model_size(model_size):
    model_size = (model_size or "base").strip().lower()
    if model_size not in SUPPORTED_WHISPER_MODEL_SIZES:
        raise ValueError(f"Unsupported model size: {model_size}")
    return model_size


def _read_button_config():
    config = dict(DEFAULT_BUTTON_CONFIG)
    if os.path.exists(BUTTON_CONFIG_FILE):
        with open(BUTTON_CONFIG_FILE, "r") as config_file:
            saved_config = json.load(config_file)
        if isinstance(saved_config, dict):
            config.update(saved_config)

    config["transcriptionLanguage"] = _normalize_transcription_language(
        config.get("transcriptionLanguage")
    )
    config["modelSize"] = _normalize_model_size(config.get("modelSize"))
    config["translateToEnglish"] = False
    return config


def _write_button_config(config):
    normalized_config = dict(DEFAULT_BUTTON_CONFIG)
    normalized_config.update(config)
    normalized_config["transcriptionLanguage"] = _normalize_transcription_language(
        normalized_config.get("transcriptionLanguage")
    )
    normalized_config["modelSize"] = _normalize_model_size(
        normalized_config.get("modelSize")
    )
    normalized_config["translateToEnglish"] = False
    with open(BUTTON_CONFIG_FILE, "w") as config_file:
        json.dump(normalized_config, config_file)
    return normalized_config

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
    ydotoold_process = None
    ydotoold_ready = False
    poll_thread = None
    poll_running = False
    controller_enabled = False
    recording_start_count = 0  # Increments each time recording starts
    active_preset = "wow"
    dictation_transaction = None

    @staticmethod
    def _controller_type():
        try:
            with open(CONTROLLER_TYPE_FILE, "r") as controller_file:
                return controller_file.read().strip() or "unknown"
        except OSError:
            return "unknown"

    @staticmethod
    def _start_dictation_trace():
        if telemetry:
            Plugin.dictation_transaction = telemetry_start_dictation(
                Plugin.active_preset,
                Plugin._controller_type(),
            )

    @staticmethod
    def _finish_dictation_trace(success):
        if telemetry_available:
            telemetry_finish_dictation(Plugin.dictation_transaction, success)
        Plugin.dictation_transaction = None

    @staticmethod
    def start_ydotoold():
        """Start Decktation's private virtual-keyboard daemon."""
        Plugin.ydotoold_ready = False
        ydotoold = os.path.join(plugin_path, "bin", "ydotoold")
        if not os.path.isfile(ydotoold):
            logger.error(f"Bundled ydotoold not found: {ydotoold}")
            return False

        Plugin.stop_ydotoold()
        try:
            Plugin.ydotoold_process = subprocess.Popen(
                [
                    ydotoold,
                    "--socket-path", YDOTOOL_SOCKET,
                    "--socket-perm", "0600",
                    "--mouse-off",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            threading.Thread(
                target=Plugin._log_process_output,
                args=(Plugin.ydotoold_process,),
                daemon=True,
            ).start()

            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if Plugin.ydotoold_process.poll() is not None:
                    logger.error(
                        "ydotoold exited with code "
                        f"{Plugin.ydotoold_process.returncode}"
                    )
                    Plugin.ydotoold_process = None
                    return False
                if os.path.exists(YDOTOOL_SOCKET):
                    logger.info(f"ydotoold ready on {YDOTOOL_SOCKET}")
                    Plugin.ydotoold_ready = True
                    return True
                time.sleep(0.05)
            logger.error("Timed out waiting for ydotoold socket")
        except Exception:
            logger.error(f"Failed to start ydotoold: {traceback.format_exc()}")

        Plugin.stop_ydotoold()
        return False

    @staticmethod
    def stop_ydotoold():
        """Stop only the ydotoold process started by this plugin."""
        Plugin.ydotoold_ready = False
        process = Plugin.ydotoold_process
        Plugin.ydotoold_process = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        try:
            if os.path.exists(YDOTOOL_SOCKET):
                os.remove(YDOTOOL_SOCKET)
        except OSError as error:
            logger.warning(f"Could not remove ydotool socket: {error}")

    @staticmethod
    def _log_process_output(process):
        """Continuously forward child-process output into the plugin log."""
        try:
            for line in process.stdout:
                message = line.rstrip()
                logger.info(f"Child process: {message}")
                if telemetry:
                    if "raw HID interface not found" in message:
                        telemetry_capture_error(
                            "controller.device_not_found",
                            controller_type=Plugin._controller_type(),
                        )
                    elif "Raw HID disconnected:" in message:
                        telemetry_capture_error(
                            "controller.hid_disconnected",
                            controller_type=Plugin._controller_type(),
                        )
        except Exception as e:
            logger.warning(f"Stopped reading child-process output: {e}")

    @staticmethod
    def start_controller_listener():
        """Start the external controller listener process"""
        try:
            # Kill any existing listener
            Plugin.stop_controller_listener()

            listener_script = os.path.join(plugin_path, "bin", "controller_listener.py")
            if not os.path.exists(listener_script):
                logger.error(f"Controller listener script not found: {listener_script}")
                return False

            # Start the listener as a subprocess using system Python
            # Note: sys.executable is the PyInstaller frozen Decky binary, not a Python interpreter
            python_bin = "/usr/bin/python3"
            if not os.path.exists(python_bin):
                # Fallback to finding python3 in PATH
                import shutil
                python_bin = shutil.which("python3")
                if not python_bin:
                    logger.error("No python3 found in system")
                    return False

            Plugin.listener_process = subprocess.Popen(
                [python_bin, listener_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={
                    **os.environ,
                    "DECKTATION_CONFIG_DIR": CONFIG_DIR,
                },
            )
            logger.info(f"Started controller listener (PID {Plugin.listener_process.pid})")

            threading.Thread(
                target=Plugin._log_process_output,
                args=(Plugin.listener_process,),
                daemon=True,
            ).start()

            # Give it a moment to start
            time.sleep(0.5)

            # Check if it's still running
            if Plugin.listener_process.poll() is not None:
                logger.error(
                    f"Controller listener exited immediately with code "
                    f"{Plugin.listener_process.returncode}"
                )
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
            for f in [STATE_FILE, PREVIEW_FILE, PID_FILE, CONTROLLER_TYPE_FILE]:
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
                            Plugin._start_dictation_trace()
                            try:
                                Plugin.voice_service.start_recording()
                                Plugin.recording_start_count += 1
                            except Exception as e:
                                Plugin._finish_dictation_trace(False)
                                if telemetry:
                                    telemetry_capture_error(
                                        "recording.start_failed",
                                        e,
                                        preset=Plugin.active_preset,
                                        controller_type=Plugin._controller_type(),
                                    )
                                raise
                    elif not state and last_state:
                        # Button released
                        logger.info("Button combo released - stopping recording")
                        if Plugin.voice_service and Plugin.voice_service.is_recording:
                            try:
                                Plugin.voice_service.stop_recording()
                            except Exception as e:
                                Plugin._finish_dictation_trace(False)
                                if telemetry:
                                    telemetry_capture_error(
                                        "recording.stop_failed",
                                        e,
                                        preset=Plugin.active_preset,
                                        controller_type=Plugin._controller_type(),
                                    )
                                raise
                            else:
                                Plugin._finish_dictation_trace(True)

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
                        if telemetry:
                            telemetry_capture_error(
                                "controller.listener_crashed",
                                controller_type=Plugin._controller_type(),
                            )
                        if not Plugin.start_controller_listener() and telemetry:
                            telemetry_capture_error(
                                "controller.listener_restart_failed",
                                controller_type=Plugin._controller_type(),
                            )

                time.sleep(0.05)  # 50ms polling interval
            except Exception as e:
                logger.error(f"Error polling button state: {e}")
                time.sleep(0.1)

        logger.info("Button state polling stopped")

    async def _main(self):
        """Initialize the plugin"""
        try:
            logger.info("Initializing Decktation plugin")

            # Start the bundled daemon; store installs require no terminal setup.
            Plugin.start_ydotoold()

            if WoWVoiceChat is None:
                logger.error("WoWVoiceChat not available - dependencies may be missing")
                return

            # Load persisted settings
            saved_config = dict(DEFAULT_BUTTON_CONFIG)
            try:
                saved_config = _read_button_config()
            except Exception as e:
                logger.error(f"Error reading settings from config: {e}")

            active_game = saved_config.get("game", "wow")
            active_preset = _game_presets.get(active_game, _game_presets.get("wow", {}))
            Plugin.active_preset = active_game
            logger.info(f"Active game preset: {active_game}")

            confirm_mode = saved_config.get("confirmMode", False)
            manual_send = saved_config.get("manualSend", False)
            model_size = saved_config.get("modelSize", "base")
            transcription_language = saved_config.get("transcriptionLanguage", "auto")

            # Initialize the voice service with lazy model loading
            context_file = f"{plugin_path}/wow_context.json"

            Plugin.voice_service = WoWVoiceChat(
                context_file=context_file,
                lazy_load=True,
                test_mode=False,
                test_audio_file=None,
                preset=active_preset,
                confirm_delay=2.0 if confirm_mode else 0,
                manual_send=manual_send,
                model_size=model_size,
                transcription_language=(
                    None if transcription_language == "auto" else transcription_language
                ),
                diagnostic_reporter=lambda name, error=None: (
                    telemetry_capture_error(
                        name,
                        error,
                        preset=Plugin.active_preset,
                        controller_type=Plugin._controller_type(),
                    )
                    if telemetry else None
                ),
            )
            logger.info("Voice service initialized (model will load on first use)")
            if telemetry:
                telemetry_breadcrumb("voice_service.initialized")

            # Restore enabled state from config
            try:
                if os.path.exists(BUTTON_CONFIG_FILE):
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
                if telemetry:
                    telemetry_breadcrumb("controller.listener_started")
            else:
                logger.error("Failed to start controller listener")
                if telemetry:
                    telemetry_capture_error("controller.listener_start_failed")

        except Exception as e:
            logger.error(f"Failed to initialize: {traceback.format_exc()}")
            if telemetry:
                telemetry_capture_error("plugin.initialization_failed", e)
        return

    async def _unload(self):
        """Cleanup when plugin unloads"""
        logger.info("Unloading Decktation plugin")
        try:
            Plugin.poll_running = False
            Plugin.stop_controller_listener()
            Plugin.stop_ydotoold()
            if Plugin.voice_service and Plugin.voice_service.is_recording:
                Plugin.voice_service.stop_recording()
                Plugin._finish_dictation_trace(False)
        except Exception as e:
            logger.error(f"Error during unload: {traceback.format_exc()}")
            if telemetry:
                telemetry_capture_error("plugin.unload_failed", e)
        if telemetry:
            telemetry_flush()
        return

    async def _uninstall(self):
        """Remove runtime processes and transient files on uninstall."""
        Plugin.poll_running = False
        Plugin.stop_controller_listener()
        Plugin.stop_ydotoold()

    async def _migration(self):
        """Move settings created by pre-store releases into Decky's settings."""
        legacy_dir = os.path.join(decky_user_home, ".config", "decktation")
        legacy_config = os.path.join(legacy_dir, "button_config.json")
        if not os.path.exists(BUTTON_CONFIG_FILE) and os.path.isfile(legacy_config):
            try:
                shutil.copy2(legacy_config, BUTTON_CONFIG_FILE)
                logger.info(f"Migrated settings from {legacy_config}")
            except OSError as error:
                logger.warning(f"Could not migrate settings: {error}")

    async def set_enabled(self, enabled: bool):
        """Enable or disable controller listening"""
        Plugin.controller_enabled = enabled
        logger.info(f"Controller listening {'enabled' if enabled else 'disabled'}")
        # Persist enabled state to config
        try:
            config = _read_button_config()
            config["enabled"] = enabled
            _write_button_config(config)
        except Exception as e:
            logger.error(f"Error saving enabled state: {e}")
        return {"success": True}

    async def get_button_config(self):
        """Get current button configuration and settings"""
        try:
            return {"success": True, "config": _read_button_config()}
        except Exception as e:
            logger.error(f"Error getting button config: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_share_diagnostics(self, enabled: bool):
        """Persist and immediately apply anonymous diagnostics consent."""
        global telemetry
        try:
            config = _read_button_config()
            config["shareDiagnostics"] = bool(enabled)
            _write_button_config(config)

            telemetry = bool(enabled) and telemetry_available
            if telemetry_available:
                telemetry_set_enabled(telemetry, plugin_version)
            logger.info(
                f"Anonymous diagnostics {'enabled' if telemetry else 'disabled'}"
            )
            return {"success": True, "enabled": telemetry}
        except Exception as e:
            telemetry = False
            logger.error(f"Error saving diagnostics preference: {e}")
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

            config = _read_button_config()

            config["buttons"] = unique_buttons
            config["showNotifications"] = showNotifications

            _write_button_config(config)

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
            config = _read_button_config()
            config["confirmMode"] = enabled
            _write_button_config(config)

            if Plugin.voice_service:
                Plugin.voice_service.confirm_delay = 2.0 if enabled else 0

            logger.info(f"Confirm mode {'enabled' if enabled else 'disabled'}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error setting confirm mode: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_manual_send(self, enabled: bool):
        """Enable or disable manual send mode (skip final Enter press)"""
        try:
            config = _read_button_config()
            config["manualSend"] = enabled
            _write_button_config(config)

            if Plugin.voice_service:
                Plugin.voice_service.manual_send = enabled

            logger.info(f"Manual send mode {'enabled' if enabled else 'disabled'}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error setting manual send mode: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_transcription_options(self, language: str = "auto", translateToEnglish: bool = False):
        """Set Faster Whisper language selection."""
        try:
            language = _normalize_transcription_language(language)
            config = _read_button_config()
            config["transcriptionLanguage"] = language
            config["translateToEnglish"] = False
            _write_button_config(config)

            if Plugin.voice_service:
                Plugin.voice_service.set_transcription_options(
                    None if language == "auto" else language,
                )

            logger.info(
                "Transcription options updated: "
                f"language={language}"
            )
            return {
                "success": True,
                "language": language,
                "translateToEnglish": False,
            }
        except Exception as e:
            logger.error(f"Error setting transcription options: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def set_model_size(self, modelSize: str = "base"):
        """Set the Faster Whisper model size and reload the model if needed."""
        try:
            model_size = _normalize_model_size(modelSize)
            config = _read_button_config()
            config["modelSize"] = model_size
            _write_button_config(config)

            reloaded = False
            if Plugin.voice_service:
                reloaded = Plugin.voice_service.model is not None
                success = await asyncio.to_thread(
                    Plugin.voice_service.set_model_size,
                    model_size,
                )
                if not success:
                    return {"success": False, "error": Plugin.voice_service.model_load_error}

            logger.info(
                f"Whisper model size updated: {model_size}"
                f"{' (reloaded active model)' if reloaded else ''}"
            )
            return {"success": True, "modelSize": model_size, "reloaded": reloaded}
        except Exception as e:
            logger.error(f"Error setting model size: {traceback.format_exc()}")
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
            config = _read_button_config()
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

            config = _read_button_config()
            config["game"] = game
            _write_button_config(config)

            # Update running voice service
            if Plugin.voice_service:
                Plugin.voice_service.set_preset(_game_presets[game])
            Plugin.active_preset = game

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
            Plugin._start_dictation_trace()
            try:
                Plugin.voice_service.start_recording()
            except Exception as e:
                Plugin._finish_dictation_trace(False)
                if telemetry:
                    telemetry_capture_error(
                        "recording.start_failed",
                        e,
                        preset=Plugin.active_preset,
                        controller_type=Plugin._controller_type(),
                    )
                raise
            return {"success": True}
        except Exception as e:
            logger.error(f"Error starting recording: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def stop_recording(self, send: bool = True):
        """Stop recording and transcribe"""
        try:
            if Plugin.voice_service is None:
                logger.error("Voice service not initialized")
                return {"success": False, "error": "Service not initialized"}

            logger.info("Stopping recording")
            # Stream shutdown happens promptly in the worker, while Decky's
            # event loop remains available for status/UI requests during
            # transcription.
            try:
                await asyncio.to_thread(Plugin.voice_service.stop_recording, send)
            except Exception as e:
                Plugin._finish_dictation_trace(False)
                if telemetry:
                    telemetry_capture_error(
                        "recording.stop_failed",
                        e,
                        preset=Plugin.active_preset,
                        controller_type=Plugin._controller_type(),
                    )
                raise
            else:
                Plugin._finish_dictation_trace(True)
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

            detected_button = "None"
            try:
                if os.path.exists(PREVIEW_FILE):
                    with open(PREVIEW_FILE, "r") as f:
                        detected_button = f.read().strip() or "None"
            except Exception:
                pass

            return {
                "success": True,
                "service_ready": Plugin.voice_service is not None,
                "model_ready": model_ready,
                "model_loading": model_loading,
                "recording": Plugin.voice_service.is_recording if Plugin.voice_service else False,
                "recording_start_count": Plugin.recording_start_count,
                "detected_button": detected_button,
                "pending_text": Plugin.voice_service.pending_text or "" if Plugin.voice_service else "",
                "pending_delay": Plugin.voice_service._confirm_delay_for(Plugin.voice_service.pending_text) if Plugin.voice_service and Plugin.voice_service.pending_text else 0,
                "confirm_mode": Plugin.voice_service.confirm_delay > 0 if Plugin.voice_service else False,
                "input_ready": Plugin.ydotoold_ready,
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
            # Model construction and first-time download are blocking. Keep
            # Decky's RPC event loop responsive so status calls can report
            # progress instead of leaving the frontend stuck initializing.
            success = await asyncio.to_thread(Plugin.voice_service._load_model)
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
