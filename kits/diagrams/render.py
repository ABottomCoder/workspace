# usage: python render.py <file.svg> [scale]  -> writes <file>.png next to it (headless Chrome)
# Chrome: $CHROME if set, else the usual install location for the OS, else chrome/chromium on PATH.
import io, os, pathlib, re, shutil, subprocess, sys

def find_chrome():
    if os.environ.get('CHROME'):
        return os.environ['CHROME']
    if sys.platform == 'darwin':
        cands = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                 '/Applications/Chromium.app/Contents/MacOS/Chromium']
    elif sys.platform == 'win32':
        cands = [os.path.join(os.environ.get(v, ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
                 for v in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
    else:
        cands = []
    for c in cands:
        if c and os.path.exists(c):
            return c
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'chrome'):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit('render.py: Chrome not found; set CHROME to its executable')

src = os.path.abspath(sys.argv[1])
scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
svg = io.open(src, encoding='utf-8').read()
vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
w, h = int(float(vb.group(1)) * scale), int(float(vb.group(2)) * scale)
html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
        'body{margin:0;background:#fbfcfe;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}'
        f'svg{{display:block;width:{w}px;height:{h}px}}</style></head><body>{svg}</body></html>')
base = os.path.splitext(src)[0]
hp = base + '.render.html'
io.open(hp, 'w', encoding='utf-8').write(html)
png = base + '.png'
subprocess.run([find_chrome(), '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--screenshot={png}',
                f'--window-size={w},{h}', pathlib.Path(hp).as_uri()], capture_output=True)
print(png, os.path.exists(png))
