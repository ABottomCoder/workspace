import { createClient, DeepgramClient } from '@deepgram/sdk'
import type { TTSProvider } from './tts.js'

export class DeepgramTTS implements TTSProvider {
  private client: DeepgramClient

  constructor(
    apiKey: string,
    private model: string,
    private onAudio: (pcm: Buffer) => void
  ) {
    this.client = createClient(apiKey)
  }

  async speak(text: string): Promise<void> {
    const response = await this.client.speak.request(
      { text },
      {
        model: this.model,
        encoding: 'linear16',
        sample_rate: 16000,
        container: 'none'
      }
    )

    const stream = await response.getStream()
    if (!stream) {
      console.error('[tts-deepgram] no stream returned')
      return
    }

    const reader = stream.getReader()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      if (value) this.onAudio(Buffer.from(value))
    }
  }
}
