import 'dotenv/config'
import { captureFromDevice } from './input.js'
import { openPlayback } from './output.js'

const inputDevice = process.env.AUDIO_INPUT_DEVICE ?? 'BlackHole 2ch'
const outputDevice = process.env.AUDIO_OUTPUT_DEVICE ?? 'BlackHole 16ch'
const durationMs = 5000

console.log(`[test-loop] capturing from "${inputDevice}" for ${durationMs}ms, replaying to "${outputDevice}"`)

const buffers: Buffer[] = []
const capture = captureFromDevice(inputDevice)

capture.stream.on('data', (chunk: Buffer) => {
  buffers.push(chunk)
})

setTimeout(async () => {
  capture.stop()
  await new Promise((r) => setTimeout(r, 200))

  const total = buffers.reduce((sum, b) => sum + b.length, 0)
  console.log(`[test-loop] captured ${total} bytes (${(total / 32000).toFixed(2)}s of 16kHz mono PCM)`)

  if (total === 0) {
    console.error('[test-loop] no audio captured — check device name and mic permissions')
    process.exit(1)
  }

  console.log('[test-loop] replaying...')
  const player = openPlayback(outputDevice)
  for (const chunk of buffers) {
    player.write(chunk)
  }
  await player.flush()
  console.log('[test-loop] done')
  process.exit(0)
}, durationMs)
