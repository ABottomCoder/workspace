import 'dotenv/config'
import { readFileSync, existsSync } from 'fs'
import { ASR } from '../asr.js'

async function main() {
  const apiKey = process.env.DEEPGRAM_API_KEY
  if (!apiKey) {
    console.error('Missing DEEPGRAM_API_KEY in .env')
    process.exit(1)
  }

  const rawPath = 'tmp/check-tts.raw'
  if (!existsSync(rawPath)) {
    console.error(`Missing ${rawPath} — run check-tts.ts first to generate test audio`)
    process.exit(1)
  }

  const pcm = readFileSync(rawPath)
  console.log(`Loaded ${pcm.length} bytes (${(pcm.length / 32000).toFixed(2)}s) of 16kHz mono PCM`)

  const asr = new ASR(apiKey)
  const transcripts: string[] = []
  asr.on('transcript', (e) => {
    if (e.isFinal) {
      console.log(`[final] ${e.text}`)
      transcripts.push(e.text)
    }
  })

  console.log('Opening Deepgram streaming connection...')
  asr.start()
  await new Promise((r) => setTimeout(r, 800))

  // Stream the PCM in ~250ms slices to mimic live capture
  const chunkSize = 16000 * 2 / 4
  for (let i = 0; i < pcm.length; i += chunkSize) {
    const slice = pcm.subarray(i, Math.min(i + chunkSize, pcm.length))
    asr.send(slice)
    await new Promise((r) => setTimeout(r, 200))
  }

  console.log('Audio sent, waiting 3s for final transcripts...')
  await new Promise((r) => setTimeout(r, 3000))
  asr.stop()
  await new Promise((r) => setTimeout(r, 500))

  const merged = transcripts.join(' ').toLowerCase()
  const keywords = ['meeting', 'proxy', 'voice', 'test']
  const hits = keywords.filter((k) => merged.includes(k))
  console.log(`\nKeyword recall: ${hits.length}/${keywords.length} found (${hits.join(', ')})`)
  console.log(`Full transcript: "${transcripts.join(' ')}"`)
  process.exit(hits.length >= 3 ? 0 : 1)
}

main().catch((e) => { console.error(e); process.exit(1) })
