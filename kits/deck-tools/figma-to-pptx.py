#!/usr/bin/env python3
"""Rebuild a deck exported from Figma (one PDF per page) as an editable 16:9 pptx.

Per page: background = the page rendered with its text glyphs removed (cards, images and
gradients kept); text = editable text boxes at the original positions, colours sampled from
the render, bold inferred from ink density, letter casing fixed from OCR when the PDF's text
layer disagrees with what is drawn. Run with --help for options; see README.
"""
import argparse, glob, os, shlex, shutil, tempfile
import subprocess, re, io, statistics as st, sys, difflib
try:
    import pymupdf
    from PIL import Image, ImageChops
    from pptx import Presentation
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.oxml.ns import qn
    MISSING = None
except ImportError as e:   # reported after --help is handled
    MISSING = e

SLIDE_W_PT = 960       # 16:9 slide, 13.333in
EMU = 12700
DPI = 144              # 2x render for sampling
FONT = 'Arial'         # set with --font to the deck's typeface (must be installed where it is opened)
OCR_CMD = None         # argv list; prints "x0<TAB>y0<TAB>x1<TAB>y1<TAB>text" per line, normalised, top-left origin

CHARMAP = {'\u2122': '\u2192', '\x14': '\u2014', '\x13': '\u2013', '\u02c7': '\u2019'}
def fixchars(s): return ''.join(CHARMAP.get(c, c) for c in s)
def letters(s): return re.sub(r'[^A-Za-z0-9]', '', s)
def norm(s): return letters(s).lower().replace('l', 'i')

def recase(src, ocr):
    """Apply OCR's letter casing onto src when they are the same letters."""
    if norm(src) != norm(ocr) or not letters(src): return src
    it = iter(c for c in ocr if c.isalnum())
    out = []
    for c in src:
        if c.isalnum():
            o = next(it)
            out.append(c if (o in 'lI' or c in 'lI') else o)
        else: out.append(c)
    return ''.join(out)

def ocr_lines(png):
    if not OCR_CMD: return []
    out = subprocess.run(OCR_CMD + [png], capture_output=True, text=True).stdout
    res = []
    for ln in out.splitlines():
        a = ln.split('\t', 4)
        if len(a) == 5: res.append((tuple(map(float, a[:4])), a[4]))
    return res

def best_ocr(span_bbox, W, H, ocr):
    x0, y0, x1, y1 = span_bbox[0]/W, span_bbox[1]/H, span_bbox[2]/W, span_bbox[3]/H
    cy = (y0+y1)/2; cands = []
    for (a, b, c, d), s in ocr:
        if b - 0.01 <= cy <= d + 0.01 and min(x1, c) - max(x0, a) > 0:
            cands.append(s)
    return cands

