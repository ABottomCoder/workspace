import { createClient, LiveTranscriptionEvents, LiveClient } from '@deepgram/sdk'
import { EventEmitter } from 'events'

export interface TranscriptEvent {
  text: string
  isFinal: boolean
  speechFinal: boolean
}

export class ASR extends EventEmitter {
  private connection: LiveClient | null = null
  private keepAliveTimer: NodeJS.Timeout | null = null
  private stopped = false
  private lastSampleRate = 16000
  private lastKeyterms: string[] = []

  constructor(private apiKey: string) {
    super()
  }

  start(sampleRate = 16000, keyterms: string[] = []) {
    this.stopped = false
    this.lastSampleRate = sampleRate
    this.lastKeyterms = keyterms
    const client = createClient(this.apiKey)
    // keywords boost recognition of specific words (e.g. user's name).
    // Format: "word:intensifier" — higher intensifier = stronger boost.
    // 8x: at 3x a short first name was still mis-transcribed in live tests.
    const keywords = keyterms.length > 0 ? keyterms.map(k => `${k}:8`) : undefined
    this.connection = client.listen.live({
      model: 'nova-2',
      language: 'en-US',
      encoding: 'linear16',
      sample_rate: sampleRate,
      channels: 1,
      interim_results: true,
      smart_format: true,
      vad_events: true,
      utterance_end_ms: 1000,
      endpointing: 300,
      ...(keywords && { keywords })
    })

    this.connection.on(LiveTranscriptionEvents.Open, () => {
      console.log('[asr] connected to Deepgram')
      this.keepAliveTimer = setInterval(() => {
        this.connection?.keepAlive()
      }, 8000)
    })

    this.connection.on(LiveTranscriptionEvents.Transcript, (data: any) => {
      const text: string = data?.channel?.alternatives?.[0]?.transcript ?? ''
      if (!text.trim()) return
      this.emit('transcript', {
        text,
        isFinal: !!data.is_final,
        speechFinal: !!data.speech_final
      } satisfies TranscriptEvent)
    })

    this.connection.on(LiveTranscriptionEvents.UtteranceEnd, () => {
      this.emit('utterance-end')
    })

    this.connection.on(LiveTranscriptionEvents.Error, (err: any) => {
      console.error('[asr] error:', err)
    })

    this.connection.on(LiveTranscriptionEvents.Close, () => {
      console.log('[asr] disconnected')
      if (this.keepAliveTimer) {
        clearInterval(this.keepAliveTimer)
        this.keepAliveTimer = null
      }
      // Deepgram drops long-lived sockets; without reconnect the proxy goes
      // permanently deaf while everything else keeps running (2026-07-14).
      if (!this.stopped) {
        console.log('[asr] reconnecting in 2s...')
        this.connection = null
        setTimeout(() => {
          if (!this.stopped) this.start(this.lastSampleRate, this.lastKeyterms)
        }, 2000)
      }
    })
  }

  send(pcm: Buffer) {
    if (this.connection) {
      // Deepgram SDK accepts ArrayBuffer, not Node Buffer
      const ab = pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength) as ArrayBuffer
      this.connection.send(ab)
    }
  }

  stop() {
    this.stopped = true
    if (this.keepAliveTimer) {
      clearInterval(this.keepAliveTimer)
      this.keepAliveTimer = null
    }
    if (this.connection) {
      this.connection.finish()
      this.connection = null
    }
  }
}
