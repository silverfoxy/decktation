"""Listener-owned physical button capture and atomic session IPC."""
import json
import os
import tempfile


def read_json(path):
    try:
        with open(path) as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return {}


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(path), delete=False) as stream:
        json.dump(value, stream)
        temporary = stream.name
    os.replace(temporary, path)


class BindingCapture:
    def __init__(self, session, deadline):
        self.session = session
        self.deadline = deadline
        self.phase = 'release'
        self.source = None
        self.buttons = []
        self.previous = set()
        self.error = ''
        self.releasing = False

    @property
    def active(self):
        return self.phase in ('release', 'listening', 'holding')

    def update(self, sources, now):
        if not self.active:
            return
        if now >= self.deadline:
            self.phase, self.error = 'cancelled', 'Binding timed out. Your previous binding is unchanged.'
            return
        if self.phase == 'release':
            if not any(any(states.values()) for states in sources.values()):
                self.phase = 'listening'
            return
        if self.source is None:
            self.source = next((path for path, states in sources.items() if any(states.values())), None)
        if self.source is None:
            return
        if self.source not in sources:
            self.phase, self.error = 'cancelled', 'Controller disconnected. Your previous binding is unchanged.'
            return
        held = {name for name, down in sources[self.source].items() if down}
        if held:
            # Accept additions only while the existing chord remains held.
            # During staggered release, freeze the last full combination.
            if self.previous - held:
                self.releasing = True
            if not self.releasing:
                if len(held) > 5:
                    self.phase, self.error = 'cancelled', 'Use at most five buttons.'
                    return
                self.buttons = sorted(held)
            self.phase = 'holding'
        elif self.buttons and not any(any(states.values()) for states in sources.values()):
            self.phase = 'captured'
        self.previous = held

    def status(self):
        return {'session': self.session, 'phase': self.phase, 'buttons': self.buttons, 'error': self.error}
