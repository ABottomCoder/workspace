export const meta = {
  name: 'duo-harness',
  description: 'Author implements a coding task; correctness-critic (runs tests) + optional pluggable static-scanner verify in parallel; iterate to sign-off or escalate to human',
  phases: [
    { title: 'Author', detail: 'implement the task, with execution evidence' },
    { title: 'Review', detail: 'correctness-critic (runs tests) + static-scanner (if enabled) in parallel' },
    { title: 'Rework', detail: 'author fixes reproduced/reported blocking defects' },
  ],
}

// ── INPUT via args (no company hardcoding, no process/require) ──
//   Shape = tools/harness/config.template.json (copy to business/<co>/harness.json and fill):
//   { task, repoDir, testCmd, rolesDir,
//     models:{author,critic}, scanner:{enabled,command,timeout_ms}, maxReworks }
//   Docs: docs/process/multi-agent-harness.md
const TASK       = args?.task ?? 'NO TASK PROVIDED'
const REPO       = args?.repoDir ?? 'NO REPO PROVIDED'
const TEST_CMD   = args?.testCmd ?? '(discover the test command from the repo yourself)'
const M          = args?.models ?? { author: 'opus', critic: 'opus' }
const SCANNER    = args?.scanner ?? { enabled: false, command: '', timeout_ms: 420000 }
const MAX_REWORKS= args?.maxReworks ?? 3
const ROLES      = args?.rolesDir ?? '.claude/agents'   // relative to the main dir (session cwd)
const HARD_ITER_CAP = MAX_REWORKS + 3

const PROPOSAL_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['files', 'summary', 'evidence'],
  properties: {
    files: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    evidence: { type: 'string', description: 'exact command(s) EXECUTED + observed output — not reasoning' },
  },
}
const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'summary', 'findings'],
  properties: {
    verdict: { type: 'string', enum: ['go', 'no-go'] },
    summary: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['severity', 'title', 'failure_evidence'],
        properties: {
          severity: { type: 'string', enum: ['critical', 'important', 'suggestion'] },
          title: { type: 'string' },
          failure_evidence: { type: 'string' },
        },
      },
    },
  },
}

// Tolerant parser for a static-scanner's stdout JSON: handles ```json``` fences,
// leading log lines, nested braces. Returns {ok, total, blocking[], reason}.
function parseScanner(raw) {
  if (!raw || typeof raw !== 'string') return { ok: false, reason: 'empty', blocking: [], total: 0 }
  let s = raw.trim()
  const fence = s.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (fence) s = fence[1].trim()
  const end = s.lastIndexOf('}')
  if (end === -1) return { ok: false, reason: 'no json object', blocking: [], total: 0 }
  let depth = 0, start = -1, inStr = false
  for (let i = end; i >= 0; i--) {
    const ch = s[i]
    if (ch === '"') inStr = !inStr
    if (inStr) continue
    if (ch === '}') depth++
    else if (ch === '{') { depth--; if (depth === 0) { start = i; break } }
  }
  if (start === -1) return { ok: false, reason: 'no balanced object', blocking: [], total: 0 }
  try {
    const j = JSON.parse(s.slice(start, end + 1))
    const findings = Array.isArray(j.findings) ? j.findings : []
    const blocking = findings.filter(f => f.severity === 'critical' || f.severity === 'important')
      .map(f => ({ severity: f.severity, title: f.title, source: 'static-scanner',
        failure_evidence: `static-scanner ${f.source ?? ''} (${f.file}:${f.line_start ?? '?'}): ${f.description ?? ''}`.trim() }))
    return { ok: true, total: findings.length, blocking, metrics: j.metrics ?? null }
  } catch (e) { return { ok: false, reason: 'parse error: ' + e.message, blocking: [], total: 0 } }
}

phase('Author')
const proposal = await agent(
  `[AUTHOR] Read ${ROLES}/author.md for your role. Target repo: ${REPO}
Task: ${TASK}
Test command: ${TEST_CMD}
Implement it in ${REPO}, matching repo style. Then EXECUTE the tests and paste the real command + output as evidence.`,
  { model: M.author, effort: 'high', label: 'author:implement', phase: 'Author', schema: PROPOSAL_SCHEMA }
)
log(`Author: ${proposal?.summary ?? 'NO OUTPUT'} | files: ${proposal?.files?.join(', ') ?? '—'}`)
if (!proposal) return { status: 'ERROR', reason: 'author no output' }

const history = [{ round: 0, ...proposal }]
let finalOwn = null, finalScanner = null
let reworksDone = 0

