"""Shared Cairo/Pango drawing for the live overlay and offline PNG previews."""
import math
import time
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

CARD_WIDTH = 600
TEXT_WIDTH = 544
MAX_LINES = 6


def rounded(ctx, x, y, width, height, radius):
    ctx.new_sub_path()
    for cx, cy, start in ((x + width - radius, y + radius, -math.pi / 2),
                          (x + width - radius, y + height - radius, 0),
                          (x + radius, y + height - radius, math.pi / 2),
                          (x + radius, y + radius, math.pi)):
        ctx.arc(cx, cy, radius, start, start + math.pi / 2)
    ctx.close_path()


def layout_text(ctx, text, size=22, width=TEXT_WIDTH, bold=False):
    layout = PangoCairo.create_layout(ctx)
    font = Pango.FontDescription('Sans')
    font.set_absolute_size(size * Pango.SCALE)
    font.set_weight(Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    layout.set_font_description(font)
    layout.set_width(int(width * Pango.SCALE))
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_spacing(5 * Pango.SCALE)
    layout.set_text(str(text), -1)
    return layout


def paint_text(ctx, layout, x, y, color=(0.96, 0.97, 0.98)):
    ctx.set_source_rgb(*color)
    ctx.move_to(x, y)
    PangoCairo.show_layout(ctx, layout)


def draw_review(ctx, width, height, state, now=None):
    """Draw at reference proportions; return whether the full text is visible."""
    now = time.time() if now is None else now
    scale = min(height / 800, width / (CARD_WIDTH + 32))
    ctx.save()
    # Measure at the actual render scale so truncation matches what is displayed.
    ctx.scale(scale, scale)
    body = layout_text(ctx, state.get('text', ''))
    truncated = body.get_line_count() > MAX_LINES
    if truncated:
        body.set_height(-MAX_LINES)
        body.set_ellipsize(Pango.EllipsizeMode.END)
    body_height = body.get_pixel_size()[1]
    error = state.get('error', '')
    note = ('Open Decktation to review all' if truncated else
            'After typing, press Enter in the game' if state.get('manual') else '')
    if error:
        note = 'Typing failed · Check game focus, then retry in Decktation'
    note_layout = layout_text(ctx, note, 16) if note else None
    note_height = note_layout.get_pixel_size()[1] + 14 if note_layout else 0
    card_height = 134 + body_height + note_height
    x = (width / scale - CARD_WIDTH) / 2
    y = height / scale - card_height - 48
    ctx.translate(x, y)
    rounded(ctx, 0, 0, CARD_WIDTH, card_height, 22)
    ctx.set_source_rgba(0.08, 0.10, 0.13, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.19)
    ctx.set_line_width(1)
    ctx.stroke()
    header = 'Sending…' if state.get('sending') else 'Review transcription'
    if state.get('mode') == 'countdown' and not state.get('sending'):
        remaining = max(0, (state.get('deadline') or now) - now)
        header = f'{"Typing" if state.get("manual") else "Sending"} in {math.ceil(remaining)}s'
    paint_text(ctx, layout_text(ctx, header, 18, 340, True), 28, 23, (0.65, 0.82, 0.98))
    destination = layout_text(ctx, state.get('destination', ''), 16, 170)
    destination.set_height(-1)
    destination.set_ellipsize(Pango.EllipsizeMode.END)
    paint_text(ctx, destination, 402, 25, (0.70, 0.75, 0.81))
    paint_text(ctx, body, 28, 66)
    if note_layout:
        paint_text(ctx, note_layout, 28, 66 + body_height + 14, (0.95, 0.70, 0.48) if error else (0.72, 0.77, 0.82))
    binding = state.get('binding', 'PTT')
    label = state.get('action', 'Send').lower()
    if state.get('mode') == 'countdown':
        hints = f'Press {binding} to cancel'
    elif truncated or error:
        hints = f'Hold {binding} to cancel'
    else:
        hints = f'Tap {binding} to {label}     ·     Hold {binding} to cancel'
    hint_layout = layout_text(ctx, hints, 17, TEXT_WIDTH, True)
    hint_layout.set_height(-1)
    hint_layout.set_ellipsize(Pango.EllipsizeMode.END)
    paint_text(ctx, hint_layout, 28, card_height - 43)
    progress = state.get('cancel_progress', 0)
    if progress:
        rounded(ctx, 28, card_height - 12, TEXT_WIDTH * min(1, progress), 4, 2)
        ctx.set_source_rgb(0.99, 0.51, 0.63)
        ctx.fill()
    ctx.restore()
    return not truncated and not error and not state.get('sending')


def draw_result(ctx, width, height, message):
    scale = min(height / 800, width / 400)
    ctx.save()
    ctx.translate((width - 368 * scale) / 2, height - 128 * scale)
    ctx.scale(scale, scale)
    rounded(ctx, 0, 0, 368, 80, 40)
    ctx.set_source_rgba(0.08, 0.10, 0.13, 0.96)
    ctx.fill()
    label = layout_text(ctx, message, 22, 320, True)
    label.set_alignment(Pango.Alignment.CENTER)
    paint_text(ctx, label, 24, 25)
    ctx.restore()
