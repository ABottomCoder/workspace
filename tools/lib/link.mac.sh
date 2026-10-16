#!/bin/bash
# POSIX links (macOS, Linux). Loaded by link.sh.
dir_link() { ln -s "$1" "$2"; }
hook_link() { ln -sfn "$1" "$2"; chmod +x "$1"; }
hook_installed() { [ -L "$2" ] && [ "$(readlink "$2")" = "$1" ]; }
