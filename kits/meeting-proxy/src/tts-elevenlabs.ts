import WebSocket from 'ws'
import type { TTSProvider } from './tts.js'

export class ElevenLabsTTS implements TTSProvider {
  constructor(
    private apiKey: string,
    private voiceId: string,
    private speed: number,
    private onAudio: (pcm: Buffer) => void
  ) {}

  async speak(text: string): Promise<void> {
    const url = `wss://api.elevenlabs.io/v1/text-to-speech/${this.voiceId}/stream-input`
      + `?model_id=eleven_turbo_v2_5`
      + `&output_format=pcm_16000`
      + `&optimize_streaming_latency=4`

    const ws = new WebSocket(url, {
      headers: { 'xi-api-key': this.apiKey }
    })

    await new Promise<void>((resolve, reject) => {
      ws.once('open', () => resolve())
      ws.once('error', reject)
    })

    ws.send(JSON.stringify({
      text: ' ',
      voice_settings: {
        stability: 0.45,
        similarity_boost: 0.8,
        use_speaker_boost: true,
        speed: this.speed
      },
      generation_config: { chunk_length_schedule: [120, 160, 250, 290] },
      xi_api_key: this.apiKey
    }))

    ws.on('message', (data) => {
      try {
        const msg = JSON.parse(data.toString())
        if (msg.audio) {
          const audio = Buffer.from(msg.audio, 'base64')
          this.onAudio(audio)
        }
        if (msg.error) {
          console.error('[tts] elevenlabs error:', msg.error)
        }
      } catch {
        // non-JSON frames are ignored
      }
    })

    ws.send(JSON.stringify({ text, try_trigger_generation: true }))
    ws.send(JSON.stringify({ text: '' }))

    await new Promise<void>((resolve) => {
      ws.once('close', () => resolve())
      ws.once('error', () => resolve())
    })
  }
}
