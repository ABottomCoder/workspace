# <id> — log

Append-only, newest last, one timestamped line each (`tools/work/log`). Record what a successor
must know: what changed (commits, deploys, files), what was decided and why, what was sent to whom,
what failed, what was found. Not: files read, raw output, thinking.
Past ~300 lines, move older lines to `history/log-<date>.md` and leave a digest at the top.

