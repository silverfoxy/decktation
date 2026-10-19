#!/usr/bin/python3
"""Compare Gamescope UTF-8 commits with text received by a plain X11 Tk entry."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tkinter as tk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display", default=":1")
    args = parser.parse_args()
    os.environ["DISPLAY"] = args.display
    os.environ["GDK_BACKEND"] = "x11"
    helper = Path("/home/deck/homebrew/plugins/decktation/bin/gamescope-inject")
    sample = "Hi 907! | ñ é Ж 中"
    root = tk.Tk()
    root.title("Decktation: isolated X11 typing test")
    root.geometry("850x300")
    tk.Label(root, text="Plain X11 text field — Gamescope UTF-8 test", font=("sans", 18)).pack(pady=10)
    tk.Label(root, text=f"Expected: {sample}", font=("sans", 16)).pack()
    entry = tk.Entry(root, font=("sans", 22))
    entry.pack(fill="x", padx=20, pady=15)
    status = tk.StringVar(value="Click Run test. Results will be captured automatically; no Enter is sent.")
    tk.Label(root, textvariable=status, wraplength=800).pack(pady=5)

    def finish(code, error):
        actual = entry.get()
        result = {"display": args.display, "expected": sample, "actual": actual,
                  "matches": actual == sample, "helper_exit": code, "error": error}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        status.set(f"Received: {actual!r} — " + ("MATCH" if actual == sample else "MISMATCH") + ". Closing in 12 seconds.")
        root.after(12000, root.destroy)

    def inject():
        if root.focus_displayof() != entry:
            status.set("Text field is not focused. Click Run test again.")
            button.config(state="normal")
            return
        env = os.environ.copy()
        env["WAYLAND_DEBUG"] = "1"
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        env["GAMESCOPE_WAYLAND_DISPLAY"] = "gamescope-0"
        try:
            result = subprocess.run([str(helper)], input=sample.encode(), env=env, timeout=5)
            root.after(500, lambda: finish(result.returncode, None))
        except (OSError, subprocess.TimeoutExpired) as error:
            root.after(500, lambda message=str(error): finish(None, message))

    def run():
        entry.delete(0, "end")
        entry.focus_force()
        button.config(state="disabled")
        status.set("Sending in one second…")
        root.after(1000, inject)

    button = tk.Button(root, text="Run test", command=run, font=("sans", 16))
    button.pack(pady=8)
    root.after(180000, root.destroy)
    print(f"Opened isolated X11 field on {args.display}; waiting for Run test.", flush=True)
    root.mainloop()


if __name__ == "__main__":
    main()
