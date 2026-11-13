"""Discover, validate, and pulse a captured Steam controller output.

Single-candidate selection is a fallback, not proof of physical/virtual pairing.
Multiple outputs require an explicit association; never guess by event number.
"""
import glob
import os
import stat
import struct
import time
from contextlib import contextmanager
from copy import deepcopy

from gamepad_evdev import EvdevGamepad, ioctl_read, bits, EVENT
from binding_capture import read_json, write_json


STEAM_OUTPUT_ID = (0x28de, 0x11ff)
INJECTION_FILE = '/tmp/decktation_controller_injection.json'


def without_injected_a(path, states):
    """Do not interpret our virtual A pulse as another PTT activation."""
    marker = read_json(INJECTION_FILE)
    if not isinstance(marker, dict):
        return states
    if (marker.get('path') == path and
            type(marker.get('until')) in (int, float) and
            time.monotonic() < marker['until']):
        return {**states, 'A': False}
    return states


class ControllerOutputError(RuntimeError):
    """No verified controller destination is available for this draft."""


def capture_output(source):
    """Freeze listener evidence; never reinterpret an old source at send time."""
    resolution = source.get('output_controller') if isinstance(source, dict) else None
    return deepcopy(resolution) if isinstance(resolution, dict) else {
        'status': 'missing_source', 'target': None}


@contextmanager
def open_output(resolution):
    if not isinstance(resolution, dict) or resolution.get('status') not in (
            'same_device', 'single_candidate') or not resolution.get('target'):
        raise ControllerOutputError('Controller unavailable or ambiguous. Select one Steam controller and record again.')
    target = resolution['target']
    path = target.get('path', '')
    if not isinstance(path, str) or not path.startswith('/dev/input/event') or not path[16:].isdigit():
        raise ControllerOutputError('Invalid controller destination. Record again.')
    fd = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        current = os.fstat(fd)
        bus, vendor, product, version = struct.unpack('4H', ioctl_read(fd, 0x02, 8))
        identity = {'bus': bus, 'vendor_id': vendor, 'product_id': product,
                    'hardware_version': version}
        sysfs = os.path.realpath(f'/sys/class/input/{os.path.basename(path)}/device')
        if (not stat.S_ISCHR(current.st_mode) or
                (vendor, product) != STEAM_OUTPUT_ID or identity != target.get('identity') or
                current.st_rdev != target.get('device_number') or
                current.st_ino != target.get('inode') or sysfs != target.get('sysfs_path')):
            raise ControllerOutputError('Controller changed or disconnected. Record again.')
        if not {304, 305}.issubset(bits(ioctl_read(fd, 0x21, 96))) or not {
                0, 1}.issubset(bits(ioctl_read(fd, 0x23, 8))):
            raise ControllerOutputError('Destination is not a compatible gamepad.')
        if 304 in bits(ioctl_read(fd, 0x18, 96)):
            raise ControllerOutputError('Controller A is held. Release it before retrying.')
        yield fd
    except OSError as error:
        raise ControllerOutputError('Controller unavailable. Reconnect it and record again.') from error
    finally:
        if fd is not None:
            os.close(fd)


def press_a(fd):
    """Pulse the already verified device; always attempt release after down."""
    if 304 in bits(ioctl_read(fd, 0x18, 96)):
        raise ControllerOutputError('Controller A is held. Release it before retrying.')
    # Publish before down, and leave a bounded grace period for queued reports.
    # Only the destination's A is masked; physical input remains independent.
    write_json(INJECTION_FILE, {'path': os.readlink(f'/proc/self/fd/{fd}'),
                                'until': time.monotonic() + 1})

    def emit(value):
        packet = EVENT.pack(0, 0, 1, 304, value) + EVENT.pack(0, 0, 0, 0, 0)
        if os.write(fd, packet) != len(packet):
            raise ControllerOutputError('Controller input write was incomplete.')

    try:
        emit(1)
        time.sleep(0.1)
    finally:
        emit(0)


def discover_outputs():
    outputs = []
    for path in sorted(glob.glob('/dev/input/event*')):
        device = None
        try:
            device = EvdevGamepad(path)
            identity = device.identity
            if (identity.get('vendor_id'), identity.get('product_id')) != STEAM_OUTPUT_ID:
                continue
            device_stat = os.fstat(device.fd)
            outputs.append({'path': path, 'identity': dict(identity),
                            'device_number': device_stat.st_rdev, 'inode': device_stat.st_ino,
                            'sysfs_path': os.path.realpath(
                                f'/sys/class/input/{os.path.basename(path)}/device')})
        except (OSError, ValueError):
            continue
        finally:
            if device is not None:
                device.close()
    return outputs


def resolve_output(source, outputs):
    """Describe evidence and ambiguity without sending any controller input."""
    if not source:
        return {'status': 'missing_source', 'target': None, 'candidates': outputs}
    identity = source.get('identity', {})
    direct = [output for output in outputs
              if output['path'] == (source.get('evdev_path') or source.get('path')) and all(
                  output['identity'].get(key) == identity.get(key)
                  for key in ('vendor_id', 'product_id')) and (
                      identity.get('bus') is None or output['identity'].get('bus') == identity['bus'])]
    if len(direct) == 1:
        status, target = 'same_device', direct[0]
    elif len(outputs) == 1:
        status, target = 'single_candidate', outputs[0]
    else:
        status, target = ('ambiguous' if outputs else 'unavailable'), None
    return {'status': status, 'target': target, 'candidates': outputs}
