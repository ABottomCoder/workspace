#!/usr/bin/env python3
"""Render a deck written in markdown to an editable 16:9 PPTX with speaker notes.

Visual quality comes from a type scale, generous margins, a restrained palette and slide
templates that *draw* the described layout instead of dumping bullets. Default font is
Arial: a deck opened on someone else's machine must use an installed font, or PowerPoint
substitutes it and the layout shifts.

Input format (see README):  ### <id> — <title>  followed by  - **On-slide:**  - **Speaker notes:**
  and optional  - **Visual:**  - **Template:**  - **Kicker:**  - **Footer:**
"""
import argparse
import json
import os
import re
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


def rgb(h):
    h = h.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# --- defaults (override any key with --config deck.json) --------------------
DEFAULTS = {
    'font': 'Arial',            # use a font installed on every machine that opens the deck
    'palette': {
        'ink': '#1A1F2E', 'muted': '#6B7284', 'accent': '#2563EB', 'violet': '#7B5BF5',
        'paper': '#FFFFFF', 'wash': '#F6F7FA', 'green': '#1B9E60', 'amber': '#C98A14',
        'red': '#C83A3A', 'hair': '#E2E5EB',
        'brand_ink': '#0B1020',  # dark ground of the title/closing slides
        'highlight': '#E8F1FF',  # fill of highlighted rows
    },
    'gradient': ['#14B8A6', '#2563EB', '#7C3AED'],
    'logo': None,               # path to a logo image drawn on brand_ink (title + closing)
    'templates': {},            # slide id -> template, for decks without "Template:" lines
    'kickers': {},              # template -> small caps label above the title
    'highlight_terms': ['Q&A', 'Questions'],
    'beat_labels': ['Problem:', 'How:', 'Result:'],
    'tags': [],                 # [{"pattern": "\\[roadmap\\]", "label": "Roadmap", "color": "violet"}]
    'closing_placeholder': 'QR / link',
    'replace_em_dash': False,   # True: " — " becomes ": " in all rendered text
}
DEFAULT_KICKERS = {
    'agenda': 'Agenda', 'traffic': 'Rules', 'beats': 'Use case', 'statement': 'Concept',
    'twocol': 'Concept', 'scorecard': 'Checklist', 'activity': 'Activity', 'closing': 'Wrap up',
    'flow': 'Process', 'compare': 'Before and after',
}
CFG = {}


def configure(cfg):
    """Load config into module globals used by the drawing code."""
    global INK, MUTED, ACCENT, VIOLET, PAPER, WASH, GREEN, AMBER, RED, HAIR, BRAND_INK, HILITE
    global GRADIENT, FONT, LOGO, CFG
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in cfg.items() if k != 'palette'})
    merged['palette'] = dict(DEFAULTS['palette'], **cfg.get('palette', {}))
    merged['kickers'] = dict(DEFAULT_KICKERS, **cfg.get('kickers', {}))
    CFG = merged
    pal = {k: rgb(v) for k, v in merged['palette'].items()}
    INK, MUTED, ACCENT, VIOLET = pal['ink'], pal['muted'], pal['accent'], pal['violet']
    PAPER, WASH, GREEN, AMBER = pal['paper'], pal['wash'], pal['green'], pal['amber']
    RED, HAIR, BRAND_INK, HILITE = pal['red'], pal['hair'], pal['brand_ink'], pal['highlight']
    GRADIENT = tuple(rgb(c) for c in merged['gradient'])
    FONT = merged['font']
    LOGO = merged['logo']


configure({})

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)


def kicker(tpl):
    return CFG['kickers'].get(tpl)


def hot(text):
    return any(t in text for t in CFG['highlight_terms'])


# --- markdown parsing ------------------------------------------------------
def parse(path):
    slides, cur = [], None
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^### (\S+)\s+[—-]\s+(.*)$', line.strip())
        if m:
            cur = {'id': m.group(1), 'title': m.group(2), 'onslide': '', 'notes': '', 'visual': '',
                   'template': '', 'kicker': '', 'footer': ''}
            slides.append(cur)
            continue
        if cur is None:
            continue
        for key, label in (('onslide', 'On-slide'), ('notes', 'Speaker notes'), ('visual', 'Visual'),
                           ('template', 'Template'), ('kicker', 'Kicker'), ('footer', 'Footer')):
            m = re.match(r'^- \*\*%s:\*\*\s*(.*)$' % label, line.strip())
            if m:
                cur[key] = m.group(1)
    return slides


