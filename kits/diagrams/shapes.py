# Workspace-standard component shapes for architecture diagrams (C4-based + cloud conventions).
# Spec: README.md in this directory.
# Import:  import sys; sys.path.insert(0, '<workspace>/kits/diagrams'); from shapes import *
# Every function returns an SVG string wrapped in <g data-kind=".." data-bbox="x,y,w,h">.
# (x, y, w, h) is the bounding box; arrows should attach to the bbox edges.
# title = first line (13px), sub = optional second line (11px). Keep both short.

def _esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def _g(kind, x, y, w, h, body):
    return f'<g data-kind="{kind}" data-bbox="{x:g},{y:g},{w:g},{h:g}">{body}</g>'

def _text(x, y, w, h, title, sub, dy=0, color='#1e293b', subcolor='#7a8494'):
    cx = x + w / 2
    if sub:
        t1 = y + h / 2 - 3 + dy
        return (f'<text x="{cx:g}" y="{t1:g}" font-size="13" fill="{color}" text-anchor="middle">{_esc(title)}</text>'
                f'<text x="{cx:g}" y="{t1 + 16:g}" font-size="11" fill="{subcolor}" text-anchor="middle">{_esc(sub)}</text>')
    return f'<text x="{cx:g}" y="{y + h / 2 + 5 + dy:g}" font-size="13" fill="{color}" text-anchor="middle">{_esc(title)}</text>'

# ---- compute / actors -------------------------------------------------------
def service(x, y, w, h, title, sub=None):
    body = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="#eef2ff" stroke="#2563eb" stroke-width="1.5"/>'
    return _g('service', x, y, w, h, body + _text(x, y, w, h, title, sub))

def client(x, y, w, h, title, sub=None):
    body = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="1.5"/>'
    return _g('client', x, y, w, h, body + _text(x, y, w, h, title, sub))

def external(x, y, w, h, title, sub=None):
    body = (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="#f1f5f9" stroke="#64748b" '
            f'stroke-width="1.5" stroke-dasharray="5 3"/>')
    return _g('external', x, y, w, h, body + _text(x, y, w, h, title, sub))

def lb(x, y, w, h, title, sub=None):
    k = min(14, w * 0.15)
    pts = f'{x + k:g},{y:g} {x + w - k:g},{y:g} {x + w:g},{y + h / 2:g} {x + w - k:g},{y + h:g} {x + k:g},{y + h:g} {x:g},{y + h / 2:g}'
    body = f'<polygon points="{pts}" fill="#eef2ff" stroke="#2563eb" stroke-width="1.5"/>'
    return _g('lb', x, y, w, h, body + _text(x, y, w, h, title, sub))

# ---- storage ----------------------------------------------------------------
def _cyl(x, y, w, h, fill, stroke, dash=''):
    ry = max(5, min(9, h * 0.13))
    d = (f'M{x:g},{y + ry:g} A{w / 2:g},{ry:g} 0 0 1 {x + w:g},{y + ry:g} V{y + h - ry:g} '
         f'A{w / 2:g},{ry:g} 0 0 1 {x:g},{y + h - ry:g} Z')
    da = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{da}/>'
            f'<path d="M{x:g},{y + ry:g} A{w / 2:g},{ry:g} 0 0 0 {x + w:g},{y + ry:g}" fill="none" stroke="{stroke}" stroke-width="1.5"{da}/>'), ry

def db(x, y, w, h, title, sub=None):
    """Database (relational / NoSQL / coordination store like ZK). title = product, e.g. 'MySQL'."""
    body, ry = _cyl(x, y, w, h, '#ecfdf5', '#047857')
    return _g('db', x, y, w, h, body + _text(x, y, w, h, title, sub, dy=ry / 2))

def cache(x, y, w, h, title, sub=None):
    """In-memory cache (volatile): dashed amber cylinder. title = product, e.g. 'Redis'."""
    body, ry = _cyl(x, y, w, h, '#fefce8', '#a16207', dash='5 3')
    return _g('cache', x, y, w, h, body + _text(x, y, w, h, title, sub, dy=ry / 2))

def mq(x, y, w, h, title, sub=None):
    """Message queue / log / pub-sub: horizontal pipe. title = product, e.g. 'Kafka'."""
    rx = max(6, min(12, w * 0.08))
    d = (f'M{x + rx:g},{y:g} H{x + w - rx:g} A{rx:g},{h / 2:g} 0 0 1 {x + w - rx:g},{y + h:g} '
         f'H{x + rx:g} A{rx:g},{h / 2:g} 0 0 1 {x + rx:g},{y:g} Z')
    cap = f'<path d="M{x + w - rx:g},{y:g} A{rx:g},{h / 2:g} 0 0 0 {x + w - rx:g},{y + h:g}" fill="none" stroke="#7c3aed" stroke-width="1.5"/>'
    body = f'<path d="{d}" fill="#f5f3ff" stroke="#7c3aed" stroke-width="1.5"/>' + cap
    return _g('mq', x, y, w, h, body + _text(x - rx / 2, y, w, h, title, sub))

def obj(x, y, w, h, title, sub=None):
    """Object / blob store: bucket. title = product, e.g. 'S3'."""
    k = min(12, w * 0.1); ry = max(4, min(7, h * 0.1))
    d = (f'M{x:g},{y + ry:g} L{x + k:g},{y + h:g} H{x + w - k:g} L{x + w:g},{y + ry:g} '
         f'A{w / 2:g},{ry:g} 0 0 0 {x:g},{y + ry:g} Z')
    rim = f'<path d="M{x:g},{y + ry:g} A{w / 2:g},{ry:g} 0 0 0 {x + w:g},{y + ry:g}" fill="none" stroke="#0369a1" stroke-width="1.5"/>'
    body = f'<path d="{d}" fill="#f0f9ff" stroke="#0369a1" stroke-width="1.5"/>' + rim
    return _g('obj', x, y, w, h, body + _text(x, y, w, h, title, sub, dy=ry / 2))

def cdn(x, y, w, h, title, sub=None):
    """CDN / edge: cloud."""
    X = lambda f: x + f * w
    Y = lambda f: y + f * h
    d = (f'M{X(.16):g},{Y(1):g} C{X(-.04):g},{Y(1):g} {X(-.04):g},{Y(.42):g} {X(.17):g},{Y(.42):g} '
         f'C{X(.17):g},{Y(.02):g} {X(.47):g},{Y(-.04):g} {X(.56):g},{Y(.18):g} '
         f'C{X(.66):g},{Y(.0):g} {X(.94):g},{Y(.08):g} {X(.86):g},{Y(.42):g} '
         f'C{X(1.05):g},{Y(.44):g} {X(1.05):g},{Y(1):g} {X(.85):g},{Y(1):g} Z')
    body = f'<path d="{d}" fill="#f0f9ff" stroke="#0284c7" stroke-width="1.5"/>'
    return _g('cdn', x, y, w, h, body + _text(x, y, w, h, title, sub, dy=4))

STORAGE_KINDS = ('db', 'cache', 'mq', 'obj')

if __name__ == '__main__':
    # CLI: python shapes.py <kind> x y w h "title" ["sub"]  -> prints the snippet
    import sys
    k, x, y, w, h = sys.argv[1], *map(float, sys.argv[2:6])
    t = sys.argv[6]; s = sys.argv[7] if len(sys.argv) > 7 else None
    print(globals()[k](x, y, w, h, t, s))
