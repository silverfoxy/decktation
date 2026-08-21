"""Decky entry point for the packaged Decktation backend.

The backend source is built from ``backend/src`` and installed in ``bin`` by
the Decky CLI. Keep this file intentionally small: Decky Loader imports
``main.py`` from the plugin root.
"""

import os
import sys


plugin_path = os.environ["DECKY_PLUGIN_DIR"]
backend_path = os.path.join(plugin_path, "bin")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from decktation_backend import Plugin
