#!/bin/bash
# Directory links and git-hook links, per OS (docs/compatibility.md). Source it.
#   dir_link <target> <link>            make <link> point at directory <target>
#   hook_link <script> <hook>           make git hook <hook> run <script>
#   hook_installed <script> <hook>      true if <hook> already runs <script>
# Small per-OS differences live inline here (variant files are for large or tool-specific differences).
_link_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$_link_here/os.sh"

if [ "$(os_variant)" = win ]; then
  # Git Bash `ln -s` silently copies without Developer Mode: directories -> NTFS junction (no admin,
  # transparent to Node/Python); git hooks -> a one-line wrapper script.
  # Separate args: MSYS quotes each for CreateProcess (embedded quotes reach cmd as \" and break it);
  # //J escapes MSYS path conversion.
  dir_link() { cmd //c mklink //J "$(cygpath -w "$2")" "$(cygpath -w "$1")" >/dev/null; }
  hook_link() { printf '#!/bin/sh\n# workspace guard wrapper (tools/lib/link.sh)\nexec bash "%s" "$@"\n' "$1" > "$2"; chmod +x "$2"; }
  hook_installed() { [ -f "$2" ] && grep -qF "exec bash \"$1\"" "$2"; }
else
  # POSIX (macOS, Linux)
  dir_link() { ln -s "$1" "$2"; }
  hook_link() { ln -sfn "$1" "$2"; chmod +x "$1"; }
  hook_installed() { [ -L "$2" ] && [ "$(readlink "$2")" = "$1" ]; }
fi
