#!/usr/bin/env python3
"""Inspect the last PTT source and current Steam outputs; never send input."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src'))
from controller_output import discover_outputs, resolve_output


def main():
    path = Path('/tmp/decktation_haptic_source.json')
    try:
        source = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        sys.exit(f'Hold the PTT combo with Decktation running, then retry: {error}')
    if not isinstance(source, dict):
        sys.exit('No PTT source captured; hold the PTT combo and retry.')
    print(json.dumps({'last_ptt_source': source,
                      'current_output_resolution': resolve_output(source, discover_outputs())},
                     indent=2))


if __name__ == '__main__':
    main()
