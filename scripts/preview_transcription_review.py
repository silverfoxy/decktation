#!/usr/bin/env python3
"""Create an offline, interactive preview using the live overlay's renderer."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend' / 'src'))
import cairo
from overlay_render import draw_review, draw_result, layout_text, paint_text


def background(ctx):
    gradient = cairo.LinearGradient(0, 0, 0, 800)
    gradient.add_color_stop_rgb(0, .08, .13, .19)
    gradient.add_color_stop_rgb(1, .17, .22, .23)
    ctx.set_source(gradient)
    ctx.paint()
    # An illustrative game scene, not a screenshot or a specific game's artwork.
    for color, points in [((.10, .18, .23), [(0, 470), (180, 240), (370, 400), (650, 180), (920, 380), (1100, 210), (1280, 460)]),
                          ((.08, .13, .16), [(0, 590), (220, 420), (520, 600), (830, 390), (1100, 530), (1280, 410)])]:
        ctx.move_to(0, 800)
        for x, y in points:
            ctx.line_to(x, y)
        ctx.line_to(1280, 800)
        ctx.close_path()
        ctx.set_source_rgb(*color)
        ctx.fill()
    ctx.set_source_rgba(.8, .9, 1, .12)
    ctx.set_line_width(1)
    for x in range(-1000, 2300, 160):
        ctx.move_to(640, 470)
        ctx.line_to(x, 800)
    for y in [540, 595, 670, 760]:
        ctx.move_to(0, y)
        ctx.line_to(1280, y)
    ctx.stroke()
    paint_text(ctx, layout_text(ctx, 'PARTY  4 / 5', 16, 200, True), 32, 28, (.49, .65, .75))
    ctx.set_source_rgba(.3, .7, .65, .5)
    for i in range(4):
        ctx.rectangle(32, 60 + i * 27, 145 - i * 12, 7)
    ctx.fill()
    paint_text(ctx, layout_text(ctx, '[Party] Ready when you are.', 15, 285), 28, 694, (.40, .55, .58))


def render(output):
    output.mkdir(parents=True, exist_ok=True)
    base = {'mode': 'review', 'id': 'example', 'text': "I'll be there in a minute.",
            'destination': 'Party', 'binding': 'L4', 'action': 'Send'}
    samples = {
        'short': base,
        'unicode': dict(base, text='Mañana estaré allí. À bientôt !\n明天见！'),
        'manual': dict(base, action='Type into chat', manual=True),
        'long': dict(base, text=('We can meet at the entrance after everyone has repaired. '
                                 'Bring food and potions, and let me know if you need a summon. ') * 5),
        'error': dict(base, error='Typing failed'),
        'countdown': dict(base, mode='countdown', deadline=1003),
        'hold': dict(base, cancel_progress=.65),
    }
    images, readiness = {}, {}
    for name, state in {**samples, 'sent': None, 'typed': None, 'cancelled': None}.items():
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1280, 800)
        ctx = cairo.Context(surface)
        background(ctx)
        if state:
            readiness[name] = draw_review(ctx, 1280, 800, state, now=1000)
        else:
            draw_result(ctx, 1280, 800, 'Sent' if name == 'sent' else 'Typed into chat' if name == 'typed' else 'Cancelled')
        png = output / f'{name}.png'
        surface.write_to_png(str(png))
        images[name] = f'{name}.png'
    html = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Decktation transcription review preview</title>
<style>
body{margin:0;background:#10151c;color:#eef3f9;font:16px system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:24px}h1{font-size:24px;margin:0 0 8px}p{color:#abb8c7;line-height:1.5}nav{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}button{background:#263649;color:#eef3f9;border:1px solid #50677e;border-radius:8px;padding:12px 18px;font:inherit;cursor:pointer}button[aria-pressed=true]{background:#386083;border-color:#91caf8}button:focus-visible{outline:3px solid #91caf8;outline-offset:3px}img{display:block;width:100%;border-radius:12px}#ptt{touch-action:none;user-select:none;background:#416789}#status{min-height:24px}footer{font-size:13px;color:#8b9aae;margin-top:20px}
</style><main><h1>Transcription review</h1>
<p>These images use the live overlay renderer at Steam Deck resolution. Select a sample, then press and release the recording button to try the flow. You can also tap or hold Space.</p>
<nav aria-label="Example transcription"><button data-sample="short">Short message</button><button data-sample="unicode">Unicode</button><button data-sample="manual">Press Enter yourself</button><button data-sample="long">Long message</button><button data-sample="error">Typing failure</button><button data-sample="countdown">Countdown</button></nav>
<img id="screen" alt="Transcription review card over an illustrative game scene">
<nav><button id="ptt">L4 — tap to send, hold to cancel</button><button id="reset">Reset</button></nav><p id="status" role="status"></p>
<footer>Offline UI preview only. No microphone, controller, or typing access. The game scene is illustrative. Countdown is frozen at three seconds for inspection.</footer></main>
<script>
const images=IMAGES,ready=READINESS;let sample='short',down=false,timer,started=0,resolved=false;
const screen=document.getElementById('screen'),status=document.getElementById('status');
function show(name){screen.src=images[name]}
function reset(){clearTimeout(timer);down=false;resolved=false;show(sample);status.textContent=(sample==='long'||sample==='error')?'Quick send is unavailable. Review the full draft in Decktation.':'Tap to send; hold for 0.6 seconds to cancel.';document.querySelectorAll('[data-sample]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sample===sample)))}
function press(){if(down||resolved)return;down=true;started=performance.now();if(sample==='countdown'){show('cancelled');status.textContent='Cancelled';resolved=true;return}show(sample==='short'?'hold':sample);timer=setTimeout(()=>{show('cancelled');status.textContent='Cancelled. Release, then reset to try again.';resolved=true},600)}
function release(){if(!down)return;down=false;clearTimeout(timer);if(resolved)return;if(performance.now()-started>=600){show('cancelled');status.textContent='Cancelled';resolved=true}else if(ready[sample]){show(sample==='manual'?'typed':'sent');status.textContent=sample==='manual'?'Typed into chat. You press Enter to send.':'Sent';resolved=true}else{show(sample);status.textContent='Open Decktation to review this draft before sending.'}}
document.querySelectorAll('[data-sample]').forEach(b=>b.onclick=()=>{sample=b.dataset.sample;reset()});
const ptt=document.getElementById('ptt');ptt.onpointerdown=e=>{ptt.setPointerCapture(e.pointerId);press()};ptt.onpointerup=release;ptt.onpointercancel=()=>{clearTimeout(timer);down=false;if(!resolved)show(sample)};
window.onkeydown=e=>{if(e.code==='Space'&&e.target.tagName!=='BUTTON'){e.preventDefault();press()}};window.onkeyup=e=>{if(e.code==='Space'){e.preventDefault();release()}};
ptt.onkeydown=e=>{if(e.code==='Space'){e.preventDefault();press()}};window.onblur=()=>{clearTimeout(timer);down=false;if(!resolved)show(sample)};
document.getElementById('reset').onclick=reset;reset();
</script></html>'''.replace('IMAGES', json.dumps(images)).replace('READINESS', json.dumps(readiness))
    page = output / 'index.html'
    page.write_text(html)
    print(page)
    return readiness


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'doc' / 'preview' / 'transcription-review')
    args = parser.parse_args()
    render(args.output)
