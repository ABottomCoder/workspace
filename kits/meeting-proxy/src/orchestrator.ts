import { spawn, ChildProcess } from 'child_process'
import type { Config } from './config.js'
import { captureFromDevice, AudioCapture } from './audio/input.js'
import { openPlayback, AudioPlayer } from './audio/output.js'
import { ASR, TranscriptEvent } from './asr.js'
import { LLM, buildSystemPrompt } from './llm.js'
import { createTTS } from './tts.js'
import { TriggerState } from './trigger.js'

const SILENT_TOKEN = '[SILENT]'

// Defensive: Claude sometimes wraps tokens in backticks/quotes even when
// the prompt forbids it. Strip common wrappers before comparing.
function isSilentResponse(raw: string): boolean {
  const stripped = raw.trim().replace(/^[`'"*\\\s]+|[`'"*\\\s]+$/g, '').trim()
  return stripped === SILENT_TOKEN || stripped.startsWith(SILENT_TOKEN)
}

export class Orchestrator {
  private capture: AudioCapture | null = null
  private playback: AudioPlayer | null = null
  private monitorPlayback: AudioPlayer | null = null
  private passthrough: ChildProcess | null = null
  private asr: ASR
  private llm: LLM
  private trigger: TriggerState
  private systemPrompt: string
  private isResponding = false
  private fillers: Buffer[] = []
  // Multi-turn memory: alternating user (new speech) / assistant (what we said
  // or [SILENT]) turns, capped to the last 10 exchanges.
  private history: { role: 'user' | 'assistant'; content: string }[] = []

  constructor(private config: Config, context: string) {
    this.asr = new ASR(config.deepgramApiKey)
    this.llm = new LLM(config.anthropicApiKey)
    this.trigger = new TriggerState(config.userName)
    this.systemPrompt = buildSystemPrompt(config.userName, context, config.meetingMode, config.nameSoundalikes)
  }

  start(): void {
    this.playback = openPlayback(this.config.audioOutputDevice)
    // Monitor: also play AI output through the passthrough device so the
    // user hears in real time what the AI is saying on their behalf,
    // and can intervene (Ctrl+C) if needed.
    if (this.config.passthroughDevice) {
      this.monitorPlayback = openPlayback(this.config.passthroughDevice)
      console.log(`[orchestrator] AI monitor: also playing to "${this.config.passthroughDevice}"`)
    }
    this.capture = captureFromDevice(this.config.audioInputDevice)

    // Passthrough: a write-only sox that takes our captured PCM stream and
    // pipes it to the user's headphones. Single reader on BlackHole 16ch
    // (our capture), then we fan out in Node — avoids the buffer-overrun
    // race when two sox processes try to read the same CoreAudio device.
    if (this.config.passthroughDevice) {
      this.passthrough = spawn('sox', [
        '-q',
        '-r', '16000', '-c', '1', '-e', 'signed-integer', '-b', '16', '-t', 'raw', '-',
        '-t', 'coreaudio', this.config.passthroughDevice
      ])
      this.passthrough.stderr?.on('data', (d) => {
        const msg = d.toString().trim()
        if (msg) console.error(`[passthrough] ${msg}`)
      })
      console.log(`[orchestrator] passthrough: "${this.config.audioInputDevice}" -> "${this.config.passthroughDevice}" (single-reader tee)`)
    }

    // Boost recognition of the user's name so it doesn't get misheard as "Holmes" / "hon"
    this.asr.start(16000, [this.config.userName])

    this.capture.stream.on('data', (chunk: Buffer) => {
      this.asr.send(chunk)
      if (this.passthrough?.stdin?.writable) {
        this.passthrough.stdin.write(chunk)
      }
    })

    this.asr.on('transcript', (evt: TranscriptEvent) => {
      this.trigger.add(evt.text, evt.isFinal)
      if (evt.isFinal) console.log(`[asr] ${evt.text}`)
    })

    // Fire LLM evaluation when the speaker actually pauses (UtteranceEnd).
    // This is the natural conversation cue, more reliable than waiting for
    // a "?" in the transcript (which Deepgram doesn't always add for short
    // utterances like "What do you do").
    this.asr.on('utterance-end', () => {
      if (this.trigger.shouldEvaluate() && !this.isResponding) {
        console.log(`[trigger] utterance ended, evaluating...`)
        this.evaluate().catch((err) => {
          console.error('[orchestrator] evaluate failed:', err)
          this.isResponding = false
        })
      }
    })

    console.log(`[orchestrator] listening on "${this.config.audioInputDevice}"`)
    console.log(`[orchestrator] speaking to "${this.config.audioOutputDevice}"`)
    console.log(`[orchestrator] user name: ${this.config.userName}`)
    console.log(`[orchestrator] ready — join your Zoom meeting now`)

    // Pre-synthesize filler clips so a question gets an instant "Hmm, let me
    // think" while the real answer is still generating (fire-and-forget).
    this.prepareFillers().catch((e) => console.error('[filler] prep failed:', e))
  }

  private async prepareFillers(): Promise<void> {
    const texts = [
      'Hmm, let me think.',
      'Uh, yeah, good question.',
      'Right, so...',
      'Yeah, let me see.'
    ]
    for (const t of texts) {
      const chunks: Buffer[] = []
      const tts = createTTS(this.config, (pcm) => chunks.push(pcm))
      await tts.speak(t)
      if (chunks.length) this.fillers.push(Buffer.concat(chunks))
    }
    console.log(`[filler] pre-synthesized ${this.fillers.length} clips`)
  }

  private async evaluate(): Promise<void> {
    this.isResponding = true
    this.trigger.markResponded()

    const transcript = this.trigger.consume()
    if (!transcript) {
      this.isResponding = false
      return
    }

    console.log(`[llm] evaluating: "${transcript.slice(-200)}"`)

    const t0 = Date.now()

    // Instant filler: mask LLM+TTS latency when we're fairly sure a response
    // is coming. 1on1 = any question-ish utterance; group = only when the
    // user's name AND a question mark are present (a stray "hmm" while others
    // talk to each other would be worse than a little latency).
    const tail = transcript.slice(-120)
    const endsWithQuestion = /\?\s*$/.test(tail)
    const hasName = tail.toLowerCase().includes(this.config.userName.toLowerCase())
    const fillerOk = this.config.meetingMode === '1on1'
      ? endsWithQuestion
      : endsWithQuestion && hasName
    if (fillerOk && this.fillers.length > 0) {
      const clip = this.fillers[Math.floor(Math.random() * this.fillers.length)]
      this.playback?.write(clip)
      this.monitorPlayback?.write(clip)
      console.log(`[filler] played (+${Date.now() - t0}ms)`)
    }

    const tts = createTTS(this.config, (pcm) => {
      this.playback?.write(pcm)         // out to Zoom mic
      this.monitorPlayback?.write(pcm)  // out to user's headphones (monitor)
    })

    // Stream sentence-by-sentence: speak each sentence as soon as the LLM
    // finishes it instead of waiting for the full response — cuts perceived
    // latency by the remaining generation time (~1-2s on multi-sentence answers).
    let full = ''
    let pending = ''
    let spokeAny = false
    const speak = async (text: string) => {
      const s = text.trim()
      if (!s) return
      if (!spokeAny) console.log(`[latency] first sentence at +${Date.now() - t0}ms`)
      spokeAny = true
      await tts.speak(s)
    }

    const messages = [...this.history, { role: 'user' as const, content: transcript }]
    for await (const chunk of this.llm.generate(this.systemPrompt, messages)) {
      full += chunk
      // Hold off until we know it isn't a (possibly wrapped) [SILENT] token.
      if (!spokeAny && pending === '' && full.trimStart().startsWith('[')) continue
      pending += chunk
      let m: RegExpMatchArray | null
      while ((m = pending.match(/^[\s\S]*?[.!?](?=\s|$)/)) !== null) {
        const sentence = m[0]
        pending = pending.slice(sentence.length)
        await speak(sentence)
      }
    }
    full = full.trim()

    const remember = (assistantSaid: string) => {
      this.history.push({ role: 'user', content: transcript })
      this.history.push({ role: 'assistant', content: assistantSaid })
      if (this.history.length > 20) this.history = this.history.slice(-20)
    }

    if (isSilentResponse(full) || full === '') {
      console.log(`[llm] -> [SILENT]`)
      remember('[SILENT]')
      this.isResponding = false
      return
    }

    await speak(pending)
    console.log(`[llm] -> "${full}"`)
    remember(full)
    await Promise.all([
      this.playback?.flush(),
      this.monitorPlayback?.flush()
    ])
    console.log(`[tts] done speaking (+${Date.now() - t0}ms total)`)

    // Refresh cooldown after speaking finishes — prevents back-to-back
    // triggers while the AI's own voice is still echoing through the loop.
    this.trigger.markResponded()
    this.isResponding = false
  }

  async stop(): Promise<void> {
    if (this.passthrough?.stdin) {
      this.passthrough.stdin.end()
    }
    this.passthrough?.kill('SIGTERM')
    this.capture?.stop()
    this.asr.stop()
    this.playback?.stop()
    this.monitorPlayback?.stop()
  }
}