def depunct(s):
    """Optionally replace em dashes (config `replace_em_dash`).

    Doing it at render time, not by hand in the .pptx, keeps the rule alive across
    re-renders from the markdown.
    """
    if not CFG.get('replace_em_dash'):
        return s
    return s.replace(' — ', ': ').replace('—', ': ')


def clean(s):
    """Strip markdown emphasis; keep the text."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'\*(.+?)\*', r'\1', s)
    return s.replace('&', '&').strip()


CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩'


def chips(onslide):
    """Split on-slide text into display chips.

    The decks use three separators: a middot, a pipe, and circled numerals. The numerals
    are both a separator *and* a bullet marker, so they are stripped after splitting —
    otherwise a numbered template renders "① ① Is this safe?".
    """
    parts = re.split(r'\s+·\s+|\s+\|\s+|(?=[%s])' % CIRCLED, clean(onslide))
    out = []
    for p in parts:
        p = p.strip().lstrip(CIRCLED).strip(' .·')
        if p:
            out.append(p)
    return out


def decompose(onslide):
    """Split on-slide text into (lead sentence, chips, closing quote).

    Without this a line like "One team. Ten jobs. Sales · support · …" gets chopped
    mid-sentence, and a trailing quote ends up glued to the last bullet.
    """
    raw = clean(onslide)
    quote = None
    m = re.search(r'("[^"]{20,}"|“[^”]{20,}”)\s*$', raw)
    if m:
        quote = m.group(1)
        raw = raw[:m.start()].rstrip(' .·')
    items = chips(raw)
    lead = None
    if items and re.search(r'\.\s', items[0]) and len(items) > 1:
        head, sep, tail = items[0].rpartition('. ')
        if sep and len(head) > 8:
            lead, items[0] = head + '.', tail
    foot = None
    if items and len(items[-1]) > 70 and '. ' in items[-1]:
        head, _, tail = items[-1].partition('. ')
        if len(tail) > 25:
            items[-1], foot = head, tail
    return lead, items, quote, foot


# --- drawing helpers -------------------------------------------------------
def textbox(slide, x, y, w, h, text, size, *, bold=False, color=None, align=PP_ALIGN.LEFT,
            spacing=1.15, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = spacing
    r = p.add_run()
    r.text = depunct(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color if color is not None else INK
    r.font.name = FONT
    return box


def gradient_bar(slide, x, y, w, h, stops=None):
    """A multi-stop colour sweep (config `gradient`), drawn as abutting blocks.

    python-pptx can set a two-stop gradient, not a four-stop one, so the sweep is
    built from one rectangle per adjacent pair. At this size the joins are invisible
    and it survives being opened in PowerPoint, which a real multi-stop fill would
    not without hand-written XML.
    """
    stops = stops or GRADIENT
    n = len(stops) - 1
    seg = int(w / n)
    for i in range(n):
        r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x + seg * i, y,
                                   seg + (int(w) - seg * n if i == n - 1 else 0), h)
        f = r.fill
        f.gradient()
        f.gradient_angle = 0
        f.gradient_stops[0].color.rgb = stops[i]
        f.gradient_stops[0].position = 0.0
        f.gradient_stops[1].color.rgb = stops[i + 1]
        f.gradient_stops[1].position = 1.0
        r.line.fill.background()
        r.shadow.inherit = False


def panel(slide, x, y, w, h, fill=None, line=None, radius=True):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill if fill is not None else WASH
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    if radius:
        try:
            shp.adjustments[0] = 0.06
        except Exception:
            pass
    return shp


def slide_base(prs, title=None, kicker=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])          # blank
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = PAPER
    if kicker:
        textbox(s, MARGIN, Inches(0.55), W - 2 * MARGIN, Inches(0.3),
                kicker.upper(), 11, bold=True, color=ACCENT)
    if title:
        # Two-line titles used to run through the accent rule; size down instead.
        tsize = 30 if len(title) <= 44 else (26 if len(title) <= 64 else 23)
        textbox(s, MARGIN, Inches(0.88), W - 2 * MARGIN, Inches(0.95),
                title, tsize, bold=True, color=INK)
        rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, Inches(1.78), Inches(0.9), Pt(3))
        rule.fill.solid(); rule.fill.fore_color.rgb = ACCENT
        rule.line.fill.background(); rule.shadow.inherit = False
    return s


def notes(slide, text):
    if text:
        slide.notes_slide.notes_text_frame.text = depunct(clean(text))


# --- templates -------------------------------------------------------------
def t_title(prs, d):
    """Brand slide: dark ground, optional logo, colour sweep.

    Only the title and the closing slide go dark. Content slides stay light on
    purpose: projected in bright rooms or printed, a dark ground loses contrast.
    """
    s = slide_base(prs)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid(); bg.fill.fore_color.rgb = BRAND_INK
    bg.line.fill.background(); bg.shadow.inherit = False
    gradient_bar(s, 0, 0, W, Inches(0.22))
    if LOGO and os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, MARGIN, Inches(0.95), height=Inches(0.62))
    parts = chips(d['onslide'])
    textbox(s, MARGIN, Inches(2.5), W - 2 * MARGIN, Inches(1.4),
            parts[0] if parts else d['title'], 46, bold=True, color=PAPER)
    if len(parts) > 1:
        textbox(s, MARGIN, Inches(4.0), W - 2 * MARGIN, Inches(0.9),
                '   ·   '.join(parts[1:]), 16, color=RGBColor(0xB8, 0xC4, 0xD9))
    gradient_bar(s, MARGIN, Inches(5.55), Inches(2.4), Pt(4))
    return s


def t_agenda(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('agenda'))
    items = [c for c in chips(d['onslide'])]
    y = Inches(2.15)
    ch = Inches(0.62)
    gap = Inches(0.14)
    for i, it in enumerate(items[:7]):
        hi = hot(it)
        p = panel(s, MARGIN, y, W - 2 * MARGIN, ch, HILITE if hi else WASH)
        num = s.shapes.add_shape(MSO_SHAPE.OVAL, MARGIN + Inches(0.18),
                                 y + Inches(0.13), Inches(0.36), Inches(0.36))
        num.fill.solid(); num.fill.fore_color.rgb = ACCENT if hi else INK
        num.line.fill.background(); num.shadow.inherit = False
        tf = num.text_frame; tf.word_wrap = False
        r = tf.paragraphs[0].add_run(); r.text = str(i + 1)
        r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = PAPER; r.font.name = FONT
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        textbox(s, MARGIN + Inches(0.75), y + Inches(0.11), W - 2 * MARGIN - Inches(1.0),
                Inches(0.45), it, 15, bold=hi, color=INK)
        y += ch + gap
    return s


def t_traffic(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('traffic'))
    raw = clean(d['onslide'])
    cols = []
    for mark, colour, label in (('🟢', GREEN, 'Safe'), ('🟡', AMBER, 'Do, then check'), ('🔴', RED, 'Never')):
        m = re.search(re.escape(mark) + r'(.*?)(?=🟢|🟡|🔴|$)', raw, re.S)
        body = m.group(1) if m else ''
        body = re.sub(r'^\s*[A-Za-z ,]*—\s*', '', body.strip())
        cols.append((colour, label, [b.strip(' .') for b in body.split('·') if b.strip(' .')]))
    cw = (W - 2 * MARGIN - Inches(0.5)) / 3
    x = MARGIN
    for colour, label, items in cols:
        panel(s, x, Inches(2.15), cw, Inches(4.3), WASH)
        head = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(2.15), cw, Inches(0.62))
        head.fill.solid(); head.fill.fore_color.rgb = colour
        head.line.fill.background(); head.shadow.inherit = False
        tf = head.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = depunct(label)
        r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = PAPER; r.font.name = FONT
        y = Inches(3.0)
        for it in items[:6]:
            textbox(s, x + Inches(0.22), y, cw - Inches(0.44), Inches(0.5), '•  ' + it, 12, color=INK)
            y += Inches(0.55)
        x += cw + Inches(0.25)
    return s


def t_beats(prs, d):
    """Three-beat slides; labels from config `beat_labels` (e.g. Problem: / How: / Result:)."""
    s = slide_base(prs, d['title'], d['kicker'] or kicker('beats'))
    raw = clean(d['onslide'])
    beats = []
    labels = CFG['beat_labels']
    stop = '|'.join(re.escape(x) for x in labels)
    for label in labels:
        m = re.search(re.escape(label) + r'\s*(.*?)(?=%s|$)' % stop, raw, re.S)
        if m:
            beats.append((label.rstrip(':'), m.group(1).strip(' .·')))
    if len(beats) < len(labels) or len(beats) < 2:
        return t_bullets(prs, d)
    n = len(beats)
    cw = (W - 2 * MARGIN - Inches(0.35) * (n - 1)) / n
    x = MARGIN
    for i, (label, body) in enumerate(beats):
        panel(s, x, Inches(2.2), cw, Inches(3.4), WASH)
        textbox(s, x + Inches(0.25), Inches(2.42), cw - Inches(0.5), Inches(0.35),
                label.upper(), 11, bold=True, color=ACCENT)
        textbox(s, x + Inches(0.25), Inches(2.85), cw - Inches(0.5), Inches(2.6),
                body, 14, color=INK)
        if i < len(beats) - 1:
            arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + cw + Inches(0.06),
                                     Inches(3.75), Inches(0.23), Inches(0.28))
            arr.fill.solid(); arr.fill.fore_color.rgb = HAIR
            arr.line.fill.background(); arr.shadow.inherit = False
        x += cw + Inches(0.35)
    if d['footer']:
        textbox(s, MARGIN, Inches(5.85), W - 2 * MARGIN, Inches(0.6), clean(d['footer']), 13, color=MUTED)
    tags(s, raw)
    return s


def tags(s, raw):
    """Corner chips for configured patterns, e.g. a "[roadmap]" marker in the on-slide text."""
    y = Inches(6.5)
    for t in CFG['tags']:
        if not re.search(t['pattern'], raw):
            continue
        colour = rgb(CFG['palette'].get(t.get('color', 'amber'), t.get('color', '#C98A14')))
        chip = panel(s, W - MARGIN - Inches(3.4), y, Inches(3.4), Inches(0.42), WASH, line=colour)
        tf = chip.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = depunct(t['label'])
        r.font.size = Pt(10); r.font.bold = True; r.font.color.rgb = colour; r.font.name = FONT
        y -= Inches(0.5)


def t_statement(prs, d):
    s = slide_base(prs, None, d['kicker'] or kicker('statement'))
    body = clean(d['onslide'])
    textbox(s, MARGIN, Inches(2.2), W - 2 * MARGIN, Inches(2.4), d['title'], 34, bold=True)
    textbox(s, MARGIN, Inches(3.5), W - 2 * MARGIN, Inches(2.6), body, 18, color=INK, spacing=1.35)
    return s


def t_twocol(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('twocol'))
    items = chips(d['onslide'])
    half = (len(items) + 1) // 2
    cw = (W - 2 * MARGIN - Inches(0.4)) / 2
    for col, group in enumerate((items[:half], items[half:])):
        x = MARGIN + col * (cw + Inches(0.4))
        panel(s, x, Inches(2.15), cw, Inches(4.2), WASH)
        y = Inches(2.42)
        for it in group[:7]:
            textbox(s, x + Inches(0.28), y, cw - Inches(0.56), Inches(0.7), '•  ' + it, 14)
            y += Inches(0.62)
    return s


def t_scorecard(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('scorecard'))
    raw = clean(d['onslide'])
    raw = re.sub(r'^[^:]{0,24}:\s*', '', raw)          # drop a lead-in like "Ask every vendor:"
    rows = [q.strip() + '?' for q in raw.split('?') if q.strip()]
    y = Inches(2.2)
    for i, r_ in enumerate(rows[:6]):
        panel(s, MARGIN, y, W - 2 * MARGIN, Inches(0.66), WASH if i % 2 == 0 else PAPER,
              line=HAIR, radius=False)
        textbox(s, MARGIN + Inches(0.3), y + Inches(0.14), W - 2 * MARGIN - Inches(1.4),
                Inches(0.45), r_, 15)
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, W - MARGIN - Inches(0.85),
                                 y + Inches(0.16), Inches(0.55), Inches(0.34))
        box.fill.solid(); box.fill.fore_color.rgb = PAPER
        box.line.color.rgb = HAIR; box.shadow.inherit = False
        y += Inches(0.72)
    return s


def t_activity(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('activity'))
    panel(s, MARGIN, Inches(2.2), W - 2 * MARGIN, Inches(2.5), HILITE)
    textbox(s, MARGIN + Inches(0.5), Inches(2.6), W - 2 * MARGIN - Inches(1.0), Inches(1.8),
            clean(d['onslide']), 20, bold=True, color=INK, spacing=1.3)
    textbox(s, MARGIN, Inches(5.2), W - 2 * MARGIN, Inches(1.2),
            clean(d['footer'] or d['visual']), 13, color=MUTED)
    return s


def t_closing(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('closing'))
    items = chips(d['onslide'])
    y = Inches(2.2)
    for it in items[:6]:
        hi = hot(it)
        # Grow the row when the line wraps: at 15pt in this column ~78 characters
        # fit on a line, and a fixed 0.66" panel let two-line rows spill out of it.
        rows = max(1, -(-len(it) // 78))
        ch = Inches(0.30 + 0.26 * rows)
        panel(s, MARGIN, y, W - 2 * MARGIN - Inches(3.2), ch,
              HILITE if hi else WASH)
        textbox(s, MARGIN + Inches(0.3), y + Inches(0.13), W - 2 * MARGIN - Inches(3.8),
                ch - Inches(0.2), it, 15, bold=hi)
        y += ch + Inches(0.12)
    ph = panel(s, W - MARGIN - Inches(2.8), Inches(2.2), Inches(2.8), Inches(2.8), WASH, line=HAIR)
    textbox(s, W - MARGIN - Inches(2.8), Inches(3.4), Inches(2.8), Inches(0.5),
            CFG['closing_placeholder'], 13, color=MUTED, align=PP_ALIGN.CENTER)
    foot = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, H - Inches(0.95), W, Inches(0.95))
    foot.fill.solid(); foot.fill.fore_color.rgb = BRAND_INK
    foot.line.fill.background(); foot.shadow.inherit = False
    gradient_bar(s, 0, H - Inches(0.95), W, Pt(3))
    if LOGO and os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, MARGIN, H - Inches(0.72), height=Inches(0.46))
    return s


def t_bullets(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or None)
    lead, items, quote, foot = decompose(d['onslide'])
    top, bottom = Inches(2.15), Inches(6.3)

    y = top
    if lead:
        textbox(s, MARGIN, y, W - 2 * MARGIN, Inches(0.9), lead, 20, bold=True, spacing=1.25)
        y += Inches(0.8)

    if not items:
        textbox(s, MARGIN, y, W - 2 * MARGIN, bottom - y, clean(d['onslide']), 20, spacing=1.4)
    else:
        # Size to the content: a four-item slide should not be set at the same size as a
        # twelve-item one, and the block is centred in the space left rather than hugging
        # the title with a field of white underneath it.
        n = len(items)
        cols = 2 if n > 5 else 1
        size = 20 if n <= 3 else (17 if n <= 5 else 14)
        row = Inches(0.95) if n <= 3 else (Inches(0.78) if n <= 5 else Inches(0.64))
        per = (n + cols - 1) // cols
        block = row * per
        avail = bottom - y
        if block < avail:
            y += int((avail - block) / 2)
        cw = (W - 2 * MARGIN - Inches(0.5)) / cols
        for c in range(cols):
            x = MARGIN + c * (cw + Inches(0.5))
            yy = y
            for it in items[c * per:(c + 1) * per]:
                dot = s.shapes.add_shape(MSO_SHAPE.OVAL, x, yy + Inches(0.15),
                                         Inches(0.12), Inches(0.12))
                dot.fill.solid(); dot.fill.fore_color.rgb = ACCENT
                dot.line.fill.background(); dot.shadow.inherit = False
                textbox(s, x + Inches(0.32), yy, cw - Inches(0.42), row, it, size, spacing=1.2)
                yy += row

    if quote or foot:
        textbox(s, MARGIN, Inches(6.35), W - 2 * MARGIN, Inches(0.6),
                quote or foot, 14, color=MUTED)
    return s


def t_flow(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('flow'))
    raw = clean(d['onslide'])
    steps = [x.strip(' .') for x in raw.split('→') if x.strip(' .')]
    tail = None
    if steps and '. ' in steps[-1]:
        steps[-1], _, tail = steps[-1].partition('. ')
    n = max(1, len(steps))
    gap = Inches(0.28)
    cw = (W - 2 * MARGIN - gap * (n - 1)) / n
    x = MARGIN
    for i, st in enumerate(steps):
        panel(s, x, Inches(2.6), cw, Inches(1.5), WASH)
        textbox(s, x + Inches(0.18), Inches(2.95), cw - Inches(0.36), Inches(1.0),
                st, 16, bold=True, align=PP_ALIGN.CENTER)
        if i < n - 1:
            arr = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + cw + Inches(0.04),
                                     Inches(3.2), Inches(0.2), Inches(0.28))
            arr.fill.solid(); arr.fill.fore_color.rgb = ACCENT
            arr.line.fill.background(); arr.shadow.inherit = False
        x += cw + gap
    if tail:
        textbox(s, MARGIN, Inches(4.6), W - 2 * MARGIN, Inches(0.6), tail, 15, color=MUTED)
    return s


def t_compare(prs, d):
    s = slide_base(prs, d['title'], d['kicker'] or kicker('compare'))
    raw = clean(d['onslide'])
    m = re.search(r'Without:(.*?)With:(.*)$', raw, re.S)
    if not m:
        return t_bullets(prs, d)
    cols = [('WITHOUT', m.group(1), MUTED, WASH), ('WITH', m.group(2), ACCENT, HILITE)]
    cw = (W - 2 * MARGIN - Inches(0.4)) / 2
    for i, (label, body, colour, fill) in enumerate(cols):
        x = MARGIN + i * (cw + Inches(0.4))
        panel(s, x, Inches(2.2), cw, Inches(3.7), fill)
        textbox(s, x + Inches(0.3), Inches(2.45), cw - Inches(0.6), Inches(0.4),
                label, 12, bold=True, color=colour)
        body = body.strip(' .·')
        y = Inches(2.95)
        for it in [b.strip(' .·') for b in re.split(r',|·', body) if b.strip(' .·')][:6]:
            textbox(s, x + Inches(0.3), y, cw - Inches(0.6), Inches(0.5), '•  ' + it, 14)
            y += Inches(0.5)
    if d['footer']:
        textbox(s, MARGIN, Inches(6.1), W - 2 * MARGIN, Inches(0.5),
                clean(d['footer']), 20, bold=True, align=PP_ALIGN.CENTER)
    return s


RENDER = {'flow': t_flow, 'compare': t_compare,'title': t_title, 'agenda': t_agenda, 'traffic': t_traffic, 'beats': t_beats,
          'statement': t_statement, 'twocol': t_twocol, 'scorecard': t_scorecard,
          'activity': t_activity, 'closing': t_closing, 'bullets': t_bullets}


def build(md_path, out_path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    slides = parse(md_path)
    for d in slides:
        tpl = (d['template'] or CFG['templates'].get(d['id']) or 'bullets').strip().lower()
        if tpl not in RENDER:
            raise SystemExit('slide %s: unknown template %r (known: %s)' % (d['id'], tpl, ', '.join(sorted(RENDER))))
        s = RENDER[tpl](prs, d)
        notes(s, d['notes'])
    prs.save(out_path)
    print('WROTE %s (%d slides)' % (out_path, len(slides)))


def main():
    ap = argparse.ArgumentParser(description='Render a deck markdown file to an editable 16:9 .pptx (see README for the format).')
    ap.add_argument('markdown', help='deck markdown file')
    ap.add_argument('output', help='output .pptx path')
    ap.add_argument('--config', help='JSON file overriding font, palette, gradient, logo, templates, kickers, ...')
    ap.add_argument('--font', help='font family (overrides config)')
    ap.add_argument('--logo', help='logo image for title/closing slides (overrides config)')
    a = ap.parse_args()
    cfg = {}
    if a.config:
        with open(a.config, encoding='utf-8') as f:
            cfg = json.load(f)
        if cfg.get('logo') and not os.path.isabs(cfg['logo']):
            cfg['logo'] = os.path.join(os.path.dirname(os.path.abspath(a.config)), cfg['logo'])
    if a.font:
        cfg['font'] = a.font
    if a.logo:
        cfg['logo'] = a.logo
    configure(cfg)
    build(a.markdown, a.output)


if __name__ == '__main__':
    main()
