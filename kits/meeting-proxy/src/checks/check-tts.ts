import { writeFileSync } from 'fs'
import { spawnSync } from 'child_process'
import { loadConfig } from '../config.js'
import { createTTS } from '../tts.js'

async function main() {
  const config = loadConfig('<check-tts>')
  const text = "Hey, this is just a quick test of the meeting proxy voice. If you can hear this clearly, the text to speech pipeline is working."

  const label = config.ttsProvider === 'elevenlabs'
    ? `ElevenLabs (voice ${config.elevenlabsVoiceId})`
    : `Deepgram (${config.deepgramTtsModel})`
  console.log(`Using TTS provider: ${label}`)
  console.log(`Generating: "${text}"`)

  const chunks: Buffer[] = []
  const tts = createTTS(config, (pcm) => chunks.push(pcm))

  const t0 = Date.now()
  await tts.speak(text)
  const ms = Date.now() - t0

  const pcm = Buffer.concat(chunks)
  const bytes = pcm.length
  const seconds = bytes / (16000 * 2)
  console.log(`Generated ${bytes} bytes (${seconds.toFixed(2)}s of audio) in ${ms}ms`)

  if (bytes === 0) {
    console.error('No audio generated. Check API key and voice ID in .env.')
    process.exit(1)
  }

  const rawPath = 'tmp/check-tts.raw'
  const wavPath = 'tmp/check-tts.wav'
  writeFileSync(rawPath, pcm)
  spawnSync('sox', ['-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', rawPath, wavPath])
  console.log(`Wrote ${wavPath}`)

  console.log('\nPlaying through default output device (your headphones)...')
  const play = spawnSync('sox', [wavPath, '-d'], { stdio: 'inherit' })
  if (play.status !== 0) {
    console.error('Playback failed — try `sox tmp/check-tts.wav -d` manually')
    process.exit(1)
  }
  console.log('Playback done.')
}

main().catch((e) => { console.error(e); process.exit(1) })
