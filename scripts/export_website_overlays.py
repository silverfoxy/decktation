#!/usr/bin/env python3
"""Export the app's Cairo/Pango popups as an offline website SVG sprite.

Run with system Python plus PyCairo, PyGObject, and Pango installed.
No GTK window, microphone, game, network, or display server is required.
"""
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import cairo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/src'))
from overlay_render import draw_recording, draw_result, draw_review

OUTPUT = ROOT / 'site/public/assets/app-overlays'
SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)
FRAMES = 28
PERIOD = math.tau / 4.6


def symbol(name, draw, width, height, crop=False):
    stream = io.BytesIO()
    surface = cairo.SVGSurface(stream, width, height)
    draw(cairo.Context(surface))
    surface.finish()
    svg = ET.fromstring(stream.getvalue())
    viewbox = f'0 0 {width} {height}'
    if crop:
        measurement = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        draw(cairo.Context(measurement))
        _, y, _, ink_height = measurement.ink_extents()
        height = math.ceil(ink_height + 4)
        viewbox = f'0 {math.floor(y) - 2} {width} {height}'
    # Each Cairo export starts its ID sequence at zero. Namespace every ID and
    # internal glyph/clip reference before combining the exports in one sprite.
    ids = {node.attrib['id']: f'{name}-{node.attrib["id"]}'
           for node in svg.iter() if 'id' in node.attrib}
    for node in svg.iter():
        for key, value in list(node.attrib.items()):
            if key == 'id':
                node.set(key, ids[value])
            elif value.startswith('#') and value[1:] in ids:
                node.set(key, '#' + ids[value[1:]])
            elif value.startswith('url(#') and value[5:-1] in ids:
                node.set(key, 'url(#' + ids[value[5:-1]] + ')')
    result = ET.Element(f'{{{SVG}}}symbol', id=name, viewBox=viewbox)
    result.extend(svg)
    # The symbol applies the crop; its browser viewport starts at the origin.
    return result, {'viewBox': f'0 0 {width} {height}', 'width': width, 'height': height}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sprite = ET.Element(f'{{{SVG}}}svg')
    dimensions = {}
    for frame in range(FRAMES):
        node, size = symbol(f'recording-{frame}',
                            lambda ctx, i=frame: draw_recording(ctx, phase=PERIOD * i / FRAMES), 184, 40)
        sprite.append(node)
        dimensions['recording'] = size
    for name, draw, width, height, crop in [
        ('transcribing', lambda ctx: draw_recording(ctx, 'transcribing'), 184, 40, False),
        ('review', lambda ctx: draw_review(ctx, 632, 800, {
            'mode': 'review', 'text': 'ready when you are', 'destination': 'Party',
            'binding': 'L1+R1', 'action': 'Send',
        }, now=0), 632, 800, True),
        ('sent', lambda ctx: draw_result(ctx, 400, 800, 'Sent'), 400, 800, True),
        ('cancelled', lambda ctx: draw_result(ctx, 400, 800, 'Cancelled'), 400, 800, True),
        ('typed', lambda ctx: draw_result(ctx, 400, 800, 'Typed into chat'), 400, 800, True),
    ]:
        node, size = symbol(name, draw, width, height, crop)
        sprite.append(node)
        dimensions[name] = size
    ET.ElementTree(sprite).write(OUTPUT / 'sprite.svg', encoding='unicode')
    sources = ['backend/src/overlay_render.py', 'scripts/export_website_overlays.py']
    manifest = {
        'frames': FRAMES, 'periodMs': PERIOD * 1000, 'dimensions': dimensions,
        'sources': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources},
        'spriteSha256': hashlib.sha256((OUTPUT / 'sprite.svg').read_bytes()).hexdigest(),
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Exported {FRAMES} recording frames and native popups to {OUTPUT}')


if __name__ == '__main__':
    main()
