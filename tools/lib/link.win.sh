#!/bin/bash
# Windows (Git Bash). Loaded by link.sh. Git Bash `ln -s` silently copies without Developer Mode, so:
# directories -> NTFS junction (no admin, transparent to Node/Python); git hooks -> a one-line wrapper script.
# Separate args (MSYS quotes each for CreateProcess; embedded quotes reach cmd as \" and break it); //J escapes MSYS path conversion.
dir_link() { cmd //c mklink //J "$(cygpath -w "$2")" "$(cygpath -w "$1")" >/dev/null; }
hook_link() { printf '#!/bin/sh\n# workspace guard wrapper (tools/lib/link.win.sh)\nexec bash "%s" "$@"\n' "$1" > "$2"; chmod +x "$2"; }
hook_installed() { [ -f "$2" ] && grep -qF "exec bash \"$1\"" "$2"; }
