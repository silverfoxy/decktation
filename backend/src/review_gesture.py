"""Controller gestures for a pending draft, independent of audio and GTK."""


class ReviewGesture:
    HOLD_SECONDS = 0.6

    def __init__(self):
        self.down = False
        self.press_id = None
        self.started = None
        self.press_ready = False
        self.consumed = False

    def suppress_until_release(self, down):
        self.down = bool(down)
        self.press_id = None
        self.started = None
        self.press_ready = False
        self.consumed = bool(down)

    def update(self, down, draft, ready, now):
        """Return (handled, action, progress); never act on an unseen draft."""
        draft_id = draft['id'] if draft else None
        handled = bool(draft or self.consumed or self.press_id)
        action = None
        progress = 0
        if down and not self.down:
            if draft:
                self.consumed = True
                self.press_id = draft_id
                self.started = now
                self.press_ready = ready
                if draft['mode'] == 'countdown':
                    action = 'cancel'
                    self.press_id = None
        if down and self.press_id and self.press_id == draft_id:
            progress = min(1, (now - self.started) / self.HOLD_SECONDS)
            if progress >= 1:
                action = 'cancel'
                self.press_id = None
        if not down and self.down:
            if self.press_id and self.press_id == draft_id:
                # A release observed past the threshold is still a cancellation.
                if now - self.started >= self.HOLD_SECONDS:
                    action = 'cancel'
                elif ready and self.press_ready and not draft.get('sending'):
                    action = 'send'
            self.press_id = None
            self.started = None
            self.consumed = False
        self.down = bool(down)
        return handled, action, progress
