#!/usr/bin/env python3
"""Compare SDL 3 and Decktation input coverage locally; never trigger dictation."""
import argparse
from collections import Counter
import glob
import json
import math
import os
from pathlib import Path
import selectors
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend' / 'src'))
from controller_listener import ComboTracker
from controller_profiles import HidGamepad, PROFILES_BY_KIND, find_hidraw
from deck_hid import STEAM_DECK_BUTTON_BITS
from gamepad_evdev import EvdevGamepad
from sdl_gamepad import SdlGamepads


class Comparison:
    """Shadow binding counters are independent per source, never production state."""
    def __init__(self, buttons, emit, clock=time.monotonic):
        self.buttons, self.emit, self.clock = buttons, emit, clock
        self.started = clock()
        self.sources = {}
        self.tracker = ComboTracker(buttons)

    def record(self, record):
        source = record.get('source')
        event = record['event']
        if event == 'connected':
            previous = self.sources.get(source, {})
            self.sources[source] = {
                **record, 'connected': True,
                'presses': previous.get('presses', Counter()),
                'releases': previous.get('releases', Counter()),
                'raw_presses': previous.get('raw_presses', Counter()),
                'raw_releases': previous.get('raw_releases', Counter()),
                'combo_presses': previous.get('combo_presses', 0),
                'combo_releases': previous.get('combo_releases', 0),
                'disconnects': previous.get('disconnects', 0),
            }
            self.tracker.update(source, record.get('initial', {}))
        elif source in self.sources:
            entry = self.sources[source]
            if event == 'disconnected':
                entry['connected'] = False
                entry['disconnects'] += 1
                self.tracker.remove(source)
            elif event == 'raw_button':
                entry['raw_presses' if record['pressed'] else 'raw_releases'][str(record['button_index'])] += 1
            elif event == 'transition':
                before = self.tracker.sources.get(source, {})
                after = {**before, record['button']: record['pressed']}
                if before.get(record['button'], False) != record['pressed']:
                    entry['presses' if record['pressed'] else 'releases'][record['button']] += 1
                    held_before = all(before.get(button, False) for button in self.buttons)
                    held_after = all(after.get(button, False) for button in self.buttons)
                    if held_before != held_after:
                        entry['combo_presses' if held_after else 'combo_releases'] += 1
                    self.tracker.update(source, after)
        self.emit({'at_ms': round((self.clock() - self.started) * 1000), **record})

    def summary(self):
        return {'event': 'summary', 'duration_ms': round((self.clock() - self.started) * 1000),
                'shadow_binding': self.buttons,
                'sources': {source: {**entry, 'held_buttons': sorted(
                    button for button, down in self.tracker.sources.get(source, {}).items() if down)}
                    for source, entry in self.sources.items()},
                'note': 'Sources are independent observations; matching VID/PID does not prove device equivalence.'}


class LegacyReaders:
    def __init__(self, record):
        self.record = record
        self.selector = selectors.DefaultSelector()
        self.devices, self.states, self.errors = {}, {}, set()

    def scan(self):
        candidates = {path: kind for path, kind in find_hidraw()}
        candidates.update({path: 'evdev_gamepad' for path in glob.glob('/dev/input/event*')})
        for path in list(self.devices):
            if path not in candidates:
                self.remove(path)
        for path, kind in candidates.items():
            if path in self.devices:
                continue
            device = None
            try:
                device = (EvdevGamepad(path) if kind == 'evdev_gamepad' else
                          HidGamepad(path, PROFILES_BY_KIND[kind]))
                self.selector.register(device.fd, selectors.EVENT_READ, path)
            except ValueError:
                # EvdevGamepad closes rejected devices, including keyboards.
                if device is not None:
                    device.close()
                continue
            except OSError as error:
                if device is not None:
                    device.close()
                if (path, error.errno) not in self.errors:
                    self.errors.add((path, error.errno))
                    self.record({'event': 'open_failed', 'source': f'legacy:{path}', 'errno': error.errno})
                continue
            self.devices[path] = device
            self.states[path] = device.states() if kind == 'evdev_gamepad' else {}
            self.record({'event': 'connected', 'source': f'legacy:{path}',
                         'backend': 'evdev' if kind == 'evdev_gamepad' else 'hidraw',
                         'controller_type': kind, 'path': path, 'identity': device.identity,
                         'supported_buttons': sorted(device.supported_buttons),
                         'initial': self.states[path].copy()})

    def poll(self):
        for key, _ in self.selector.select(timeout=0):
            path = key.data
            try:
                for states in self.devices[path].read_states():
                    for name, down in states.items():
                        if self.states[path].get(name, False) != down:
                            self.record({'event': 'transition', 'source': f'legacy:{path}',
                                         'button': name, 'pressed': down})
                    self.states[path] = states
            except BlockingIOError:
                pass
            except OSError:
                self.remove(path)

    def remove(self, path, announce=True):
        device = self.devices.pop(path)
        self.selector.unregister(device.fd)
        device.close()
        self.states.pop(path)
        if announce:
            self.record({'event': 'disconnected', 'source': f'legacy:{path}'})

    def close(self):
        for path in list(self.devices):
            self.remove(path, announce=False)
        self.selector.close()


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=60, help='Capture duration, 0–3600 seconds')
    parser.add_argument('--sdl-library', help='Explicit SDL 3.2+ shared library path')
    parser.add_argument('--sdl-hidapi', choices=('off', 'on'), default='off',
                        help='off tests OS/InputPlumber output; on also enables SDL device drivers')
    parser.add_argument('--sdl-only', action='store_true', help='Do not open additional legacy readers')
    parser.add_argument('--buttons', default='L1+R1', help='Shadow binding, e.g. L4+R4 (never activates PTT)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or not 0 <= args.seconds <= 3600:
        parser.error('--seconds must be finite and between 0 and 3600')
    args.buttons = args.buttons.split('+')
    if not 1 <= len(args.buttons) <= 5 or any(button not in STEAM_DECK_BUTTON_BITS for button in args.buttons):
        parser.error('--buttons must contain 1–5 Decktation controller buttons separated by +')
    return args


def main(argv=None):
    args = arguments(argv)
    emit = lambda record: print(json.dumps(record, sort_keys=True), flush=True)
    comparison = Comparison(args.buttons, emit)
    legacy, sdl = None, None
    exit_code = 0
    try:
        sdl = SdlGamepads(args.sdl_library, hidapi=args.sdl_hidapi == 'on')
        emit({'event': 'started', 'sdl_version': sdl.lib.SDL_GetVersion(),
              'hints': sdl.hints, 'legacy_readers': not args.sdl_only,
              'mode': 'observation_only', 'shadow_binding': args.buttons})
        if not args.sdl_only:
            legacy = LegacyReaders(comparison.record)
        deadline, next_scan = time.monotonic() + args.seconds, 0
        while True:
            now = time.monotonic()
            if legacy and now >= next_scan:
                legacy.scan()
                next_scan = now + 2
            for record in sdl.poll():
                comparison.record(record)
            if legacy:
                legacy.poll()
            if now >= deadline:
                break
            time.sleep(0.008)
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as error:
        emit({'event': 'error', 'error': str(error)})
        exit_code = 1
    finally:
        # Capture the observed status before shutdown closes healthy sources.
        emit(comparison.summary())
        if legacy:
            legacy.close()
        if sdl:
            sdl.close()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
