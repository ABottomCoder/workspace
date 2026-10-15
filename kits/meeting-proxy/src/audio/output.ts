import { spawn, ChildProcessWithoutNullStreams } from 'child_process'

export interface AudioPlayer {
  write: (pcm: Buffer) => void
  flush: () => Promise<void>
  stop: () => void
}

export function openPlayback(deviceName: string, sampleRate = 16000): AudioPlayer {
  let sox: ChildProcessWithoutNullStreams | null = null
  let exited = false

  const spawnSox = () => {
    sox = spawn('sox', [
      '-q',
      '-r', String(sampleRate),
      '-c', '1',
      '-e', 'signed-integer',
      '-b', '16',
      '-t', 'raw',
      '-',
      '-t', 'coreaudio', deviceName
    ])

    sox.stderr.on('data', (d) => {
      const msg = d.toString().trim()
      if (msg) console.error(`[sox-out] ${msg}`)
    })

    sox.on('exit', () => { exited = true })
  }

  spawnSox()

  return {
    write: (pcm: Buffer) => {
      if (sox && !exited && sox.stdin.writable) {
        sox.stdin.write(pcm)
      }
    },
    // After each TTS utterance we end stdin so sox flushes its buffer to the
    // virtual device, then we spin up a fresh sox for the next utterance.
    // (Easier than dealing with sox's persistent-mode quirks.)
    flush: () => new Promise<void>((resolve) => {
      if (!sox || exited) {
        spawnSox()
        exited = false
        resolve()
        return
      }
      sox.once('exit', () => {
        spawnSox()
        exited = false
        resolve()
      })
      sox.stdin.end()
    }),
    stop: () => {
      if (sox && !exited) {
        sox.stdin.end()
        sox.kill('SIGTERM')
      }
    }
  }
}
