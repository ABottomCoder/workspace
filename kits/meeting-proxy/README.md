# meeting-proxy (macOS only)

An AI stand-in for video meetings (tested with Zoom). It listens to the meeting, decides when you
are being addressed, and answers in a synthetic or cloned voice using a context file you write
before the meeting. Stays silent otherwise, defers commitments, refuses anything outside the context.

**Platform: macOS only.** Audio goes through BlackHole virtual devices and sox's `coreaudio`
driver; the launcher uses `SwitchAudioSource` and `osascript`; `MeetingProxy.app` is a macOS app
bundle. Files that only run on macOS carry `.mac` in their name (`bin/*.mac.sh`); `src/` also
assumes CoreAudio throughout. A Linux port would need a PulseAudio/PipeWire variant of the
routing scripts and the `-t coreaudio` calls.

## Stack

Node 20+ / TypeScript / tsx · sox · Deepgram `nova-2` streaming ASR · Claude (streaming, prompt
caching) for the reply · TTS: Deepgram Aura-2 (default) or an ElevenLabs voice clone. Target
end-to-end latency is about 1.5 to 2.5 s.

## Install

```bash
brew install sox node switchaudio-osx
brew install --cask blackhole-2ch blackhole-16ch   # reboot if the devices do not appear
npm install
cp .env.example .env                                # API keys, USER_NAME, devices
npm run list-devices                                # must show BlackHole 2ch and BlackHole 16ch
```

One-time: in Zoom, Settings, Audio, set Speaker **and** Microphone to "Same as System", and grant
Terminal microphone permission when asked.

## Usage

Write a context file per meeting (`context/` is gitignored):

```bash
cp context-templates/example.md context/weekly-sync.md   # edit it
```

Then either double-click `MeetingProxy.app` (it opens Terminal and runs the launcher) or run
`npm run meeting` (picks the context: one file is used directly, several give a menu). The launcher:

1. Preflights sox, SwitchAudioSource, node_modules, both BlackHole devices.
2. Saves your audio defaults to `tmp/audio-state.prev`.
3. Routes: system output to BlackHole 16ch (forced to 100% volume), system input to BlackHole 2ch,
   alert sounds to your real output.
4. Starts a sox mic bridge: your headset (or built-in) mic into BlackHole 2ch, so Zoom hears you and the AI.
5. Runs the proxy; you hear the meeting through a passthrough tee to your previous output device.

Stop with Ctrl+C or by closing the window; audio is restored either way. After a hard crash the
next launch restores from the leftover state file, or run `npm run restore-audio`.

Manual run: `npm start -- --context context/weekly-sync.md`.

Audio topology:

```
Zoom speaker -> BlackHole 16ch -> proxy (ASR -> LLM -> TTS) -> BlackHole 2ch -> Zoom mic
                     |                                             ^
                     +--> passthrough -> your headphones           +-- sox bridge <- your mic
```

## Configuration

`.env` (see `.env.example`): `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `USER_NAME` (required),
`NAME_SOUNDALIKES` (words ASR mishears your name as), `MEETING_MODE` (`group` or `1on1`),
`TTS_PROVIDER`, `DEEPGRAM_TTS_MODEL`, `ELEVENLABS_*`, `AUDIO_INPUT_DEVICE`, `AUDIO_OUTPUT_DEVICE`,
`PASSTHROUGH_DEVICE`.

Launcher environment overrides (device names differ per Mac): `MP_HEADSET_MIC` (default
`External Microphone`), `MP_BUILTIN_INPUT` (`MacBook Pro Microphone`), `MP_BUILTIN_OUTPUT`
(`MacBook Pro Speakers`).

Voice clone: on an ElevenLabs plan with Instant Voice Cloning, upload 1 to 3 minutes of your
speech, put the voice ID in `.env`, set `TTS_PROVIDER=elevenlabs`. No code change.

## Diagnostics

`npm run test-loop` (capture then replay), and the scripts in `src/checks/` (run with
`npx tsx src/checks/<name>.ts`): `check-asr`, `check-llm`, `check-tts`, `check-routing`,
`check-route2-long`, `check-blackhole-loopback`, `check-which-blackhole`. They write scratch audio to `tmp/`.

## Gotchas

- **Silent attenuators.** "Level meter moves but no sound" is usually BlackHole's own volume slider
  rolled down or the monitor device muted. The launcher forces BlackHole 16ch to 100% and raises a
  muted or near-zero monitor to 40.
- **Aggregate devices do not work as Zoom's mic**: Zoom reads only the first sub-device stream.
  That is why the mic goes through a sox bridge into BlackHole 2ch.
- Built-in mic plus speakers as monitor can echo; use a headset.
- Short names are often mis-transcribed; the name is boosted in ASR and `NAME_SOUNDALIKES` helps the prompt.
- Sample rate is 16 kHz throughout; changing one stage means changing all.
- Device names are case- and space-sensitive; copy them from `npm run list-devices`.

## Known limitations

- No takeover hotkey; Ctrl+C is the kill switch.
- Naive speaker handling (Deepgram returns the merged stream); a cooldown in `src/trigger.ts`
  limits self-triggering on its own voice.
- Only Zoom has been tested; Meet or Teams should work with the same device settings.
- Using an AI stand-in in a meeting may require the other participants' consent; check your
  organisation's rules and local law before recording or speaking on someone's behalf.
