import 'dotenv/config'
import { readFileSync } from 'fs'

export type TTSProviderName = 'deepgram' | 'elevenlabs'
export type MeetingMode = 'group' | '1on1'

export interface Config {
  anthropicApiKey: string
  deepgramApiKey: string
  deepgramTtsModel: string
  ttsProvider: TTSProviderName
  elevenlabsApiKey?: string
  elevenlabsVoiceId?: string
  elevenlabsSpeed: number
  audioInputDevice: string
  audioOutputDevice: string
  passthroughDevice?: string
  userName: string
  nameSoundalikes: string[]
  contextPath: string
  meetingMode: MeetingMode
}

export function loadConfig(contextPath: string): Config {
  const required = (k: string): string => {
    const v = process.env[k]
    if (!v) throw new Error(`Missing required env var: ${k}`)
    return v
  }

  const ttsProvider = (process.env.TTS_PROVIDER ?? 'deepgram') as TTSProviderName
  if (ttsProvider !== 'deepgram' && ttsProvider !== 'elevenlabs') {
    throw new Error(`TTS_PROVIDER must be "deepgram" or "elevenlabs", got "${ttsProvider}"`)
  }

  const meetingMode = (process.env.MEETING_MODE ?? 'group') as MeetingMode
  if (meetingMode !== 'group' && meetingMode !== '1on1') {
    throw new Error(`MEETING_MODE must be "group" or "1on1", got "${meetingMode}"`)
  }

  return {
    anthropicApiKey: required('ANTHROPIC_API_KEY'),
    deepgramApiKey: required('DEEPGRAM_API_KEY'),
    deepgramTtsModel: process.env.DEEPGRAM_TTS_MODEL ?? 'aura-2-thalia-en',
    ttsProvider,
    elevenlabsApiKey: process.env.ELEVENLABS_API_KEY,
    elevenlabsVoiceId: process.env.ELEVENLABS_VOICE_ID,
    elevenlabsSpeed: parseFloat(process.env.ELEVENLABS_SPEED ?? '0.9'),
    audioInputDevice: process.env.AUDIO_INPUT_DEVICE ?? 'BlackHole 16ch',
    audioOutputDevice: process.env.AUDIO_OUTPUT_DEVICE ?? 'BlackHole 2ch',
    passthroughDevice: process.env.PASSTHROUGH_DEVICE || undefined,
    userName: required('USER_NAME'),
    nameSoundalikes: (process.env.NAME_SOUNDALIKES ?? '').split(',').map(s => s.trim()).filter(Boolean),
    contextPath,
    meetingMode
  }
}

export function loadContext(path: string): string {
  return readFileSync(path, 'utf-8')
}
