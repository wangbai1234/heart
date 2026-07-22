import { useRef, useCallback } from 'react'
import { blobToWav16k } from '../services/audioRecorder'

export type RecorderState = 'idle' | 'recording' | 'willCancel'

interface RecordResult {
  wavBlob: Blob
  durationMs: number
}

export function useVoiceRecorder() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startTimeRef = useRef<number>(0)
  const autoStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const _stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const start = useCallback(async (): Promise<void> => {
    chunksRef.current = []
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream

    const mr = new MediaRecorder(stream)
    mediaRecorderRef.current = mr

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    // No timeslice: all audio arrives in one chunk when stop() fires.
    // Using a timeslice (e.g. 100ms) risks losing the final partial chunk in
    // some browsers when stop() is called before the next slice boundary.
    mr.start()
    startTimeRef.current = performance.now()

    autoStopTimerRef.current = setTimeout(() => {
      if (mr.state === 'recording') mr.stop()
    }, 60_000)
  }, [])

  const stop = useCallback(
    async (opts?: { cancel?: boolean }): Promise<RecordResult | null> => {
      if (autoStopTimerRef.current) {
        clearTimeout(autoStopTimerRef.current)
        autoStopTimerRef.current = null
      }

      const mr = mediaRecorderRef.current
      if (!mr) {
        _stopStream()
        return null
      }
      mediaRecorderRef.current = null

      if (opts?.cancel || mr.state === 'inactive') {
        if (mr.state === 'recording') mr.stop()
        _stopStream()
        return null
      }

      const durationMs = Math.round(performance.now() - startTimeRef.current)

      if (mr.state === 'recording') {
        await new Promise<void>((resolve) => {
          mr.addEventListener('stop', () => resolve(), { once: true })
          mr.stop()
        })
      }
      _stopStream()

      // Minimum duration guard (~800ms) to avoid uploading accidental taps
      if (durationMs < 800 || chunksRef.current.length === 0) return null

      const raw = new Blob(chunksRef.current, { type: chunksRef.current[0]?.type || 'audio/webm' })
      const wavBlob = await blobToWav16k(raw)
      return { wavBlob, durationMs }
    },
    [_stopStream],
  )

  return { start, stop }
}
