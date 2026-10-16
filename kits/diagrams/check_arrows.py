# usage: python check_arrows.py <file.svg> [more.svg ...]
# Flags SOLID arrows (have marker-end, no stroke-dasharray) whose START point lies on/inside a
# storage shape (data-kind db/cache/mq/obj, or a legacy fill=#ecfdf5 rect). README.md rule 3: such arrows must not exist.
import io, re, sys

def rects(svg):
    out = []
    # new-style shapes: <g data-kind="db|cache|mq|obj" data-bbox="x,y,w,h">
    for m in re.finditer(r'<g\b[^>]*data-kind="(db|cache|mq|obj)"[^>]*data-bbox="([\d.\-]+),([\d.\-]+),([\d.\-]+),([\d.\-]+)"', svg):
        x, y, w, h = map(float, m.groups()[1:])
        out.append((x, y, x + w, y + h))
    for m in re.finditer(r'<rect\b([^>]*)/?>', svg):
        a = m.group(1)
        if 'fill="#ecfdf5"' not in a.lower():
            continue
        g = {k: float(v) for k, v in re.findall(r'(?<![\w-])(x|y|width|height)="([\d.\-]+)"', a)}
        if all(k in g for k in ('x', 'y', 'width', 'height')):
            out.append((g['x'], g['y'], g['x'] + g['width'], g['y'] + g['height']))
    return out

def starts(svg):
    res = []
    for m in re.finditer(r'<(line|path|polyline)\b([^>]*)/?>', svg):
        tag, a = m.group(1), m.group(2)
        if 'marker-end' not in a or 'stroke-dasharray' in a:
            continue
        if tag == 'line':
            g = dict(re.findall(r'\b(x1|y1)="([\d.\-]+)"', a))
            if 'x1' in g and 'y1' in g:
                res.append((float(g['x1']), float(g['y1']), m.group(0)[:120]))
        elif tag == 'path':
            d = re.search(r'\bd="\s*[Mm]\s*([\d.\-]+)[ ,]+([\d.\-]+)', a)
            if d:
                res.append((float(d.group(1)), float(d.group(2)), m.group(0)[:120]))
        else:
            p = re.search(r'points="\s*([\d.\-]+)[ ,]+([\d.\-]+)', a)
            if p:
                res.append((float(p.group(1)), float(p.group(2)), m.group(0)[:120]))
    return res

tol = 6
bad_total = 0
for f in sys.argv[1:]:
    svg = io.open(f, encoding='utf-8').read()
    R = rects(svg)
    bad = [(x, y, s) for x, y, s in starts(svg)
           if any(x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol for x0, y0, x1, y1 in R)]
    bad_total += len(bad)
    print(f'{f}: {len(bad)} solid arrow(s) starting at storage')
    for x, y, s in bad:
        print(f'   start=({x:.0f},{y:.0f})  {s}')
print('TOTAL', bad_total)
