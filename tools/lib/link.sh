#!/bin/bash
# Directory links and git-hook links, per OS: loads link.<variant>.sh (docs/compatibility.md). Source it.
#   dir_link <target> <link>            make <link> point at directory <target>
#   hook_link <script> <hook>           make git hook <hook> run <script>
#   hook_installed <script> <hook>      true if <hook> already runs <script>
# Linux uses the POSIX variant (link.mac.sh). No variant for the OS -> fail with a message.
_link_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$_link_here/os.sh"
_link_v=$(os_variant); [ "$_link_v" = linux ] && _link_v=mac
if [ -f "$_link_here/link.$_link_v.sh" ]; then . "$_link_here/link.$_link_v.sh"
else echo "link: no variant for OS '$(uname -s)' (add tools/lib/link.<variant>.sh)" >&2; return 1 2>/dev/null || exit 1; fi
