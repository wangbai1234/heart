import { useCallback, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'

// Streaming ASR for the voice CALL page (push-to-talk, 边说边转).
//
// While the mic button is held we capture raw PCM16 16kHz mono frames and
// stream them to the backend WS (/api/voice/asr-stream), which bridges to Qwen
// realtime ASR. On release we send {type:"commit"} and resolve with the final
// transcript — because transcription happened DURING the hold, the transcript
// is essentially ready the instant the user lets go (no post-release upload +
// full-file ASR latency like the old MiMo /transcribe flow).
//
// We also accumulate all PCM locally so the voice bubble still gets a WAV blob
// to play back, matching the previous recorder's RecordResult shape.

const TARGET_RATE = 16000

interface StreamResult {
  transcript: string
  wavBlob: Blob
  durationMs: number
}

interface StartOptions {
  onPartial?: (text: string) => void
}

function wsBase(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/api/voice/asr-stream`
}

function floatTo16k(input: Float32Array, srcRate: number): Int16Array {
  // Downsample (linear) src → 16k, then float[-1,1] → int16.
  const ratio = srcRate / TARGET_RATE
  const outLen = Math.floor(input.length / ratio)
  const out = new Int16Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const s = Math.max(-1, Math.min(1, input[Math.floor(i * ratio)]))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out
}

function encodeWav(pcm: Int16Array, sampleRate: number): Blob {
  const dataLen = pcm.length * 2
  const buf = new ArrayBuffer(44 + dataLen)
  const view = new DataView(buf)
  const writeStr = (o: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + dataLen, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, dataLen, true)
  let offset = 44
  for (let i = 0; i < pcm.length; i++) {
    view.setInt16(offset, pcm[i], true)
    offset += 2
  }
  return new Blob([buf], { type: 'audio/wav' })
}

export function useStreamingAsr() {
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const nodeRef = useRef<ScriptProcessorNode | null>(null)
  const srcNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const pcmChunksRef = useRef<Int16Array[]>([])
  const readyRef = useRef(false)
  const pendingRef = useRef<Int16Array[]>([])
  const finalRef = useRef<string>('')
  const finalResolveRef = useRef<((t: string) => void) | null>(null)
  const startTimeRef = useRef(0)
  const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const teardownAudio = useCallback(() => {
    if (autoStopRef.current) {
      clearTimeout(autoStopRef.current)
      autoStopRef.current = null
    }
    try {
      nodeRef.current?.disconnect()
      srcNodeRef.current?.disconnect()
    } catch { /* already gone */ }
    nodeRef.current = null
    srcNodeRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const start = useCallback(async (opts?: StartOptions): Promise<void> => {
    const { accessToken } = useAuthStore.getState()
    if (!accessToken) throw new Error('未登录')

    pcmChunksRef.current = []
    pendingRef.current = []
    readyRef.current = false
    finalRef.current = ''

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream

    const AC = (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext })
    const Ctor = AC.AudioContext ?? AC.webkitAudioContext
    if (!Ctor) throw new Error('浏览器不支持录音')
    const ctx = new Ctor()
    ctxRef.current = ctx
    const srcRate = ctx.sampleRate

    // Open the backend WS. Frames captured before "ready" are buffered and
    // flushed once the Qwen session is live so we never drop the first words.
    const ws = new WebSocket(`${wsBase()}?token=${accessToken}`)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws
    ws.onmessage = (e) => {
      let msg: { type?: string; text?: string }
      try { msg = JSON.parse(e.data as string) } catch { return }
      if (msg.type === 'ready') {
        readyRef.current = true
        for (const chunk of pendingRef.current) {
          if (ws.readyState === WebSocket.OPEN) ws.send(chunk.buffer as ArrayBuffer)
        }
        pendingRef.current = []
      } else if (msg.type === 'partial' && msg.text) {
        opts?.onPartial?.(msg.text)
      } else if (msg.type === 'final') {
        finalRef.current = msg.text ?? ''
        finalResolveRef.current?.(finalRef.current)
        finalResolveRef.current = null
      } else if (msg.type === 'error') {
        // Degrade: resolve with whatever we have (usually empty) so the caller
        // can show a friendly toast rather than hang.
        finalResolveRef.current?.(finalRef.current)
        finalResolveRef.current = null
      }
    }

    const node = ctx.createScriptProcessor(4096, 1, 1)
    nodeRef.current = node
    const source = ctx.createMediaStreamSource(stream)
    srcNodeRef.current = source
    node.onaudioprocess = (ev) => {
      const pcm16 = floatTo16k(ev.inputBuffer.getChannelData(0), srcRate)
      pcmChunksRef.current.push(pcm16)
      if (readyRef.current && ws.readyState === WebSocket.OPEN) {
        ws.send(pcm16.buffer as ArrayBuffer)
      } else {
        pendingRef.current.push(pcm16)
      }
    }
    source.connect(node)
    node.connect(ctx.destination)
    startTimeRef.current = performance.now()

    // Hard cap the utterance at 60s to match the old recorder.
    autoStopRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'commit' }))
      }
    }, 60_000)
  }, [])

  const stop = useCallback(
    async (opts?: { cancel?: boolean }): Promise<StreamResult | null> => {
      const ws = wsRef.current
      const durationMs = Math.round(performance.now() - startTimeRef.current)
      teardownAudio()

      if (opts?.cancel) {
        if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'cancel' }))
        ws?.close()
        wsRef.current = null
        return null
      }

      // Assemble the WAV from everything we captured (for the voice bubble).
      const total = pcmChunksRef.current.reduce((n, c) => n + c.length, 0)
      if (durationMs < 800 || total === 0) {
        if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'cancel' }))
        ws?.close()
        wsRef.current = null
        return null
      }
      const merged = new Int16Array(total)
      let off = 0
      for (const c of pcmChunksRef.current) { merged.set(c, off); off += c.length }
      const wavBlob = encodeWav(merged, TARGET_RATE)

      // Ask for the final transcript, then wait (bounded) for it to land.
      const transcript = await new Promise<string>((resolve) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) { resolve(finalRef.current); return }
        finalResolveRef.current = resolve
        // Flush any still-pending frames before committing.
        for (const chunk of pendingRef.current) ws.send(chunk.buffer as ArrayBuffer)
        pendingRef.current = []
        ws.send(JSON.stringify({ type: 'commit' }))
        setTimeout(() => {
          if (finalResolveRef.current) { finalResolveRef.current = null; resolve(finalRef.current) }
        }, 8000)
      })
      ws?.close()
      wsRef.current = null

      return { transcript: transcript.trim(), wavBlob, durationMs }
    },
    [teardownAudio],
  )

  return { start, stop }
}
