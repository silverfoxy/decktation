#!/usr/bin/env python3
"""One explicit, bounded hardware cue. Does not modify Decktation settings."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
from controller_listener import find_steam_hidraw
from haptic_feedback import HapticFeedback, _ff_path, _identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('steam-controller', 'steam-controller-2026', 'evdev'), required=True)
    parser.add_argument('--path', required=True, help='Exact /dev/hidrawN or /dev/input/eventN path')
    parser.add_argument('--play', action='store_true', help='Send exactly one start cue')
    args = parser.parse_args()
    if args.backend.startswith('steam-controller'):
        allowed = (('steam_controller_2026',) if args.backend == 'steam-controller-2026'
                   else ('steam_controller_wired', 'steam_controller_wireless'))
        matches = {path: kind for path, kind in find_steam_hidraw()
                   if kind in allowed}
        kind = matches.get(args.path)
        if kind is None:
            parser.error('path is not a discovered Steam Controller interface of this type')
        source = {'path': args.path, 'kind': kind, 'identity': {}}
        print(f'Detected {kind} at {args.path}')
    else:
        if not args.path.startswith('/dev/input/event'):
            parser.error('evdev path must be /dev/input/eventN')
        fd = os.open(args.path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            identity = _identity(fd)
        finally:
            os.close(fd)
        source = {'path': args.path, 'kind': 'evdev_gamepad', 'identity': identity}
        ff_path, reason = _ff_path(source)
        if ff_path is None:
            parser.error(reason)
        print(f'Detected FF_RUMBLE for {args.path} on {ff_path}')
    if not args.play:
        print('Discovery only. Add --play to send one bounded start cue.')
        return
    feedback = HapticFeedback(enabled=True)
    feedback._play('started', source, 0)
    print('One start cue completed.')


if __name__ == '__main__':
    main()
