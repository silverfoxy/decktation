"""Small Linux evdev reader using the stable input.h ABI (no native dependency).

Devices are selected by gamepad capabilities, never USB vendor/product IDs.
No exclusive grab is taken, so Steam and games keep receiving input.
"""
import fcntl
import json
import os
import struct

EVENT = struct.Struct('@llHHi')
KEY_BUTTONS = {
    0x130: 'A', 0x131: 'B', 0x133: 'Y', 0x134: 'X',
    0x136: 'L1', 0x137: 'R1', 0x138: 'L2', 0x139: 'R2',
}
# Common xpad/hid mappings, then the gamepad specification's HAT2 axes.
# Prefer dedicated GAS/BRAKE axes: Xbox Bluetooth can expose Z/RZ for
# the right stick alongside these trigger axes.
TRIGGER_AXES = {'L2': (0x0a, 0x02, 0x15), 'R2': (0x09, 0x05, 0x14)}


def button_mapping(identity):
    mapping = KEY_BUTTONS.copy()
    # Xbox drivers use the historical BTN_X/BTN_Y aliases (0x133/0x134),
    # rather than the positional NORTH/WEST interpretation. Steam's virtual
    # Xbox 360 pads expose the same convention. Keep other gamepads positional.
    if identity.get('vendor_id') == 0x045e or (
        identity.get('vendor_id'), identity.get('product_id')
    ) == (0x28de, 0x11ff):
        mapping.update({0x133: 'X', 0x134: 'Y'})
    return mapping


def configured_button_mapping(identity):
    mapping = button_mapping(identity)
    config_dir = os.environ.get('DECKTATION_CONFIG_DIR', os.path.expanduser('~/.config/decktation'))
    path = os.path.join(config_dir, 'controller_mappings.json')
    device_id = '{bus:04x}:{vendor_id:04x}:{product_id:04x}'.format(
        bus=identity.get('bus', 0), vendor_id=identity.get('vendor_id', 0),
        product_id=identity.get('product_id', 0))
    try:
        with open(path) as config_file:
            config = json.load(config_file)
        overrides = config.get(device_id, {})
        if not isinstance(overrides, dict):
            raise ValueError('device mapping must be an object')
        validated = {}
        for code, name in overrides.items():
            key = int(code, 0)
            if not 0x120 <= key <= 0x2ff or name not in set(KEY_BUTTONS.values()):
                raise ValueError(f'invalid button mapping: {code}={name}')
            validated[key] = name
        mapping.update(validated)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f'Ignoring controller mapping for {device_id}: {error}', flush=True)
    return mapping


def ioctl_read(fd, number, size):
    data = bytearray(size)
    fcntl.ioctl(fd, (2 << 30) | (size << 16) | (ord('E') << 8) | number, data)
    return data


def bits(data):
    return {i for i in range(len(data) * 8) if data[i // 8] & (1 << (i % 8))}


class EvdevGamepad:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            keys = bits(ioctl_read(self.fd, 0x21, 96))
            if not {0x130, 0x131}.issubset(keys):
                raise ValueError('not a gamepad')
            self.identity = {}
            try:
                bus, vendor, product, version = struct.unpack('4H', ioctl_read(self.fd, 0x02, 8))
                self.identity = {'bus': bus, 'vendor_id': vendor, 'product_id': product,
                                 'hardware_version': version}
            except OSError:
                pass  # Diagnostics must not prevent controller input.
            self.key_buttons = configured_button_mapping(self.identity)
            self.supported_buttons = {name for code, name in self.key_buttons.items() if code in keys}
            axes = bits(ioctl_read(self.fd, 0x23, 8))
            self.axes = {}
            for name, candidates in TRIGGER_AXES.items():
                for code in candidates:
                    if code in axes:
                        value, low, high, *_ = self.absinfo(code)
                        if high > low:
                            self.axes[code] = (name, low, high)
                            self.supported_buttons.add(name)
                            break
            self.dropped = False
            self.resync_count = 0
            self.resync()
        except Exception:
            self.close()
            raise

    def close(self):
        os.close(self.fd)

    def absinfo(self, code):
        return struct.unpack('6i', ioctl_read(self.fd, 0x40 + code, 24))

    def resync(self):
        self.keys = bits(ioctl_read(self.fd, 0x18, 96))
        self.values = {code: self.absinfo(code)[0] for code in self.axes}

    def states(self):
        states = {name: False for name in KEY_BUTTONS.values()}
        for code, name in self.key_buttons.items():
            states[name] |= code in self.keys
        for code, (name, low, high) in self.axes.items():
            states[name] |= 2 * (self.values[code] - low) >= high - low
        return states

    def feed(self, event_type, code, value):
        if event_type == 0 and code == 3:  # SYN_DROPPED
            self.dropped = True
        elif event_type == 0 and code == 0:  # SYN_REPORT
            if self.dropped:
                self.resync()
                self.resync_count += 1
                self.dropped = False
            return self.states()
        elif not self.dropped:
            if event_type == 1:
                if value:
                    self.keys.add(code)
                else:
                    self.keys.discard(code)
            elif event_type == 3 and code in self.axes:
                self.values[code] = value
        return None

    def read_states(self):
        data = os.read(self.fd, EVENT.size * 64)
        if not data:
            raise OSError('evdev disconnected')
        for _, _, event_type, code, value in EVENT.iter_unpack(data):
            states = self.feed(event_type, code, value)
            if states is not None:
                yield states
