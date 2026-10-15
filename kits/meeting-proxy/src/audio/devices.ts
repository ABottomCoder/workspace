import { execSync } from 'child_process'

function listViaSystemProfiler(): void {
  console.log('=== system_profiler SPAudioDataType ===\n')
  try {
    const output = execSync('system_profiler SPAudioDataType', { encoding: 'utf-8' })
    console.log(output)
  } catch (e) {
    console.error('system_profiler failed:', e)
  }
}

function listViaSox(): void {
  console.log('\n=== sox -V6 CoreAudio probe ===\n')
  try {
    // sox dumps the audio device list at verbose level 6 when initializing.
    const output = execSync(
      'sox -V6 -n -t coreaudio default trim 0 0.001 2>&1 | grep -i "Audio Device\\|BlackHole\\|coreaudio" | head -50 || true',
      { encoding: 'utf-8', shell: '/bin/zsh' }
    )
    console.log(output || '(no matching lines — try running `sox -V6 -n -t coreaudio default trim 0 0.001` manually)')
  } catch (e) {
    console.error('sox probe failed:', e)
  }
}

listViaSystemProfiler()
listViaSox()
