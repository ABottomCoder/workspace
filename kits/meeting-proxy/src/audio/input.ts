import { spawn } from 'child_process'
import { Readable } from 'stream'

export interface AudioCapture {
  stream: Readable
  stop: () => void
}

export function captureFromDevice(deviceName: string, sampleRate = 16000): AudioCapture {
  const sox = spawn('sox', [
    '-q',
    '-t', 'coreaudio', deviceName,
    '-r', String(sampleRate),
    '-c', '1',
    '-e', 'signed-integer',
    '-b', '16',
    '-t', 'raw',
    '-'
  ])

  sox.stderr.on('data', (d) => {
    const msg = d.toString().trim()
    if (msg) console.error(`[sox-in] ${msg}`)
  })

  sox.on('exit', (code, signal) => {
    if (code !== 0 && code !== null && signal !== 'SIGTERM') {
      console.error(`[sox-in] exited with code ${code}`)
    }
  })

  return {
    stream: sox.stdout,
    stop: () => sox.kill('SIGTERM')
  }
}
