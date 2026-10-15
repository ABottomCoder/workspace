import { loadConfig, loadContext } from './config.js'
import { Orchestrator } from './orchestrator.js'

const DEFAULT_CONTEXT = `## Default context (no meeting-specific context provided)

This is a casual call. No specific meeting agenda or project status to report.

I am a software developer.

## Behavior

- Answer general questions naturally and briefly (name, role, how I'm doing, what I do generally).
- If asked about ANY specific project, deadline, status, commitment, scope, or technical detail — defer with "I'd need to check the latest before I can give you specifics, let me follow up after the call".
- If asked something I clearly cannot answer without context (e.g. "did you finish task X?"), defer rather than guess.
`

function parseArgs(): { contextPath: string | null } {
  const args = process.argv.slice(2)
  const flagIdx = args.indexOf('--context')
  if (flagIdx === -1 || !args[flagIdx + 1]) {
    return { contextPath: null }
  }
  return { contextPath: args[flagIdx + 1] }
}

async function main() {
  const { contextPath } = parseArgs()
  const config = loadConfig(contextPath ?? '<default>')

  let context: string
  if (contextPath) {
    context = loadContext(contextPath)
    console.log(`[main] loaded context from ${contextPath} (${context.length} chars)`)
  } else {
    context = DEFAULT_CONTEXT
    console.log(`[main] no --context flag, using built-in default (general-purpose, defers specifics)`)
  }

  const orch = new Orchestrator(config, context)
  orch.start()

  process.on('SIGINT', async () => {
    console.log('\n[main] shutting down...')
    await orch.stop()
    process.exit(0)
  })
}

main().catch((err) => {
  console.error('[main] fatal:', err)
  process.exit(1)
})
