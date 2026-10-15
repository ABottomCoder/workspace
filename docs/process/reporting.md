# Reporting

Report style, metadata, evidence and the no-self-auditing rule. Mandatory in heavy tier; in light tier,
write a report only when someone will read it. Reviewing someone else's PR is a different protocol:
[pr-review.md](pr-review.md).

## Where reports live

All in the ticket dir: `business/<co>/tickets/<ID>/reports/`.

| File | What |
|---|---|
| `test-report-v<n>.html` | test run: command, pass/fail/skip counts per runtime with exact dependency versions, failure details, coverage if available. `v1` = the final passing run; `v2+` only for re-tests after review |
| `ticket-report.html` | the ticket's permanent record (sections below) |
| `qa.md`, `qa-report.html` | the QA session's working record and final report ([qa-session.md](qa-session.md)) |
| `review-r<n>.md` | your review of someone else's PR, round n |

Source images and raw proofs live in `evidence/`. Non-ticket deliverables go to `business/<co>/docs/<topic>/`.

## Ticket report structure

Answer, in this order and visually: **what was asked → what we did and why → how it was tested →
evidence that it is done**. Sections: metadata, summary, implementation (changes, rationale, files),
problems encountered → resolutions, testing (results, link to test report), evidence, learnings.
Review rework is appended as its own section, never a rewrite.

## Style

- **Self-contained single HTML file**: inline CSS, no CDN, no external JS or fonts; opens in a browser
  with no build step.
- Clean, light, readable; colour-coded status (green pass, red fail, yellow warning/skip), never colour
  alone; tables for structured data; `<details>` for stack traces and long logs.
- **Visual first, no walls of text.** Any block past ~4 lines becomes a table, list, before/after pair
  or diagram. Lead each section with the answer (verdict chip, count, one-line takeaway). Prefer status
  chips, before/after screenshots, AC-vs-evidence tables (✅/❌/⚠️), metric tiles, simple inline SVG flows.
- **Every number must be current.** After any code change, grep the report for the *previous* numbers too.

## Everything inlined: a report is forwarded as one file

- Images are embedded as base64 data URIs (`<img src="data:image/png;base64,…">`); keep the source
  PNG in `evidence/` for re-cropping.
- Check before calling it done: `grep -o 'src="[^d][^"]*"' <report>.html` must print nothing.

## Evidence, not just conclusions

Every report has an **Evidence** section with the raw artifact behind each material claim: real command
output, network calls, route listings, query results, before/after diffs, screenshots, with real values.
One evidence item per claim; verbose blocks inside `<details>`. A report with conclusions but no
embedded evidence is incomplete.

## A report states the current conclusion; it never audits itself

A report has two jobs: state the conclusion, show the evidence. Never write "an earlier draft said X",
"corrected from 5 of 10 to 4 of 10", a "Corrections" section, or any heading that reads as *this
document* being unreliable. It destroys the credibility of every other number on the page.

The corrections history goes in the working record (`LOG.md`, or the measurement file in `evidence/`),
where a future session can find why a figure moved.

Not forbidden, and required: stating limits ("n = 10, illustrates the mechanism, not a rate"),
provenance tags (`measured` / `from source` / `inference`), and a "What this does not show" section.
Test: does the sentence tell the reader about **the subject**, or about **us**? Subject stays, us goes.
Name the broken thing precisely in headings so a heading about a pipeline defect doesn't read as the
report being broken.

## Required metadata header

| Field | Source |
|---|---|
| Ticket ID | ticket system |
| Report date | today |
| Reporter, reporter email | `user/profile.md` |
| Repo(s), base branch, feature branch | intake / Phase 2 |
| Commit hash | `git rev-parse HEAD` after the final commit, pasted, never from memory |
| Test environment | where the tests actually ran |

## Before sending any generated document

Read it end to end; every number in the prose must agree with the table beside it; every claim must be
derived from the artifact it describes; every "there is no X", "another person" or alarming qualitative
word needs a falsifying command or value-level evidence behind it
([verification-antipatterns.md](../principles/verification-antipatterns.md) §28).
