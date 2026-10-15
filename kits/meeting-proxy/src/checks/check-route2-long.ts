import 'dotenv/config'
import { DeepgramTTS } from '../tts-deepgram.js'
import { openPlayback } from '../audio/output.js'

async function main() {
  const apiKey = process.env.DEEPGRAM_API_KEY!
  const model = process.env.DEEPGRAM_TTS_MODEL ?? 'aura-2-orpheus-en'
  const outputDevice = process.env.AUDIO_OUTPUT_DEVICE ?? 'BlackHole 2ch'

  console.log(`Writing to "${outputDevice}" for ~30 seconds.`)
  console.log(`Open Zoom → Settings → Audio.`)
  console.log(`Watch the Input Level bar to the RIGHT of the "Test microphone" button.`)
  console.log(`It should pulse (green/blue) for the entire duration.\n`)

  // Generate one chunk of audio
  const chunks: Buffer[] = []
  const tts = new DeepgramTTS(apiKey, model, (pcm) => chunks.push(pcm))
  await tts.speak('Route two test. The meeting proxy is now feeding audio into your virtual microphone. If you see the Zoom input level meter pulse, this side of the pipeline is working correctly. Once more for good measure. The meeting proxy is feeding audio.')
  const pcm = Buffer.concat(chunks)
  console.log(`[generated ${(pcm.length / 32000).toFixed(1)}s of audio, will loop until 30s total]\n`)

  const player = openPlayback(outputDevice)
  const start = Date.now()
  const targetMs = 30_000
  let loopNum = 0

  while (Date.now() - start < targetMs) {
    loopNum++
    console.log(`[loop ${loopNum}] ${((Date.now() - start) / 1000).toFixed(1)}s elapsed`)
    const chunkSize = 16000 * 2 / 10
    for (let i = 0; i < pcm.length && Date.now() - start < targetMs; i += chunkSize) {
      player.write(pcm.subarray(i, Math.min(i + chunkSize, pcm.length)))
      await new Promise((r) => setTimeout(r, 90))
    }
    await player.flush()
  }

  player.stop()
  console.log(`\nDone. Did the Input Level bar pulse?`)
}

main().catch((e) => { console.error(e); process.exit(1) })
