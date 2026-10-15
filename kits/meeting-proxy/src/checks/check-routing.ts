import 'dotenv/config'
import { writeFileSync } from 'fs'
import { spawn, spawnSync } from 'child_process'
import { DeepgramTTS } from '../tts-deepgram.js'
import { captureFromDevice } from '../audio/input.js'
import { openPlayback } from '../audio/output.js'

function peakAmplitude(pcm: Buffer): number {
  let peak = 0
  for (let i = 0; i + 1 < pcm.length; i += 2) {
    const sample = pcm.readInt16LE(i)
    const abs = Math.abs(sample)
    if (abs > peak) peak = abs
  }
  return peak
}

async function main() {
  const apiKey = process.env.DEEPGRAM_API_KEY
  if (!apiKey) { console.error('Missing DEEPGRAM_API_KEY'); process.exit(1) }
  const model = process.env.DEEPGRAM_TTS_MODEL ?? 'aura-2-perseus-en'
  const inputDevice = process.env.AUDIO_INPUT_DEVICE ?? 'BlackHole 2ch'
  const outputDevice = process.env.AUDIO_OUTPUT_DEVICE ?? 'BlackHole 16ch'

  console.log(`Model: ${model}`)
  console.log(`Input device: ${inputDevice}`)
  console.log(`Output device: ${outputDevice}\n`)

  // Step 1: Generate TTS audio once (used for both routing tests).
  console.log('[1/3] Generating Perseus TTS audio...')
  const ttsChunks: Buffer[] = []
  const tts = new DeepgramTTS(apiKey, model, (pcm) => ttsChunks.push(pcm))
  await tts.speak("Audio routing test. This is the meeting proxy speaking. If your routing is correct, this audio will be captured from BlackHole two-channel, and then replayed into BlackHole sixteen-channel.")
  const ttsAudio = Buffer.concat(ttsChunks)
  const ttsDurationSec = ttsAudio.length / 32000
  console.log(`  generated ${ttsAudio.length} bytes (${ttsDurationSec.toFixed(2)}s)\n`)

  // Step 2: ROUTE 1 — Zoom Speaker writes to BlackHole 16ch → we capture from BlackHole 16ch
  // Simulated by sox writing directly to BlackHole 16ch (no Multi-Output Device).
  // This is what Zoom will actually do when Zoom Speaker = BlackHole 16ch.
  console.log(`[2/3] Testing ROUTE 1 (Zoom Speaker direct -> ${inputDevice} -> our capture)`)
  console.log(`  Starting capture from "${inputDevice}"...`)
  const capturedChunks: Buffer[] = []
  const capture = captureFromDevice(inputDevice)
  capture.stream.on('data', (c: Buffer) => capturedChunks.push(c))
  await new Promise((r) => setTimeout(r, 500))

  // Write TTS to wav, then play that wav into the input device (mimics Zoom).
  const wavPath = 'tmp/check-routing.wav'
  const rawPath = 'tmp/check-routing.raw'
  writeFileSync(rawPath, ttsAudio)
  spawnSync('sox', ['-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', rawPath, wavPath])

  console.log(`  Playing TTS directly to "${inputDevice}" (simulates Zoom Speaker = ${inputDevice})...`)
  const play = spawn('sox', ['-q', wavPath, '-t', 'coreaudio', inputDevice])
  await new Promise<void>((resolve) => play.on('exit', () => resolve()))
  await new Promise((r) => setTimeout(r, 500))

  capture.stop()
  await new Promise((r) => setTimeout(r, 200))

  const captured = Buffer.concat(capturedChunks)
  const peak = peakAmplitude(captured)
  const capturedSec = captured.length / 32000
  console.log(`  captured ${captured.length} bytes (${capturedSec.toFixed(2)}s), peak amplitude ${peak}/32767`)

  // Threshold lowered to 1500 — writing mono to 16ch device + sox averaging
  // on read gives ~1/8 amplitude. ASR works fine at this level.
  const route1Pass = peak > 1500
  console.log(`  ROUTE 1: ${route1Pass ? 'PASS' : 'FAIL'} ${route1Pass ? `(audio loops through ${inputDevice})` : `(silence — ${inputDevice} not round-tripping)`}\n`)

  if (!route1Pass) {
    console.error(`Route 1 failed. ${inputDevice} should round-trip cleanly. Try:`)
    console.error(`  - sudo killall coreaudiod  # restart CoreAudio`)
    console.error(`  - Reinstall BlackHole: brew reinstall --cask blackhole-16ch`)
    process.exit(1)
  }

  // Step 3: ROUTE 2 — write to AUDIO_OUTPUT_DEVICE which is what Zoom's mic reads from.
  console.log(`[3/3] Testing ROUTE 2 (we write -> ${outputDevice} -> Zoom mic input)`)
  console.log(`  Confirm Zoom → Settings → Audio → Microphone is set to "${outputDevice}"`)
  console.log(`  Watch the Input Level meter — it should move for the next ~${ttsDurationSec.toFixed(0)}s.\n`)
  console.log(`  Playing TTS into "${outputDevice}" now...`)

  const player = openPlayback(outputDevice)
  const chunkSize = 16000 * 2 / 10
  for (let i = 0; i < ttsAudio.length; i += chunkSize) {
    player.write(ttsAudio.subarray(i, Math.min(i + chunkSize, ttsAudio.length)))
    await new Promise((r) => setTimeout(r, 90))
  }
  await player.flush()
  console.log('  Done. Did the Zoom Input Level meter move? (you tell me)')
}

main().catch((e) => { console.error(e); process.exit(1) })
