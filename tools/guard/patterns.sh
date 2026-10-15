# Shared leak patterns for pre-commit, path-lint and route-check (grep -E syntax).
# Written so that this file does not match itself.
GUARD_BLOCKED_DIRS='^(user|business|\.staging)/'
GUARD_SECRET_RE='xox[abpr]-[A-Za-z0-9-]{10,}|xapp-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN ([A-Z]+ )*PRIVATE KEY-----|sk-ant-[A-Za-z0-9_-]{20,}|sk_live_[A-Za-z0-9]{16,}'
GUARD_HOMEPATH_RE='/(Users|home)/[A-Za-z0-9._-]+'

# Denylist (one term per line, # comments) -> one case-insensitive ERE with word boundaries.
# Underscore counts as a boundary, so "slack_term" still matches "term".
guard_denylist_re() {
  [ -f "$1" ] || return 1
  local alt
  alt=$(grep -v '^[[:space:]]*#' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$' \
        | sed 's/[][\.*^$(){}?+|/]/\\&/g' | paste -sd '|' -)
  [ -n "$alt" ] || return 1
  printf '(^|[^A-Za-z0-9])(%s)([^A-Za-z0-9]|$)' "$alt"
}
