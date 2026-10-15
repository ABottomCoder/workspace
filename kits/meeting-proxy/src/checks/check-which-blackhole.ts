import 'dotenv/config'
import { writeFileSync } from 'fs'
import { spawn, spawnSync, execSync } from 'child_process'
import { DeepgramTTS } from '../tts-deepgram.js'
import { captureFromDevice } from '../audio/input.js'

function peak(pcm: Buffer): number {
  let p = 0
  for (let i = 0; i + 1 < pcm.length; i += 2) {
    const s = Math.abs(pcm.readInt16LE(i))
    if (s > p) p = s
  }
  return p
}

async function main() {
  const apiKey = process.env.DEEPGRAM_API_KEY!
  const model = process.env.DEEPGRAM_TTS_MODEL ?? 'aura-2-orpheus-en'

  console.log('Diagnostic: which BlackHole device is currently receiving audio from system output?\n')

  // Show current system default output
  console.log('[macOS current default output]')
  try {
    const out = execSync(`system_profiler SPAudioDataType | grep -B 1 "Default Output Device: Yes" | head -5`, { encoding: 'utf-8' })
    console.log(out.trim().split('\n').map(l => '  ' + l).join('\n'))
  } catch {}
  try {
    const out = execSync(`system_profiler SPAudioDataType | grep -B 1 "Default System Output Device: Yes" | head -5`, { encoding: 'utf-8' })
    console.log('  (Default System Output:)')
    console.log(out.trim().split('\n').map(l => '  ' + l).join('\n'))
  } catch {}

  // Generate test audio once
  console.log('\nGenerating TTS audio...')
  const ttsChunks: Buffer[] = []
  const tts = new DeepgramTTS(apiKey, model, (pcm) => ttsChunks.push(pcm))
  await tts.speak('Diagnostic test. One two three four five six seven eight nine ten.')
  const pcm = Buffer.concat(ttsChunks)
  const wavPath = 'tmp/diag.wav'
  const rawPath = 'tmp/diag.raw'
  writeFileSync(rawPath, pcm)
  spawnSync('sox', ['-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', rawPath, wavPath])
  console.log(`  ${pcm.length} bytes (${(pcm.length / 32000).toFixed(2)}s)`)

  for (const device of ['BlackHole 2ch', 'BlackHole 16ch']) {
    console.log(`\n--- Testing capture from "${device}" ---`)
    const chunks: Buffer[] = []
    const capture = captureFromDevice(device)
    capture.stream.on('data', (c: Buffer) => chunks.push(c))
    await new Promise((r) => setTimeout(r, 500))

    console.log(`  Playing TTS through default system output...`)
    const play = spawn('sox', [wavPath, '-d'])
    await new Promise<void>((resolve) => play.on('exit', () => resolve()))
    await new Promise((r) => setTimeout(r, 500))
    capture.stop()
    await new Promise((r) => setTimeout(r, 300))

    const captured = Buffer.concat(chunks)
    const p = peak(captured)
    const verdict = p > 1000 ? 'RECEIVING AUDIO' : 'silence/noise floor only'
    console.log(`  captured ${captured.length} bytes, peak ${p}/32767  ←  ${verdict}`)
  }

  console.log('\nInterpretation:')
  console.log('  - If "BlackHole 16ch" RECEIVING AUDIO  → Multi-Output Device is correctly configured ✓')
  console.log('  - If "BlackHole 2ch"  RECEIVING AUDIO  → Multi-Output Device still has 2ch checked (needs swap)')
  console.log('  - If NEITHER receives audio            → System sound output is not set to "Meeting Output"')
  console.log('  - If BOTH receive audio                → Multi-Output Device has both checked (fine, but only 16ch is what .env expects)')
}

main().catch((e) => { console.error(e); process.exit(1) })
