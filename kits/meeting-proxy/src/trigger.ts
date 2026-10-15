interface Segment {
  text: string
  timestamp: number
  isFinal: boolean
}

export class TriggerState {
  private segments: Segment[] = []
  private lastResponseAt = 0
  private readonly windowMs = 30_000
  private readonly cooldownMs = 5_000
  private readonly lookbackMs = 7_000

  constructor(private userName: string) {}

  add(text: string, isFinal: boolean): void {
    const now = Date.now()
    this.segments.push({ text, timestamp: now, isFinal })
    this.segments = this.segments.filter(s => now - s.timestamp < this.windowMs)
  }

  // Permissive pre-filter — fires whenever the speaker pauses (UtteranceEnd)
  // AND we have a non-trivial recent transcript AND cooldown elapsed.
  // The actual "should I respond" judgment is delegated to Claude via [SILENT].
  // Haiku is cheap enough that letting it judge every utterance is fine.
  shouldEvaluate(): boolean {
    const now = Date.now()
    if (now - this.lastResponseAt < this.cooldownMs) return false

    const recent = this.segments
      .filter(s => s.isFinal && now - s.timestamp < this.lookbackMs)
      .map(s => s.text)
      .join(' ')
      .trim()

    if (!recent) return false
    // skip trivial utterances ("yeah", "ok", "mm-hmm")
    if (recent.split(/\s+/).length < 2) return false

    return true
  }

  recentTranscript(): string {
    const now = Date.now()
    return this.segments
      .filter(s => s.isFinal && now - s.timestamp < this.windowMs)
      .map(s => s.text)
      .join(' ')
      .trim()
  }

  // Like recentTranscript but CLEARS the buffer — each evaluation consumes
  // only speech that arrived since the previous one; earlier speech lives in
  // the orchestrator's conversation history instead of being re-sent raw.
  consume(): string {
    const text = this.recentTranscript()
    this.segments = []
    return text
  }

  markResponded(): void {
    this.lastResponseAt = Date.now()
  }
}
