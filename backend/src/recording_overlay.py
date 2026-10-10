#!/usr/bin/env python3
"""Input-transparent Gamescope recording indicator for Decktation."""
import math
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import cairo
from overlay_render import draw_review, draw_result
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo, Gdk, GdkX11, GLib, Gtk  # noqa: E402

STATE = Path(sys.argv[1])
PARENT_PID = int(sys.argv[2])
WIDTH = 368
HEIGHT = 80
REFERENCE_HEIGHT = 800
BOTTOM_MARGIN = 48


def rounded(ctx, x, y, w, h, radius):
    ctx.new_sub_path()
    ctx.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
    ctx.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
    ctx.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
    ctx.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
    ctx.close_path()


class Indicator(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Decktation recording indicator")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.stick()
        screen = self.get_screen()
        self.surface_width = screen.get_width()
        self.surface_height = screen.get_height()
        self.set_default_size(self.surface_width, self.surface_height)
        screen.connect("size-changed", self.sync_geometry)
        screen.connect("monitors-changed", self.sync_geometry)
        self.focus_connection = None
        self.focus_library = None
        self.state = {"mode": "hidden"}
        self.mode = "hidden"
        self.phase = time.monotonic()
        self.last_state = "hidden"
        self.connect("draw", self.draw_indicator)
        self.connect("destroy", Gtk.main_quit)

        visual = screen.get_rgba_visual()
        if visual is None:
            raise RuntimeError("Xwayland has no RGBA visual")
        self.set_visual(visual)
        self.move(0, 0)
        self.set_opacity(0)
        self.show_all()
        window = self.get_window()
        window.set_pass_through(True)
        window.input_shape_combine_region(cairo.Region(), 0, 0)
        xid = GdkX11.X11Window.get_xid(window)
        subprocess.run(
            ["xprop", "-id", str(xid), "-f", "GAMESCOPE_EXTERNAL_OVERLAY", "32c",
             "-set", "GAMESCOPE_EXTERNAL_OVERLAY", "1"], check=True
        )
        print(f"window={hex(xid)} display={os.environ['DISPLAY']} rgba=1 pass_through=1", flush=True)
        GLib.timeout_add(50, self.tick)
        GLib.timeout_add(1000, self.sync_geometry)

    def sync_geometry(self, *_args):
        screen = self.get_screen()
        width, height = screen.get_width(), screen.get_height()
        if (width, height) != (self.surface_width, self.surface_height):
            self.surface_width, self.surface_height = width, height
            self.resize(width, height)
            self.move(0, 0)
            self.queue_draw()
        return True

    def tick(self):
        if not Path(f"/proc/{PARENT_PID}").exists():
            Gtk.main_quit()
            return False
        try:
            raw = STATE.read_text().strip()
            try:
                self.state = json.loads(raw)
                mode = self.state.get("mode", "hidden")
            except (ValueError, AttributeError):
                self.state = {"mode": raw}
                mode = raw
        except FileNotFoundError:
            Gtk.main_quit()
            return False
        if mode == "result" and time.time() >= self.state.get("expires", 0):
            mode = "hidden"
        if mode not in {"compact", "transcribing", "review", "countdown", "result", "hidden"}:
            mode = "hidden"
        if mode != self.last_state:
            self.mode = mode
            self.last_state = mode
            self.set_opacity(0 if mode == "hidden" else 1)
            print(f"state={mode}", flush=True)
        if mode != "hidden":
            self.queue_draw()
        return True

    def focused_app(self):
        # Gdk.property_get cannot be called through PyGObject's caller-allocated
        # output argument on SteamOS. Use an independent, read-only X connection.
        try:
            if self.focus_library is None:
                library = ctypes.CDLL("libX11.so.6")
                library.XOpenDisplay.argtypes = [ctypes.c_char_p]
                library.XOpenDisplay.restype = ctypes.c_void_p
                library.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
                library.XDefaultRootWindow.restype = ctypes.c_ulong
                library.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
                library.XInternAtom.restype = ctypes.c_ulong
                library.XGetWindowProperty.argtypes = [
                    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                    ctypes.c_long, ctypes.c_long, ctypes.c_int, ctypes.c_ulong,
                    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
                    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                    ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                ]
                library.XGetWindowProperty.restype = ctypes.c_int
                library.XCloseDisplay.argtypes = [ctypes.c_void_p]
                library.XCloseDisplay.restype = ctypes.c_int
                library.XFree.argtypes = [ctypes.c_void_p]
                library.XFree.restype = ctypes.c_int
                self.focus_library = library
            library = self.focus_library
            if not self.focus_connection:
                self.focus_connection = library.XOpenDisplay(None)
            if not self.focus_connection:
                return None
            root = library.XDefaultRootWindow(self.focus_connection)
            atom = library.XInternAtom(self.focus_connection, b"GAMESCOPE_FOCUSED_APP", True)
            cardinal = library.XInternAtom(self.focus_connection, b"CARDINAL", True)
            if not atom or not cardinal:
                return None
            actual_type, fmt = ctypes.c_ulong(), ctypes.c_int()
            count, remaining = ctypes.c_ulong(), ctypes.c_ulong()
            data = ctypes.POINTER(ctypes.c_ubyte)()
            result = library.XGetWindowProperty(
                self.focus_connection, root, atom, 0, 1, False, cardinal,
                ctypes.byref(actual_type), ctypes.byref(fmt), ctypes.byref(count),
                ctypes.byref(remaining), ctypes.byref(data),
            )
            try:
                if result == 0 and actual_type.value == cardinal and fmt.value == 32 and count.value == 1 and data:
                    # Xlib represents a format-32 item as a native unsigned long.
                    return ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0]
            finally:
                if data:
                    library.XFree(data)
        except (OSError, AttributeError):
            pass
        return None

    def close_focus_connection(self):
        if self.focus_connection and self.focus_library:
            self.focus_library.XCloseDisplay(self.focus_connection)
            self.focus_connection = None

    def draw_indicator(self, _widget, ctx):
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
        allocation = self.get_allocation()
        width, height = allocation.width, allocation.height
        if self.mode == "result":
            draw_result(ctx, width, height, self.state.get("message", ""))
            return False
        if self.mode in {"review", "countdown"}:
            ready = draw_review(ctx, width, height, self.state)
            try:
                status = STATE.parent / "ack" / "status"
                temporary = status.with_name("status.new")
                temporary.write_text(json.dumps({
                    "id": self.state.get("id"), "ready": ready, "time": time.time(),
                    "focus_app": self.focused_app(),
                }))
                temporary.replace(status)
            except OSError:
                pass
            return False
        # Gamescope can scale this surface independently of the game resolution.
        # Use current allocation and proportional dimensions, including after docking.
        scale = min(height / REFERENCE_HEIGHT, width / (WIDTH + 32))
        ctx.translate((width - WIDTH * scale) / 2,
                      height - (HEIGHT + BOTTOM_MARGIN) * scale)
        ctx.scale(2 * scale, 2 * scale)
        rounded(ctx, 0.5, 0.5, 183, 39, 20)
        ctx.set_source_rgba(0.12, 0.13, 0.16, 0.78)
        ctx.fill_preserve()
        ctx.set_line_width(1)
        ctx.set_source_rgba(1, 1, 1, 0.17)
        ctx.stroke()
        if self.mode == "transcribing":
            ctx.set_source_rgb(0.96, 0.96, 0.97)
            try:
                label = STATE.with_name("label").read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                label = "Transcribing..."
            layout = PangoCairo.create_layout(ctx)
            layout.set_font_description(Pango.FontDescription("Sans 12px"))
            layout.set_text(label or "Transcribing...", -1)
            layout.set_width(160 * Pango.SCALE)
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            layout.set_alignment(Pango.Alignment.CENTER)
            _, text_height = layout.get_pixel_size()
            ctx.move_to(12, (40 - text_height) / 2)
            PangoCairo.show_layout(ctx, layout)
        else:
            ctx.arc(22, 20, 4, 0, math.tau)
            ctx.set_source_rgb(0.98, 0.35, 0.45)
            ctx.fill()
            t = time.monotonic() - self.phase
            for i in range(9):
                height = 4 + 13 * (0.5 + 0.5 * math.sin(t * 4.6 + i * 0.77))
                x = 68 + i * 7
                rounded(ctx, x, 20 - height / 2, 4, height, 2)
                ctx.set_source_rgb(0.99, 0.51, 0.63)
                ctx.fill()
        return False


def main():
    signal.signal(signal.SIGTERM, lambda *_: Gtk.main_quit())
    signal.signal(signal.SIGINT, lambda *_: Gtk.main_quit())
    indicator = Indicator()
    try:
        Gtk.main()
    finally:
        indicator.close_focus_connection()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"overlay error: {exc}", file=sys.stderr, flush=True)
        raise
