"""Optional renderer checks run when the host has SteamOS's Cairo/Pango deps."""
import pytest

cairo = pytest.importorskip('cairo')
gi = pytest.importorskip('gi')
from overlay_render import draw_review, draw_result


def canvas(width=1280, height=800):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    return surface, cairo.Context(surface)


@pytest.mark.parametrize('size', [(1280, 800), (1920, 1080), (800, 1280)])
def test_short_unicode_message_is_fully_visible(size):
    _, ctx = canvas(*size)
    assert draw_review(ctx, *size, {'text': 'Mañana estaré allí. À bientôt !\n明天见！', 'mode': 'review'})


def test_long_message_cannot_be_quick_confirmed():
    _, ctx = canvas()
    assert not draw_review(ctx, 1280, 800, {'text': 'Please meet at the entrance. ' * 100})


@pytest.mark.parametrize('extra', [{'error': 'Typing failed'}, {'sending': True}])
def test_failed_or_sending_card_cannot_be_quick_confirmed(extra):
    _, ctx = canvas()
    assert not draw_review(ctx, 1280, 800, dict(text='Hello', **extra))


def test_render_countdown_and_result_to_png(tmp_path):
    surface, ctx = canvas()
    draw_review(ctx, 1280, 800, {'text': 'Hello', 'mode': 'countdown', 'deadline': 1003}, now=1000)
    draw_result(ctx, 1280, 800, 'Cancelled')
    path = tmp_path / 'preview.png'
    surface.write_to_png(str(path))
    assert path.read_bytes().startswith(b'\x89PNG')


def test_blocked_confirmation_explains_reason_without_advertising_tap(monkeypatch):
    import overlay_render
    texts = []
    original = overlay_render.layout_text

    def capture(ctx, text, *args, **kwargs):
        texts.append(text)
        return original(ctx, text, *args, **kwargs)

    monkeypatch.setattr(overlay_render, 'layout_text', capture)
    _, ctx = canvas()
    assert draw_review(ctx, 1280, 800, {
        'text': 'Hello', 'binding': 'L2+R2+X',
        'send_block_reason': 'Close Steam menus and return to your game',
    })  # Readability remains true so clearing the focus block can enable sending.
    assert 'Close Steam menus and return to your game' in texts
    assert not any(text.startswith('Tap ') for text in texts)


def test_recording_wave_moves_but_transcribing_pill_is_static():
    from overlay_render import draw_recording

    def pixels(mode, phase):
        surface, ctx = canvas(184, 40)
        draw_recording(ctx, mode, phase)
        surface.flush()
        return bytes(surface.get_data())

    recording = pixels('compact', 0)
    assert recording != pixels('compact', 0.4)
    assert pixels('transcribing', 0) == pixels('transcribing', 0.4)
    assert recording != pixels('transcribing', 0)
    # Rounded corners stay transparent while the pill interior is painted.
    assert recording[3] == 0
    assert recording[(20 * 184 + 22) * 4 + 3] > 0
