# deck-tools

Two scripts that produce **editable** PowerPoint files:

- `render_deck.py`: a deck written in markdown becomes a styled 16:9 `.pptx` with speaker notes.
  Templates draw the layout (agenda rows, flow arrows, three-beat columns, traffic-light rules,
  before/after, checklist, closing) instead of dumping bullets.
- `figma-to-pptx.py`: a Figma deck exported as one PDF per page becomes a `.pptx` where every
  text line is an editable text box over a text-free background render.

No brand assets ship with the kit. Fonts, palette, gradient and logo are parameters.

## Install

Python 3.9+.

```bash
pip install python-pptx                    # render_deck.py
pip install python-pptx pymupdf pillow     # figma-to-pptx.py
```

## render_deck.py

```bash
python3 render_deck.py deck.md out.pptx [--config deck.json] [--font Arial] [--logo logo.png]
python3 render_deck.py example.md /tmp/example.pptx --config deck.example.json   # try it
```

### Markdown format

Each slide is a `###` heading with an id and a title, then labelled bullet lines. Anything else is ignored.

```markdown
### 4 — A typical request
- **Template:** beats
- **Kicker:** Use case
- **On-slide:** Problem: customers wait two days · How: a shared inbox · Result: same-day answers
- **Speaker notes:** What the presenter says.
- **Visual:** Description used by the activity template.
- **Footer:** Optional line under the slide body.
```

- Heading: `### <id> — <title>` (em dash or hyphen). The id is any token (`1`, `S1.4`, `intro`).
- `On-slide:` is the slide text. Items split on ` · `, ` | ` or circled numerals (①②③).
- `Template:` (default `bullets`): `title`, `agenda`, `flow` (steps split on `→`), `beats`
  (sections start with the `beat_labels`), `traffic` (sections start with 🟢 / 🟡 / 🔴), `twocol`,
  `statement`, `scorecard` (questions split on `?`), `activity`, `compare` (`Without: … With: …`),
  `stats` (up to six `<figure>: <label>` tiles),
  `closing`, `bullets`.
- `Kicker:` overrides the small caps label above the title (per-template defaults in `kickers`).
- `**bold**` and `*italic*` markers are stripped.

See `example.md` for one slide per template.

### Config (`--config deck.json`)

All keys optional; see `deck.example.json`.

| Key | Meaning |
|---|---|
| `font` | font family for all text; pick one installed wherever the deck is opened |
| `palette` | hex colours: `ink`, `muted`, `accent`, `violet`, `paper`, `wash`, `green`, `amber`, `red`, `hair`, `brand_ink` (title/closing ground), `highlight` |
| `gradient` | list of hex stops for the colour sweep on title/closing slides |
| `logo` | image drawn on title and closing slides (relative to the config file); design it for the `brand_ink` ground |
| `templates` | `{slide id: template}` for decks without `Template:` lines |
| `kickers` | `{template: label}` |
| `highlight_terms` | agenda/closing rows containing any of these are highlighted |
| `beat_labels` | section labels for the `beats` template |
| `tags` | `[{pattern, label, color}]`: a corner chip when the on-slide text matches `pattern` (regex); `color` is a palette key or hex |
| `closing_placeholder` | text in the closing slide's QR/link box |
| `replace_em_dash` | `true` replaces em dashes with `: ` in rendered text |

## figma-to-pptx.py

```bash
python3 figma-to-pptx.py <dir-of-page-pdfs> out.pptx [--order order.txt] [--font Poppins] [--no-ocr]
```

- Input: export each Figma frame as its own PDF. Default order is a natural sort of `*.pdf` in
  the directory (`x.pdf, x-1.pdf, …, x-10.pdf`); `--order` takes a text file of file names, one per line.
- Slides are 16:9; each page is scaled to the slide width.
- `--font`: the deck's typeface (default Arial). It must be installed on the machine that opens the
  pptx, or PowerPoint substitutes it.
- OCR fixes letter casing and recovers text whose PDF text layer is missing or duplicated. On macOS
  it uses `ocr.mac.swift` (Vision framework) automatically; compile it once with
  `swiftc -O ocr.mac.swift -o ocr` and pass `--ocr-cmd ./ocr` to skip the per-page Swift start-up.
  Any command printing `x0 TAB y0 TAB x1 TAB y1 TAB text` (normalised, top-left origin) for a PNG
  path works as `--ocr-cmd`. `--no-ocr` uses the text layer only.
- `--work-dir` keeps the intermediate renders (original and text-free background per page).
- Prints a per-slide report: text lines placed and lines re-cased from OCR.

Check the result in PowerPoint: gradient-filled titles are approximated with a three-stop
gradient and bold is inferred from ink density, so a few boxes may need a touch.

## Platform notes

| Piece | macOS | Linux |
|---|---|---|
| `render_deck.py` | yes | yes |
| `figma-to-pptx.py` | yes | yes, with `--no-ocr` or your own `--ocr-cmd` (e.g. a tesseract wrapper) |
| `ocr.mac.swift` | yes (Vision) | no |
