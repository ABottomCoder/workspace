#!/bin/bash
# Run every tests/test_*.sh (or the ones given). Exit non-zero if any fails. Same files on macOS and Windows.
#   bash tests/run.sh                 all
#   bash tests/run.sh tests/test_work.sh
here="$(cd "$(dirname "$0")" && pwd)"
files=("$@"); [ ${#files[@]} -gt 0 ] || files=("$here"/test_*.sh)
rc=0
for f in "${files[@]}"; do bash "$f" || rc=1; done
[ $rc = 0 ] && echo "tests: all passed" || echo "tests: FAILURES"
exit $rc