def sample_color(orig, bg, box):
    o = orig.crop(box); b = bg.crop(box)
    diff = ImageChops.difference(o, b).convert('L')
    px = [p for p, d in zip(o.getdata(), diff.getdata()) if d > 60]
    if not px: return (255, 255, 255), 0.0
    # brightest-ish half of the ink pixels = fill colour (edges are blended with bg)
    px.sort(key=lambda p: -abs(p[0]-b.getpixel((0, 0))[0]) - abs(p[2]-b.getpixel((0, 0))[2]))
    core = px[:max(1, len(px)//3)]
    col = tuple(int(st.median(c[i] for c in core)) for i in range(3))
    return col, len(px) / max(1, o.size[0]*o.size[1])

def main(files, out, work):
    prs = Presentation(); prs.slide_width = Emu(12192000); prs.slide_height = Emu(6858000)
    report = []
    for idx, path in enumerate(files, 1):
        name = os.path.basename(path)
        doc = pymupdf.open(path); page = doc[0]; W, H = page.rect.width, page.rect.height
        SCALE = SLIDE_W_PT / W   # e.g. 1920pt page -> 960pt slide = 0.5
        orig_pix = page.get_pixmap(dpi=DPI); orig = Image.open(io.BytesIO(orig_pix.tobytes('png'))).convert('RGB')
        orig_png = os.path.join(work, f'orig_{idx:02d}.png'); orig.save(orig_png)
        ocr = ocr_lines(orig_png)
        d = page.get_text('dict')
        lines = []
        for b in d['blocks']:
            if b['type'] != 0: continue
            for l in b['lines']:
                sp = [s for s in l['spans'] if s['text'].strip()]
                if sp: lines.append(sp)
        def lbox(sp): return (min(s_['bbox'][0] for s_ in sp), min(s_['bbox'][1] for s_ in sp),
                              max(s_['bbox'][2] for s_ in sp), max(s_['bbox'][3] for s_ in sp))
        auth = []   # (rect, text, size)
        for (a, b_, c, d_), otext in ocr:
            R = (a*W, b_*H, c*W, d_*H); NO = norm(otext)
            if len(NO) < 4: continue
            hits = [sp for sp in lines if (lambda L: L[1] <= (R[1]+R[3])/2 <= L[3] and min(L[2], R[2]) - max(L[0], R[0]) > 0)(lbox(sp))]
            got = sum(len(norm(''.join(s_['text'] for s_ in sp))) for sp in hits
                      if norm(''.join(s_['text'] for s_ in sp)) and norm(''.join(s_['text'] for s_ in sp)) in NO)
            if hits and got / len(NO) < 0.7:   # no hits = text inside a logo/screenshot: leave it in the image
                size = max([max(s_['size'] for s_ in sp) for sp in hits] or [(R[3]-R[1])*0.8])
                ot = re.sub(r'\bAl\b', 'AI', otext)
                if any('\u2122' in s_['text'] for sp in hits for s_ in sp):   # hidden layer had an arrow here
                    ot = re.sub(r'(^|\s)[-\u2013\u203a>]+(?=\s)', lambda m_: m_.group(1) + '\u2192', ot)
                auth.append((R, ot, size))
                for sp in hits:
                    if sp in lines: lines.remove(sp)
        for R, _, size in auth:
            page.add_redact_annot(pymupdf.Rect(R) + (-0.3*size, -0.25*size, 0.3*size, 0.25*size))
        for sp in lines:
            sz = max(s_['size'] for s_ in sp)
            r_ = pymupdf.Rect(min(s_['bbox'][0] for s_ in sp), min(s_['bbox'][1] for s_ in sp),
                              max(s_['bbox'][2] for s_ in sp), max(s_['bbox'][3] for s_ in sp))
            page.add_redact_annot(r_ + (-0.3*sz, -0.2*sz, 0.3*sz, 0.2*sz))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                              graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                              text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        bg = Image.open(io.BytesIO(page.get_pixmap(dpi=DPI).tobytes('png'))).convert('RGB')
        bg_jpg = os.path.join(work, f'bg_{idx:02d}.jpg'); bg.save(bg_jpg, quality=90)
        k = DPI/72
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(bg_jpg, 0, 0, prs.slide_width, prs.slide_height)
        recased = 0
        used = {}
        for R, otext, size in auth:
            tb = slide.shapes.add_textbox(Emu(int(R[0]*SCALE*EMU)), Emu(int(R[1]*SCALE*EMU)),
                                          Emu(int((R[2]-R[0])*SCALE*EMU*1.12)+EMU*4), Emu(int((R[3]-R[1])*SCALE*EMU)))
            tf = tb.text_frame; tf.word_wrap = False; tf.auto_size = MSO_AUTO_SIZE.NONE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            col, dens = sample_color(orig, bg, tuple(int(v*k) for v in R))
            r = tf.paragraphs[0].add_run(); r.text = otext
            f = r.font; f.name = FONT; f.size = Pt(round(size*SCALE, 1)); f.color.rgb = RGBColor(*col); f.bold = dens > 0.205
        recased += len(auth)
        for sp in lines:
            # merge spans into segments: tiny gaps = same word run; real gaps = new segment + a space
            segs = []
            for sp_ in sp:
                t = fixchars(sp_['text'])
                if segs and sp_['bbox'][0] - segs[-1]['x1'] < 0.25 * sp_['size']:
                    segs[-1]['text'] += t; segs[-1]['x1'] = sp_['bbox'][2]
                    segs[-1]['y0'] = min(segs[-1]['y0'], sp_['bbox'][1]); segs[-1]['y1'] = max(segs[-1]['y1'], sp_['bbox'][3])
                else:
                    if segs and not segs[-1]['text'].endswith(' ') and not t.startswith(' '): t = ' ' + t
                    segs.append(dict(text=t, x0=sp_['bbox'][0], x1=sp_['bbox'][2], y0=sp_['bbox'][1], y1=sp_['bbox'][3], size=sp_['size']))
            x0 = min(g['x0'] for g in segs); y0 = min(g['y0'] for g in segs)  # recomputed after trim below
            x1 = max(g['x1'] for g in segs); y1 = max(g['y1'] for g in segs)
            tb = slide.shapes.add_textbox(Emu(int(x0*SCALE*EMU)), Emu(int(y0*SCALE*EMU)),
                                          Emu(int((x1-x0)*SCALE*EMU*1.12)+EMU*4), Emu(int((y1-y0)*SCALE*EMU)))
            tf = tb.text_frame; tf.word_wrap = False; tf.auto_size = MSO_AUTO_SIZE.NONE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            cands = best_ocr((x0, y0, x1, y1), W, H, ocr)
            full = norm(''.join(g['text'] for g in segs))
            replaced = None
            for c in cands:
                NC = norm(c); u = used.setdefault(c, [])
                pos = NC.find(full)
                if full and pos >= 0 and not any(a < pos+len(full) and pos < b for a, b in u):
                    u.append((pos, pos+len(full))); break
                # leading letters duplicated from an earlier fragment of the same OCR line -> trim them
                ends = [b for a, b in u]
                trimmed = False
                for e in ends:
                    for kk in range(min(len(full), 40), 0, -1):
                        if NC[e-kk:e] == full[:kk] and NC.find(full[kk:], e) == e and full[kk:]:
                            g0 = segs[0]; n = 0; t = g0['text']; i = 0
                            while i < len(t) and n < kk:
                                if t[i].isalnum(): n += 1
                                i += 1
                            if n == kk and t:
                                g0['x0'] += (g0['x1'] - g0['x0']) * i / len(t); g0['text'] = t[i:].lstrip()
                            u.append((e, e+len(full)-kk)); trimmed = True; break
                    if trimmed: break
                if trimmed: break
                if not u and full and difflib.SequenceMatcher(None, full, NC).ratio() > 0.75:
                    replaced = c; u.append((0, len(NC))); break
            else:
                if cands and full and all(norm(c).find(full) < 0 for c in cands):
                    # whole line is a duplicate of an OCR line already fully used -> drop it
                    if any(used.get(c) and difflib.SequenceMatcher(None, full, norm(c)).find_longest_match(0, len(full), 0, len(norm(c))).size >= 0.8*len(full) for c in cands):
                        tb._element.getparent().remove(tb._element); continue
            tb.left = Emu(int(min(g['x0'] for g in segs)*SCALE*EMU))
            if replaced is not None:
                segs = [dict(segs[0], text=replaced, x1=max(g['x1'] for g in segs))]
            for g in segs:
                text = g['text']
                spaced = re.fullmatch(r'\s*(\S ){2,}\S\s*', text) is not None
                for c in cands:
                    L = norm(text); NC = norm(c); pos = NC.find(L)
                    if L and pos >= 0:
                        if spaced:
                            # take OCR's own spelling (proper word spacing) for letter-spaced labels
                            al = [i for i, ch in enumerate(c) if ch.isalnum()]
                            text = (' ' if text.startswith(' ') else '') + c[al[pos]:al[pos+len(L)-1]+1]
                        else:
                            alnum = [ch for ch in c if ch.isalnum()][pos:pos+len(L)]
                            text = recase(text, ''.join(alnum))
                        if text != g['text']: recased += 1
                        break
                box = tuple(int(v*k) for v in (g['x0'], g['y0'], g['x1'], g['y1']))
                col, dens = sample_color(orig, bg, box)
                r = p.add_run(); r.text = text
                f = r.font; f.name = FONT; f.size = Pt(round(g['size']*SCALE, 1)); f.color.rgb = RGBColor(*col)
                f.bold = dens > 0.205
                if g['size'] >= 48 and g['x1'] - g['x0'] > 4 * g['size']:
                    w = box[2] - box[0]
                    cl, _ = sample_color(orig, bg, (box[0], box[1], box[0] + w//5, box[3]))
                    cm, _ = sample_color(orig, bg, (box[0] + 2*w//5, box[1], box[0] + 3*w//5, box[3]))
                    cr, _ = sample_color(orig, bg, (box[2] - w//5, box[1], box[2], box[3]))
                    if sum(abs(a-b) for a, b in zip(cl, cr)) > 120:
                        rPr = r._r.get_or_add_rPr()
                        for e in rPr.findall(qn('a:solidFill')): rPr.remove(e)
                        gf = rPr.makeelement(qn('a:gradFill'), {'rotWithShape': '1'})
                        gl = gf.makeelement(qn('a:gsLst'), {})
                        for pos_, cc in ((0, cl), (50000, cm), (100000, cr)):
                            gs = gl.makeelement(qn('a:gs'), {'pos': str(pos_)})
                            sc = gs.makeelement(qn('a:srgbClr'), {'val': '%02X%02X%02X' % cc}); gs.append(sc); gl.append(gs)
                        gf.append(gl); gf.append(gf.makeelement(qn('a:lin'), {'ang': '0', 'scaled': '1'}))
                        rPr.insert(0, gf)
        report.append((idx, name, len(lines), recased))
    prs.save(out)
    print('slide\tfile\ttext_lines\trecased')
    for r in report: print(*r, sep='\t')
    print('WROTE', out)

def natural_key(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', os.path.splitext(os.path.basename(p))[0])]

def default_ocr_cmd():
    here = os.path.dirname(os.path.abspath(__file__))
    helper = os.path.join(here, 'ocr.mac.swift')
    if sys.platform == 'darwin' and shutil.which('swift') and os.path.exists(helper):
        return ['swift', helper]
    return None

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Rebuild a Figma PDF export (one PDF per page) as an editable pptx.')
    ap.add_argument('src', help='directory of page PDFs, or a single multi-file glob in quotes')
    ap.add_argument('output', help='output .pptx path')
    ap.add_argument('--order', help='text file listing the PDF file names in slide order, one per line '
                                    '(default: all *.pdf in src, natural sort: "x.pdf, x-1.pdf, x-2.pdf, ... x-10.pdf")')
    ap.add_argument('--font', default=FONT, help='font family for the text boxes (default %(default)s)')
    ap.add_argument('--ocr-cmd', help='OCR command (default on macOS: swift ocr.mac.swift); gets the PNG path appended')
    ap.add_argument('--no-ocr', action='store_true', help='skip OCR: use the PDF text layer only (any platform)')
    ap.add_argument('--work-dir', help='keep intermediate renders here (default: a temp dir, deleted afterwards)')
    a = ap.parse_args()
    if MISSING:
        sys.exit(f'missing dependency ({MISSING}); run: pip install pymupdf pillow python-pptx')
    FONT = a.font
    OCR_CMD = None if a.no_ocr else (shlex.split(a.ocr_cmd) if a.ocr_cmd else default_ocr_cmd())
    if a.order:
        base = a.src if os.path.isdir(a.src) else os.path.dirname(a.src)
        files = [os.path.join(base, l.strip()) for l in open(a.order, encoding='utf-8') if l.strip()]
    elif os.path.isdir(a.src):
        files = sorted(glob.glob(os.path.join(a.src, '*.pdf')), key=natural_key)
    else:
        files = sorted(glob.glob(a.src), key=natural_key)
    missing = [f for f in files if not os.path.exists(f)]
    if not files or missing:
        sys.exit('no input PDFs' if not files else 'missing: ' + ', '.join(missing))
    if not OCR_CMD:
        print('note: OCR disabled; casing and hidden-layer fixes are skipped', file=sys.stderr)
    work = a.work_dir or tempfile.mkdtemp(prefix='figma2pptx-')
    os.makedirs(work, exist_ok=True)
    try:
        main(files, a.output, work)
    finally:
        if not a.work_dir: shutil.rmtree(work, ignore_errors=True)
