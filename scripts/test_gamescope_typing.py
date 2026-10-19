#!/usr/bin/env python3
"""Send a known UTF-8 sample directly to the installed Gamescope helper."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("ascii", "unicode", "mixed"), default="mixed")
    parser.add_argument("--delay", type=float, default=15, help="seconds to focus an empty game text field")
    parser.add_argument("--helper", type=Path, default=Path("/home/deck/homebrew/plugins/decktation/bin/gamescope-inject"))
    parser.add_argument("--trace", action="store_true", help="print Wayland protocol traffic, including the sample")
    parser.add_argument("--probe", action="store_true", help="check capability without typing")
    args = parser.parse_args()
    if not 0 <= args.delay <= 300:
        parser.error("--delay must be between 0 and 300")
    samples = {"ascii": "Hello 907!", "unicode": "mañana Привет 中文", "mixed": "Hi 907! | ñ é Ж 中"}
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    env.setdefault("GAMESCOPE_WAYLAND_DISPLAY", "gamescope-0")
    if args.trace:
        env["WAYLAND_DEBUG"] = "1"
    try:
        probe = subprocess.run([str(args.helper), "--probe"], env=env, timeout=5)
        if probe.returncode or args.probe:
            return probe.returncode
        sample = samples[args.case]
        print(f"Expected ({len(sample)} characters): {sample!r}", flush=True)
        print(f"Focus an EMPTY game text field. Sending in {args.delay:g}s; no Enter or clear keys.", flush=True)
        time.sleep(args.delay)
        result = subprocess.run([str(args.helper)], input=sample.encode("utf-8"), env=env, timeout=5)
        print(f"Helper exit: {result.returncode}. Compare the visible text with the expected sample.", flush=True)
        print("Exit 0 confirms protocol completion only, not correct text delivery.", flush=True)
        return result.returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
