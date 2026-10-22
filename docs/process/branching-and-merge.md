# Branching and Merge Methods

Read for any release, branch or merge question, and when choosing the base for a PR. The business's own
model and per-repo deviations are recorded in `business/<co>/stack.md` and the repo rows; this is the
transferable guidance.

## Git Flow (when the team uses release branches)

| Branch | Role |
|---|---|
| `feature/*` | one per feature, per the branch convention; merges **into the integration branch** (`develop`) |
| `develop` | integration branch; the base for new work |
| `release/*` | cut from `develop` to prepare a release; release-only fixes land here |
| `hotfix/*` | cut from `main` for urgent production fixes |
| `main` | released code only; **tag every release** |

**The rule that prevents history drift:** after a release, merge the release branch back into **both**
`develop` and `main`.

**Merge method per PR:**
- feature → develop: **squash and merge** (one commit per feature, clean history).
- develop/release → main: **merge commit (`--no-ff`), never squash.** A squash creates a single-parent
  commit with no ancestry link, so the next release PR re-lists every already-shipped commit with
  phantom conflicts. It looks like a git bug; the cause is one dropdown chosen months earlier.
- Rebase-and-merge: avoid for releases (rewrites SHAs, no merge link).
- An identical hotfix that must reach both `main` and `develop` is the usual exception that justifies a
  merge commit into `develop`.

Mnemonic: **into develop, squash; out to main, merge commit.** Also check releases are actually tagged.

**Branch from the PR's target.** Branching off `main` and opening a PR into `develop` drags every
merged-but-not-yet-in-develop commit into the PR. Cut the feature branch from the branch it will merge
into.

## Trunk-based teams

Keep the same two invariants that matter: short-lived branches cut from the target, and a merge method
that preserves ancestry wherever two long-lived branches must stay in sync.

## Review and merge gates

- Never merge into a shared branch without the review the team requires; "the owner said merge it" plus
  green tests is not a review. Check open PRs for duplicates first.
- Pushing, opening PRs and merging are outward actions: they need authorisation
  ([communication.md](../principles/communication.md#authority-and-approval)).

## Writing the PR description

The reviewer should know what the PR does and why before reading any detail. Write it for someone who
was not in the session.

1. **Summary first: one or two plain sentences.** What changes for the user or the system, and why.
   No file names, no jargon the reviewer has to decode.
2. **Then the detail, in short headed sections**, only the ones that apply:
   - **Changes**: one bullet per logical change, grouped by area; the file only when it helps.
   - **Why / context**: the problem, the ticket link, a decision and the alternative rejected.
   - **How it was tested**: commands run, cases covered, what was not verified (UNVERIFIED).
   - **Risk and rollout**: migrations, flags, config, anything to do at deploy or to watch after.
   - **Review notes**: where to look first, anything deliberately left out.
3. **Layout for scanning.** Headings and bullets, one idea per bullet, blank lines between sections, at
   most two levels of nesting, code formatting for names and commands. No wall of text and no long
   paragraphs; if a bullet needs three lines, split it or move the detail to a linked report.

Keep the description current: after review rework, update it (the summary too) rather than appending.

## What makes a useful repo row (in the business repo table)

- Key entry points at file granularity; non-obvious behaviour inline (a function that mutates shared
  state, an error branch that falls through).
- Base branch stated explicitly; host and conventions when the repo differs from the default (other git
  host, merge requests, different branch and commit formats).
- Branch → environment mapping when deploys are branch-driven.
- Who owns the platform it runs on when that isn't the team, and where to file platform requests.
- Migration pairs: legacy and new repo both listed, which is source and destination, what still lives
  only in the legacy one.
- Local clone directory versus remote path when they differ.
