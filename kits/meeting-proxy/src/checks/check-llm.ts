import 'dotenv/config'
import { LLM, buildSystemPrompt } from '../llm.js'

const SAMPLE_CONTEXT = `## Meeting: Acme Weekly Sync
## Attendees: Sam (lead), Jordan
## My role: Lead developer on the Acme app

## Recent work
- Last week shipped: agents feature, GitHub OAuth alt-path
- This week working on: timezone-aware agent scheduling, demo polish
- Blockers: none

## Hard rules
- NEVER commit to a specific date
- NEVER agree to scope additions
- If asked about something not in this doc, say "let me check the latest and follow up"`

const CASES: Array<{ label: string; transcript: string; expected: 'silent' | 'respond' }> = [
  {
    label: 'Other person addressed',
    transcript: 'Sarah, can you give us an update on the design system this week?',
    expected: 'silent'
  },
  {
    label: 'Name mentioned, no question',
    transcript: 'Yeah, Alex mentioned that last week in the standup. Anyway, the next item is the marketing review.',
    expected: 'silent'
  },
  {
    label: 'Direct status question',
    transcript: "Alex, what's the status on the agents feature this week?",
    expected: 'respond'
  },
  {
    label: 'Commitment pressure (should deflect)',
    transcript: 'Alex, can you commit to having the entire timezone work done by Wednesday?',
    expected: 'respond'
  }
]

async function main() {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    console.error('Missing ANTHROPIC_API_KEY in .env')
    process.exit(1)
  }
  const llm = new LLM(apiKey)
  const prompt = buildSystemPrompt('Alex', SAMPLE_CONTEXT)

  console.log(`System prompt: ${prompt.length} chars (cached after first call)\n`)

  let pass = 0
  let fail = 0

  for (const c of CASES) {
    const t0 = Date.now()
    let full = ''
    for await (const chunk of llm.generate(prompt, [{ role: "user" as const, content: c.transcript }])) full += chunk
    full = full.trim()
    const stripped = full.trim().replace(/^[`'"*\\\s]+|[`'"*\\\s]+$/g, '').trim()
    const isSilent = stripped === '[SILENT]' || stripped.startsWith('[SILENT]')
    const actual = isSilent ? 'silent' : 'respond'
    const ok = actual === c.expected
    const mark = ok ? 'PASS' : 'FAIL'
    const ms = Date.now() - t0
    console.log(`[${mark}] ${c.label} (${ms}ms)`)
    console.log(`  transcript: "${c.transcript}"`)
    console.log(`  decision: ${actual}${ok ? '' : ` (expected ${c.expected})`}`)
    if (!isSilent) console.log(`  spoken: "${full}"`)
    console.log()
    if (ok) pass++; else fail++
  }

  console.log(`---\n${pass}/${pass + fail} passed`)
  process.exit(fail > 0 ? 1 : 0)
}

main().catch((e) => { console.error(e); process.exit(1) })
