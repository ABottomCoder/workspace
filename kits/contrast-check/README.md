# contrast-check

Lists every hex colour in a deployed site's JavaScript bundles whose contrast against a background
(default white) falls in the band that is plausibly text yet fails WCAG AA (1.8 to 4.5:1).

Reading the built bundle catches what the other two methods miss: grepping source misses colours
passed through constants, props or colour maps, and scanning rendered pages misses states the crawl
never entered.

Output is **candidates, not defects**: the script cannot know what a colour is drawn on, or whether
it is text at all. Check each candidate where it is used.

## Install

Node 18+ (built-in `fetch`). No dependencies.

## Usage

```bash
node contrast-check.mjs https://app.example.com
node contrast-check.mjs https://app.example.com --bg '#0b1020' --top 50
```

| Option | Default | Meaning |
|---|---|---|
| `<url>` | (required) | page whose same-origin `<script src>` bundles are scanned |
| `--bg` | `#ffffff` | background to score against (`#rrggbb`) |
| `--min` | `1.8` | lower bound; below it a colour is almost surely a fill or hairline |
| `--max` | `4.5` | upper bound (WCAG AA body text) |
| `--top` | `30` | rows to print |

Only 6-digit hex literals are found; `rgb()`, `hsl()`, 3-digit hex and CSS files are not scanned.
Bundles loaded dynamically (not referenced from the page HTML) are not fetched.

## Platform notes

Pure Node; macOS and Linux. Makes HTTP requests to the given URL only.
