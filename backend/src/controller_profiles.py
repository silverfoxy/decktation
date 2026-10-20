"""Explicit proprietary HID layouts; ordinary controllers use evdev capabilities."""
from dataclasses import dataclass
from typing import Callable
import glob
import os

from deck_hid import (STEAM_DECK_BUTTON_BITS, STEAM_CONTROLLER_BUTTON_BITS,
                      TRITON_BUTTON_MASKS, raw_button_states, triton_button_states)
from legion_go_s import BUTTON_BITS, button_states


def valve_states(report):
    # Wireless receiver remains connected when the controller disconnects.
    if len(report) >= 5 and report[:3] == b'\x01\x00\x03' and report[4] == 1:
        return dict.fromkeys(STEAM_DECK_BUTTON_BITS, False)
    return raw_button_states(report)


@dataclass(frozen=True)
class ControllerProfile:
    kind: str
    bus: int
    vendor: int
    products: tuple
    decode: Callable[[bytes], dict[str, bool] | None]
    buttons: frozenset
    report_size: int = 64
    # hid-steam can require read/write access even for input delivery.
    access: int = os.O_RDWR
    physical_suffixes: tuple | None = None
    usb_interface: str | None = None
    feedback: str | None = None

    def matches(self, properties, device):
        try:
            bus, vendor, product = (int(part, 16) for part in properties.get('HID_ID', '').split(':'))
        except ValueError:
            return False
        if (bus, vendor) != (self.bus, self.vendor) or product not in self.products:
            return False
        if self.physical_suffixes is not None and not properties.get('HID_PHYS', '').endswith(self.physical_suffixes):
            return False
        if self.usb_interface is not None:
            with open(os.path.join(device, '..', 'bInterfaceNumber')) as source:
                return source.read().strip().lower() == self.usb_interface
        return True


PROFILES = (
    ControllerProfile('steam_deck', 3, 0x28de, (0x1205,), valve_states,
                      frozenset(STEAM_DECK_BUTTON_BITS), physical_suffixes=('/input2',), feedback='deck'),
    ControllerProfile('steam_controller_wired', 3, 0x28de, (0x1102,), valve_states,
                      frozenset(STEAM_CONTROLLER_BUTTON_BITS), physical_suffixes=('/input2',), feedback='legacy'),
    ControllerProfile('steam_controller_wireless', 3, 0x28de, (0x1142,), valve_states,
                      frozenset(STEAM_CONTROLLER_BUTTON_BITS), physical_suffixes=('/input1', '/input2'), feedback='legacy'),
    *(ControllerProfile(kind, bus, 0x28de, (product,), triton_button_states,
                        frozenset(TRITON_BUTTON_MASKS), physical_suffixes=suffixes, feedback=feedback)
      for product, kind, suffixes, bus, feedback in (
          (0x1304, 'steam_controller_2026_puck', tuple(f'/input{i}' for i in range(2, 6)), 3, 'triton'),
          (0x1305, 'steam_controller_2026_receiver', tuple(f'/input{i}' for i in range(2, 6)), 3, None),
          (0x1302, 'steam_controller_2026_wired', ('/input0', '/input1', '/input2'), 3, None),
          (0x1303, 'steam_controller_2026_bluetooth', None, 5, None))),
    ControllerProfile('legion_go_s', 3, 0x1a86, (0xe310, 0xe311), button_states,
                      frozenset(BUTTON_BITS), report_size=32, access=os.O_RDONLY, usb_interface='06'),
)
PROFILES_BY_KIND = {profile.kind: profile for profile in PROFILES}


def find_hidraw(sysfs_root='/sys/class/hidraw', profiles=None):
    """Scan once and accept only known report layouts on their controller interface."""
    for path in glob.glob('/dev/hidraw*'):
        device = os.path.join(sysfs_root, os.path.basename(path), 'device')
        try:
            with open(os.path.join(device, 'uevent')) as source:
                properties = dict(line.rstrip().split('=', 1) for line in source if '=' in line)
            for profile in PROFILES if profiles is None else profiles:
                if profile.matches(properties, device):
                    yield path, profile.kind
                    break
        except (OSError, ValueError):
            continue


class HidGamepad:
    """Nonexclusive reader whose access mode and decoding come from its profile."""
    def __init__(self, path, profile):
        self.profile = profile
        self.supported_buttons = set(profile.buttons)
        self.identity = {}
        try:
            with open(f'/sys/class/hidraw/{os.path.basename(path)}/device/uevent') as source:
                properties = dict(line.rstrip().split('=', 1) for line in source if '=' in line)
            values = [int(part, 16) for part in properties.get('HID_ID', '').split(':')]
            if len(values) == 3 and all(0 <= value <= 65535 for value in values):
                self.identity = dict(zip(('bus', 'vendor_id', 'product_id'), values))
        except (OSError, ValueError):
            pass
        self.fd = os.open(path, profile.access | os.O_NONBLOCK)

    def close(self):
        os.close(self.fd)

    def read_states(self):
        report = os.read(self.fd, self.profile.report_size)
        if not report:
            raise OSError('HID controller disconnected')
        states = self.profile.decode(report)
        if states is not None:
            yield states
