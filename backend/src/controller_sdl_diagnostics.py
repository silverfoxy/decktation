"""Allowlisted SDL support evidence; never export names, paths, or mappings."""
import re

BOOL_HINTS = (
    'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', 'SDL_JOYSTICK_HIDAPI',
    'SDL_JOYSTICK_HIDAPI_STEAMDECK', 'SDL_JOYSTICK_HIDAPI_STEAM',
    'SDL_JOYSTICK_HIDAPI_XBOX', 'SDL_JOYSTICK_LINUX_CLASSIC',
)
FILTER_HINTS = ('SDL_GAMECONTROLLER_IGNORE_DEVICES',
                'SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT', 'SDL_HIDAPI_IGNORE_DEVICES')
PRESENCE_HINTS = ('SDL_GAMECONTROLLERCONFIG', 'SDL_GAMECONTROLLERCONFIG_FILE')
HINTS = BOOL_HINTS + FILTER_HINTS + PRESENCE_HINTS
ERRORS = {'permission_denied', 'disconnected', 'unsupported', 'other'}


def error_category(error):
    text = str(error).lower()
    if any(word in text for word in ('permission', 'access denied', 'not permitted')):
        return 'permission_denied'
    if any(word in text for word in ('disconnected', 'not connected', 'no such device')):
        return 'disconnected'
    if any(word in text for word in ('unsupported', 'not supported', 'mapping')):
        return 'unsupported'
    return 'other'


def hint_evidence(name, value):
    if not value:
        return {'state': 'unset'}
    if name in BOOL_HINTS:
        return {'state': value if value in ('0', '1') else 'other'}
    if name in FILTER_HINTS:
        if value.startswith('@'):
            return {'state': 'file'}
        pairs = value.split(',')
        valid = [pair.strip().lower() for pair in pairs[:16]
                 if re.fullmatch(r'0x[0-9a-fA-F]{4}/0x[0-9a-fA-F]{4}', pair.strip())]
        return {'state': 'list', 'devices': valid, 'truncated': len(pairs) > 16,
                'invalid': len(valid) != len(pairs[:16])}
    return {'state': 'set'}


def sanitize_sdl(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, maximum in (('version', 9999999), ('joystick_count', 65535), ('gamepad_count', 65535)):
        item = value.get(key)
        if type(item) is int and 0 <= item <= maximum:
            result[key] = item
    if type(value.get('enumeration_failed')) is bool:
        result['enumeration_failed'] = value['enumeration_failed']
    hints = value.get('hints')
    if isinstance(hints, dict):
        result['hints'] = {}
        for name in HINTS:
            entry = hints.get(name)
            if not isinstance(entry, dict):
                continue
            states = {'unset', '0', '1', 'other'} if name in BOOL_HINTS else (
                {'unset', 'file', 'list'} if name in FILTER_HINTS else {'unset', 'set'})
            if not isinstance(entry.get('state'), str) or entry['state'] not in states:
                continue
            safe = {'state': entry['state']}
            if name in FILTER_HINTS and entry['state'] == 'list':
                pairs = entry.get('devices')
                safe['devices'] = [p for p in pairs[:16] if isinstance(p, str) and
                                   re.fullmatch(r'0x[0-9a-f]{4}/0x[0-9a-f]{4}', p)] if isinstance(pairs, list) else []
                for key in ('truncated', 'invalid'):
                    safe[key] = entry.get(key) is True
            result['hints'][name] = safe
    return result
