"""Physical recording gestures and bounded, timestamped controller events."""
import uuid
from binding_capture import read_json, write_json

MODES = ('hold', 'tap')
TAP_THRESHOLD = 0.250


class RecordingGesture:
    def __init__(self, mode='hold'):
        self.mode = mode
        self.reset()

    def reset(self):
        self.recording = False
        self.latched = False
        self.pressed_at = None

    def feed(self, kind, timestamp):
        if kind == 'cancel':
            action = 'abort' if self.recording else None
            self.reset()
            return action
        if kind == 'press':
            if self.pressed_at is not None:
                return None
            self.pressed_at = timestamp
            if self.latched:
                self.recording = self.latched = False
                return 'stop'
            self.recording = True
            return 'start'
        if kind == 'release' and self.pressed_at is not None:
            duration = timestamp - self.pressed_at
            self.pressed_at = None
            if not self.recording:
                return None  # Release following the stop press.
            if self.mode == 'tap' and duration < TAP_THRESHOLD:
                self.latched = True
                return None
            self.recording = self.latched = False
            return 'stop'
        return None


class ControllerEvents:
    def __init__(self, path):
        self.path = path
        self.generation = uuid.uuid4().hex
        self.sequence = 0
        self.events = []
        self.publish()

    def publish(self):
        write_json(self.path, {'generation': self.generation, 'events': self.events})

    def append(self, kind, timestamp):
        self.sequence += 1
        self.events.append({'sequence': self.sequence, 'kind': kind, 'time': timestamp})
        self.events = self.events[-128:]
        self.publish()


class EventCursor:
    def __init__(self):
        self.generation = None
        self.sequence = 0

    def read(self, path):
        snapshot = read_json(path)
        generation = snapshot.get('generation')
        if not generation:
            return []
        reset = self.generation is not None and self.generation != generation
        if generation != self.generation:
            self.generation, self.sequence = generation, 0
        events = [event for event in snapshot.get('events', []) if event['sequence'] > self.sequence]
        gap = bool(events and events[0]['sequence'] > self.sequence + 1)
        if events:
            self.sequence = events[-1]['sequence']
        # On listener restart or queue overflow, cancel rather than replay an
        # incomplete gesture that could latch the microphone unexpectedly.
        if reset or gap:
            return [{'kind': 'cancel', 'time': 0}]
        return events
