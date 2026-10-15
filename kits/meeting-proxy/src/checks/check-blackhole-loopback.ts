import 'dotenv/config'
import { writeFileSync } from 'fs'
import { spawn, spawnSync, execSync } from 'child_process'
import { DeepgramTTS } from '../tts-deepgram.js'
import { captureFromDevice } from '../audio/input.js'

function peakAmplitude(pcm: Buffer): number {
  let peak = 0
  for (let i = 0; i + 1 < pcm.length; i += 2) {
    const sample = pcm.readInt16LE(i)
    if (Math.abs(sample) > peak) peak = Math.abs(sample)
  }
  return peak
}

async function main() {
  const apiKey = process.env.DEEPGRAM_API_KEY!
  const model = process.env.DEEPGRAM_TTS_MODEL ?? 'aura-2-orpheus-en'
  const outputDevice = process.env.AUDIO_OUTPUT_DEVICE ?? 'BlackHole 16ch'

  console.log(`Testing loopback through device: "${outputDevice}"\n`)

  // 1. Show device's native sample rate (might be the issue)
  console.log('[1/4] Device properties:')
  try {
    const info = execSync(`system_profiler SPAudioDataType | grep -A 8 "${outputDevice}:"`, { encoding: 'utf-8' })
    console.log(info.split('\n').slice(0, 10).map(l => '  ' + l).join('\n'))
  } catch {
    console.log('  (could not read properties)')
  }

  // 2. Generate test audio
  console.log('\n[2/4] Generating TTS test audio...')
  const chunks: Buffer[] = []
  const tts = new DeepgramTTS(apiKey, model, (pcm) => chunks.push(pcm))
  await tts.speak('Loopback test, one two three four five six.')
  const pcm = Buffer.concat(chunks)
  const wavPath = 'tmp/loopback.wav'
  const rawPath = 'tmp/loopback.raw'
  writeFileSync(rawPath, pcm)
  spawnSync('sox', ['-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', rawPath, wavPath])
  console.log(`  generated ${pcm.length} bytes (${(pcm.length / 32000).toFixed(2)}s)`)

  // 3. Start capture from BlackHole 16ch (as INPUT)
  console.log(`\n[3/4] Capturing from "${outputDevice}" while writing to it...`)
  const capturedChunks: Buffer[] = []
  const capture = captureFromDevice(outputDevice)
  capture.stream.on('data', (c: Buffer) => capturedChunks.push(c))
  await new Promise((r) => setTimeout(r, 500))

  // 4. Write to BlackHole 16ch via sox (as OUTPUT)
  console.log(`  Writing TTS audio to "${outputDevice}"...`)
  const write = spawn('sox', [
    '-q',
    '-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', rawPath,
    '-t', 'coreaudio', outputDevice
  ], { stdio: ['ignore', 'pipe', 'pipe'] })

  let writeErr = ''
  write.stderr.on('data', (d) => { writeErr += d.toString() })

  await new Promise<void>((resolve) => write.on('exit', () => resolve()))
  await new Promise((r) => setTimeout(r, 800))
  capture.stop()
  await new Promise((r) => setTimeout(r, 300))

  const captured = Buffer.concat(capturedChunks)
  const peak = peakAmplitude(captured)
  console.log(`  sox-write stderr: ${writeErr.trim() || '(none)'}`)
  console.log(`  captured ${captured.length} bytes, peak amplitude ${peak}/32767`)

  console.log('\n[4/4] Verdict:')
  if (peak > 1000) {
    console.log(`  PASS — "${outputDevice}" round-trips audio cleanly.`)
    console.log(`  → If Zoom Input Level still does not move, the issue is in Zoom's config.`)
  } else {
    console.log(`  FAIL — audio written to "${outputDevice}" cannot be read back.`)
    console.log(`  → Either the device isn't actually receiving our writes (sample-rate or channel issue),`)
    console.log(`    or BlackHole 16ch's permissions/routing are broken.`)
  }
}

main().catch((e) => { console.error(e); process.exit(1) })
