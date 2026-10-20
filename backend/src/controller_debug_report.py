"""Bounded, allowlisted controller-input observations and host build metadata."""
import json
import platform
import re
import shlex

from controller_profiles import PROFILES_BY_KIND

MAX_DEVICES = 16
MAX_EVENTS = 256
MAX_BYTES = 32768
DURATION = 30
FINAL_DRAIN_GRACE = 0.25
MAX_CONTROLLER_KEY = 0x2ff


def _controller_key(code):
    """Allow Linux BTN ranges, excluding keyboard-only KEY_* ranges."""
    return (type(code) is int and
            (0x100 <= code <= 0x15f or 0x220 <= code <= 0x223 or
             0x2c0 <= code <= MAX_CONTROLLER_KEY))


BUTTONS = {'A', 'B', 'X', 'Y', 'L1', 'R1', 'L2', 'R2', 'L3', 'R3',
           'L4', 'R4', 'L5', 'R5', 'View', 'Menu', 'D-pad Up', 'D-pad Down',
           'D-pad Left', 'D-pad Right', 'Left Trackpad', 'Right Trackpad'}
CONTROLLER_TYPES = {'evdev_gamepad', *PROFILES_BY_KIND}
REJECTION_REASONS = {'missing_gamepad_buttons', 'missing_stick_axes',
                     'missing_gamepad_buttons_and_stick_axes'}
METADATA_FIELDS = ('decktation_version', 'os_id', 'os_version', 'os_build',
                   'os_pretty_name', 'kernel_release', 'architecture',
                   'device_vendor', 'device_model', 'device_product_version',
                   'board_name', 'board_version', 'device_sku', 'bios_version', 'bios_date',
                   'cpu_model')


def collect_runtime_metadata(decktation_version, reader=None):
    """Collect support-relevant OS/firmware/model data, never serial numbers."""
    def read(path):
        try:
            if reader:
                value = reader(path)
            else:
                with open(path, encoding='utf-8', errors='ignore') as source:
                    value = source.read()
            return value.strip().strip(chr(0)) if isinstance(value, str) else ''
        except OSError:
            return ''

    release = {}
    for line in (read('/etc/os-release') + '\n' + read('/etc/steamos-release')).splitlines():
        key, sep, value = line.partition('=')
        if sep and key in {'ID', 'VERSION_ID', 'BUILD_ID', 'PRETTY_NAME', 'BUILD_NUMBER'}:
            try:
                release[key] = shlex.split(value, posix=True)[0]
            except (ValueError, IndexError):
                release[key] = value.strip().strip(chr(34) + chr(39))

    def safe(value, limit=100):
        if not isinstance(value, str):
            return ''
        return re.sub(r'[\x00-\x1f\x7f]', '', value).strip()[:limit]

    values = {
        'decktation_version': safe(decktation_version),
        'os_id': safe(release.get('ID', '').lower()),
        'os_version': safe(release.get('VERSION_ID', '')),
        'os_build': safe(release.get('BUILD_ID', release.get('BUILD_NUMBER', ''))),
        'os_pretty_name': safe(release.get('PRETTY_NAME', ''), 120),
        'kernel_release': safe(platform.release()),
        'architecture': safe(platform.machine()),
        'device_vendor': safe(read('/sys/devices/virtual/dmi/id/sys_vendor')),
        'device_model': safe(read('/sys/devices/virtual/dmi/id/product_name')),
        'device_product_version': safe(read('/sys/devices/virtual/dmi/id/product_version')),
        'board_name': safe(read('/sys/devices/virtual/dmi/id/board_name')),
        'board_version': safe(read('/sys/devices/virtual/dmi/id/board_version')),
        'device_sku': safe(read('/sys/devices/virtual/dmi/id/product_sku')),
        'bios_version': safe(read('/sys/devices/virtual/dmi/id/bios_version')),
        'bios_date': safe(read('/sys/devices/virtual/dmi/id/bios_date')),
        'cpu_model': safe(next((line.partition(':')[2].strip()
                               for line in read('/proc/cpuinfo').splitlines()
                               if line.lower().startswith(('model name', 'hardware'))), '')),
    }
    return {key: value for key, value in values.items() if value}


