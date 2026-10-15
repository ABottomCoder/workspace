import type { Config } from './config.js'
import { DeepgramTTS } from './tts-deepgram.js'
import { ElevenLabsTTS } from './tts-elevenlabs.js'

export interface TTSProvider {
  speak(text: string): Promise<void>
}

export function createTTS(config: Config, onAudio: (pcm: Buffer) => void): TTSProvider {
  if (config.ttsProvider === 'elevenlabs') {
    if (!config.elevenlabsApiKey || !config.elevenlabsVoiceId) {
      throw new Error('TTS_PROVIDER=elevenlabs but ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID is missing')
    }
    return new ElevenLabsTTS(config.elevenlabsApiKey, config.elevenlabsVoiceId, config.elevenlabsSpeed, onAudio)
  }
  return new DeepgramTTS(config.deepgramApiKey, config.deepgramTtsModel, onAudio)
}