// Timing-safe loop: cap on REWORKS; a review always runs after the last rework
// (reviews = reworks + 1), so a late-surfacing finding still gets one fix + re-confirm.
for (let round = 1; round <= HARD_ITER_CAP; round++) {
  phase('Review')
  const scannerCmd = SCANNER.enabled && SCANNER.command
    ? SCANNER.command.replace(/\{\{REPO\}\}/g, REPO)
    : null

  const [own, scanner] = await parallel([
    () => agent(
      `[CORRECTNESS-CRITIC] Read ${ROLES}/correctness-critic.md for your role and adversarial stance.
Target repo: ${REPO}
Task under review: ${TASK}
Author's latest claim: ${JSON.stringify(history[history.length - 1])}
Write adversarial tests and RUN them against the code in ${REPO}. Reproduce any defect (command + failing output) before filing. Return the structured verdict.`,
      { model: M.critic, effort: 'high', label: `own-critic:r${round}`, phase: 'Review', schema: VERDICT_SCHEMA }
    ),
    () => scannerCmd
      ? agent(
          `[STATIC-SCANNER-RUNNER] Run this ONE bash command and return ONLY the JSON it prints on stdout as your entire response (no commentary).
CRITICAL: use a Bash timeout of at least ${SCANNER.timeout_ms} ms. Judge success by STDOUT containing a JSON object with a "findings" key and exit code 0 — NOT by empty stderr (harmless warnings there are fine). Only if stdout has NO JSON at all, return the stderr text.

The command:\n${scannerCmd}`,
          { model: 'haiku', effort: 'low', label: `scanner:r${round}`, phase: 'Review' }
        )
      : Promise.resolve(null),
  ])

  finalOwn = own; finalScanner = scanner
  const ownBlocking = (own?.findings ?? []).filter(f => ['critical', 'important'].includes(f.severity))
    .map(f => ({ ...f, source: 'correctness-critic' }))
  const scan = parseScanner(scanner)
  const blocking = [...ownBlocking, ...scan.blocking]
  const scanStatus = !scannerCmd ? 'disabled'
    : scan.ok ? `${scan.total} findings, ${scan.blocking.length} blocking` : `UNPARSEABLE (${scan.reason})`
  log(`Review ${round}: own-critic=${own?.verdict ?? '?'} (${ownBlocking.length} blocking) | scanner: ${scanStatus} | total blocking=${blocking.length} | reworks ${reworksDone}/${MAX_REWORKS}`)

  if (own?.verdict === 'go' && blocking.length === 0) { log('both critics clear → signoff'); break }
  if (reworksDone >= MAX_REWORKS) { log(`rework cap ${MAX_REWORKS} reached with ${blocking.length} blocking → ESCALATE`); break }

  phase('Rework')
  reworksDone++
  const rework = await agent(
    `[AUTHOR] Read ${ROLES}/author.md for your role. Critics found blocking defects in ${REPO}. Fix ALL of them, then re-run the failing cases and paste command + output as evidence.
Blocking defects:
${JSON.stringify(blocking, null, 2)}`,
    { model: M.author, effort: 'high', label: `author:rework${reworksDone}`, phase: 'Rework', schema: PROPOSAL_SCHEMA }
  )
  log(`Rework ${reworksDone}: ${rework?.summary ?? 'NO OUTPUT'}`)
  if (rework) history.push({ round: reworksDone, ...rework })
}

const scanFinal = parseScanner(finalScanner)
const blockingLeft = [
  ...(finalOwn?.findings ?? []).filter(f => ['critical', 'important'].includes(f.severity)).map(f => ({ ...f, source: 'correctness-critic' })),
  ...scanFinal.blocking,
]
const status = !finalOwn ? 'ERROR'
  : (finalOwn.verdict === 'go' && blockingLeft.length === 0) ? 'SIGNOFF_READY_FOR_HUMAN'
  : 'ESCALATED'

return {
  status,
  reworks_used: reworksDone,
  correctness_verdict: finalOwn?.verdict,
  correctness_summary: finalOwn?.summary,
  blocking_remaining: blockingLeft.length,
  blocking_findings: blockingLeft,
  scanner: SCANNER.enabled ? { ok: scanFinal.ok, total: scanFinal.total, blocking: scanFinal.blocking.length, reason: scanFinal.reason } : 'disabled',
  author_final: history[history.length - 1]?.summary,
  files: history[history.length - 1]?.files,
  models: M,
  note: 'SIGNOFF_READY_FOR_HUMAN = correctness-critic go AND zero blocking from either critic. Human approves before any commit. scanner.ok=false → scanner output unparseable, treat as NOT verified.',
}