def _safe_metadata(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in METADATA_FIELDS:
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = re.sub(r'[\x00-\x1f\x7f]', '', item).strip()[:120]
    return result


def _number(value, maximum):
    return value if type(value) is int and 0 <= value <= maximum else None


def sanitize_live_input(value, sources):
    result = {'pressed': [], 'last_event': None}
    if not isinstance(value, dict):
        return result
    pressed = value.get('pressed')
    for item in pressed[:32] if isinstance(pressed, list) else []:
        if (isinstance(item, dict) and isinstance(item.get('source'), str) and
                item['source'] in sources and isinstance(item.get('button'), str) and
                item['button'] in BUTTONS):
            safe = {'source': item['source'], 'button': item['button']}
            if safe not in result['pressed']:
                result['pressed'].append(safe)
    events = sanitize_report({'devices': [{'source': source} for source in sources],
                              'events': [value.get('last_event')]})['events']
    if events and events[0]['kind'] != 'source':
        result['last_event'] = events[0]
    return result


def sanitize_report(report):
    """Build a fresh schema, never forward arbitrary listener/renderer keys."""
    if not isinstance(report, dict):
        return {'phase': 'complete', 'devices': [], 'events': []}
    result = {'phase': report.get('phase') if report.get('phase') in ('capturing', 'complete', 'stopped') else 'complete',
              'ready': report.get('ready') is True,
              'metadata': _safe_metadata(report.get('metadata')),
              'configured_buttons': [b for b in report.get('configured_buttons', [])[:5]
                                     if isinstance(b, str) and b in BUTTONS]
              if isinstance(report.get('configured_buttons'), list) else [],
              'devices': [], 'events': []}
    duration = _number(report.get('duration_ms'), 30000)
    if duration is not None:
        result['duration_ms'] = duration
    if isinstance(report.get('stop_reason'), str) and report['stop_reason'] in ('stop_requested', 'capture_timeout'):
        result['stop_reason'] = report['stop_reason']
    result['events_dropped'] = _number(report.get('events_dropped'), 65535) or 0
    truncation = report.get('truncation')
    result['truncation'] = {key: isinstance(truncation, dict) and truncation.get(key) is True
                            for key in ('events', 'devices', 'bytes')}
    for key, limit in (('events', MAX_EVENTS), ('devices', MAX_DEVICES)):
        if isinstance(report.get(key), list) and len(report[key]) > limit:
            result['truncation'][key] = True
    for device in report.get('devices', [])[:MAX_DEVICES] if isinstance(report.get('devices'), list) else []:
        if not isinstance(device, dict):
            continue
        safe = {}
        if device.get('source') in [f'source_{i}' for i in range(1, MAX_DEVICES + 1)]:
            safe['source'] = device['source']
        if isinstance(device.get('status'), str) and device['status'] in ('accepted', 'rejected', 'open_failed', 'disconnected', 'hidraw'):
            safe['status'] = device['status']
        for key, allowed in (('input_backend', {'evdev', 'hidraw'}),
                             ('controller_type', CONTROLLER_TYPES),
                             ('rejection_reason', REJECTION_REASONS)):
            if isinstance(device.get(key), str) and device[key] in allowed:
                safe[key] = device[key]
        for key in ('bindings_accepted', 'diagnostic_observed', 'input_dropped', 'capabilities_truncated'):
            if type(device.get(key)) is bool:
                safe[key] = device[key]
        for key in ('bus', 'vendor_id', 'product_id', 'hardware_version', 'errno', 'resync_count'):
            number = _number(device.get(key), 65535)
            if number is not None: safe[key] = number
        for key, limit in (('keys', MAX_CONTROLLER_KEY), ('axes', 0x3f)):
            values = device.get(key)
            if isinstance(values, list):
                if len(values) > 48:
                    safe['capabilities_truncated'] = True
                safe[key] = [v for v in values[:48] if _number(v, limit) is not None
                             and (key != 'keys' or _controller_key(v))]
        result['devices'].append(safe)
    sources = {d.get('source') for d in result['devices']}
    result['initial_state'] = []
    initial = report.get('initial_state')
    for item in initial[:MAX_DEVICES] if isinstance(initial, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get('source'), str) or item['source'] not in sources:
            continue
        at = _number(item.get('at_ms'), 30000)
        if at is None:
            continue
        buttons, keys = item.get('buttons'), item.get('keys')
        result['initial_state'].append({'source': item['source'], 'at_ms': at,
            'known': item.get('known') is True,
            'buttons': [b for b in buttons[:32] if isinstance(b, str) and b in BUTTONS]
                       if isinstance(buttons, list) else [],
            'keys': [k for k in keys[:48] if _controller_key(k)] if isinstance(keys, list) else []})
    for event in report.get('events', [])[:MAX_EVENTS] if isinstance(report.get('events'), list) else []:
        if not isinstance(event, dict) or not isinstance(event.get('source'), str) or event['source'] not in sources:
            continue
        at = _number(event.get('at_ms'), 30000)
        kind = event.get('kind')
        if at is None or kind not in ('key', 'hid', 'mapped', 'binding', 'source'):
            continue
        safe = {'at_ms': at, 'source': event['source'], 'kind': kind}
        if kind == 'key':
            code = _number(event.get('code'), MAX_CONTROLLER_KEY)
            if code is None or not _controller_key(code) or type(event.get('pressed')) is not bool: continue
            safe.update(code=code, pressed=event['pressed'])
        elif kind in ('hid', 'mapped', 'binding'):
            if not isinstance(event.get('button'), str) or event['button'] not in BUTTONS or type(event.get('pressed')) is not bool: continue
            safe.update(button=event['button'], pressed=event['pressed'])
        if kind == 'key' and isinstance(event.get('button'), str) and event['button'] in BUTTONS:
            safe['button'] = event['button']
        result['events'].append(safe)
    # A second bound protects against unusually large but valid combinations.
    while len(json.dumps(result).encode()) > MAX_BYTES and result['events']:
        result['truncation']['bytes'] = True
        result['events'].pop()
        result['events_dropped'] = min(65535, result['events_dropped'] + 1)
    # Initial state and escaped Unicode metadata can fill the budget even
    # without events. Preserve interface evidence before these optional details.
    for field in ('initial_state', 'metadata'):
        while len(json.dumps(result).encode()) > MAX_BYTES and result[field]:
            result['truncation']['bytes'] = True
            if field == 'metadata':
                result[field].popitem()
            else:
                result[field].pop()
    return result


class InputReport:
    def __init__(self, session, started, buttons, metadata=None):
        self.session = session
        self.started = started
        self.buttons = buttons
        self.metadata = _safe_metadata(metadata)
        self.devices = []
        self.events = []
        self.sources = {}
        self.held = {}
        self.initial_state = {}
        self.initialized_paths = set()
        self.live_pressed = {}
        self.last_event = None
        self.events_dropped = 0
        self.devices_truncated = False
        self.ended = None
        self.stopped = False
        self.drain_until = None

    def begin_drain(self, now):
        if self.drain_until is None:
            self.ended = min(now, self.started + DURATION)
            self.drain_until = min(now + FINAL_DRAIN_GRACE,
                                  self.started + DURATION + FINAL_DRAIN_GRACE)

    def source(self, path):
        if path not in self.sources and len(self.devices) < MAX_DEVICES:
            self.sources[path] = f'source_{len(self.devices) + 1}'
        elif path not in self.sources:
            self.devices_truncated = True
        return self.sources.get(path)

    def device(self, path, status, identity=None, keys=(), axes=(), errno=None):
        source = self.source(path)
        if not source: return
        keys = sorted((k for k in keys if _controller_key(k)),
                      key=lambda k: (0 if 0x2c0 <= k <= 0x2ff else
                                     1 if 0x100 <= k <= 0x117 else
                                     2 if 0x120 <= k <= 0x15f or 0x220 <= k <= 0x223 else 3, k))
        axes = sorted(a for a in axes if _number(a, 0x3f) is not None)
        entry = {'source': source, 'status': status, **(identity or {}),
                 'keys': keys[:48], 'axes': axes[:48], 'errno': errno,
                 'capabilities_truncated': len(keys) > 48 or len(axes) > 48}
        current = next((d for d in self.devices if d['source'] == source), None)
        if current: current.update(entry)
        else: self.devices.append(entry)

    def event(self, path, kind, now, **extra):
        capture_until = self.drain_until or self.started + DURATION
        if self.stopped or now >= capture_until:
            return
        source = self.sources.get(path)
        if source:
            at_ms = min(DURATION * 1000, max(0, int((now - self.started) * 1000)))
            event = {'at_ms': at_ms, 'source': source, 'kind': kind, **extra}
            safe = sanitize_report({'devices': [{'source': source}], 'events': [event]})['events']
            if not safe:
                return
            event = safe[0]
            if kind != 'source':
                self.last_event = event
                if 'button' in event:
                    self.live_pressed[(source, event['button'])] = event['pressed']
            if len(self.events) < MAX_EVENTS:
                self.events.append(event)
            else:
                self.events_dropped = min(65535, self.events_dropped + 1)

    def initial(self, path, states, keys, now):
        source = self.sources.get(path)
        if not source or path in self.initialized_paths:
            return
        keys = sorted(k for k in keys if _controller_key(k))[:48]
        buttons = sorted(b for b, down in (states or {}).items() if down and b in BUTTONS)
        if source not in self.initial_state or not self.initial_state[source]['known']:
            self.initial_state[source] = {'source': source,
                'at_ms': min(30000, max(0, int((now - self.started) * 1000))),
                'known': states is not None, 'keys': keys, 'buttons': buttons}
        if states is not None:
            self.initialized_paths.add(path)
        for code in keys:
            self.held[(path, code)] = True
        for button in buttons:
            self.live_pressed[(source, button)] = True

    def live_input(self):
        return sanitize_live_input({'pressed': [{'source': source, 'button': button}
            for (source, button), down in self.live_pressed.items() if down],
            'last_event': self.last_event}, set(self.sources.values()))

    def key(self, path, code, value, button, now):
        if path not in self.sources or value not in (0, 1) or not _controller_key(code): return
        key = (path, code)
        pressed = bool(value)
        if self.held.get(key, False) == pressed: return
        self.held[key] = pressed
        self.event(path, 'key', now, code=code, pressed=pressed, button=button)

    def disconnected(self, path, errno=None):
        source = self.sources.get(path)
        self.initialized_paths.discard(path)
        self.held = {key: down for key, down in self.held.items() if key[0] != path}
        for entry in self.devices:
            if entry['source'] == source:
                entry.update(status='disconnected', errno=errno)
        self.live_pressed = {key: down for key, down in self.live_pressed.items() if key[0] != source}
        if self.last_event and self.last_event['source'] == source:
            self.last_event = None

    def snapshot(self, now):
        phase = 'stopped' if self.stopped else 'complete' if now >= self.started + DURATION else 'capturing'
        ended = self.ended if self.ended is not None else now
        duration_ms = min(DURATION * 1000, max(0, int((ended - self.started) * 1000)))
        return sanitize_report({'phase': phase, 'metadata': self.metadata,
                                'configured_buttons': self.buttons,
                                'duration_ms': duration_ms,
                                'stop_reason': 'stop_requested' if self.stopped else
                                               'capture_timeout' if phase == 'complete' else None,
                                'events_dropped': self.events_dropped,
                                'truncation': {'events': self.events_dropped > 0,
                                               'devices': self.devices_truncated},
                                'initial_state': list(self.initial_state.values()),
                                'devices': self.devices, 'events': self.events})
