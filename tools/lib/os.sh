#!/bin/bash
# Which OS variant to load (docs/compatibility.md). Source it.
#   os_variant          mac | win | linux | unknown   (win = Git Bash / MSYS / Cygwin on Windows)
#   native_path <path>  the path as the OS's own programs see it (win: D:\x; elsewhere unchanged)
os_variant() { case "$(uname -s)" in Darwin) echo mac ;; MINGW*|MSYS*|CYGWIN*) echo win ;; Linux) echo linux ;; *) echo unknown ;; esac; }
native_path() { if [ "$(os_variant)" = win ]; then cygpath -w "$1"; else printf '%s\n' "$1"; fi; }
