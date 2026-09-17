"""Small Linux evdev reader using the stable input.h ABI (no native dependency).

Devices are selected by gamepad capabilities, never USB vendor/product IDs.
No exclusive grab is taken, so Steam and games keep receiving input.
"""
import fcntl
import os
import struct

EVENT = struct.Struct('@llHHi')
KEY_BUTTONS = {
    0x130: 'A', 0x131: 'B', 0x133: 'Y', 0x134: 'X',
    0x136: 'L1', 0x137: 'R1', 0x138: 'L2', 0x139: 'R2',
}
# Common xpad/hid mappings, then the gamepad specification's HAT2 axes.
TRIGGER_AXES = {'L2': (0x02, 0x0a, 0x15), 'R2': (0x05, 0x09, 0x14)}


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
            self.supported_buttons = {name for code, name in KEY_BUTTONS.items() if code in keys}
            self.identity = {}
            try:
                bus, vendor, product, version = struct.unpack('4H', ioctl_read(self.fd, 0x02, 8))
                self.identity = {'bus': bus, 'vendor_id': vendor, 'product_id': product,
                                 'hardware_version': version}
            except OSError:
                pass  # Diagnostics must not prevent controller input.
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
        states = {name: code in self.keys for code, name in KEY_BUTTONS.items()}
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
