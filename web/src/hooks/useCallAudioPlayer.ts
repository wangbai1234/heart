import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import type { CharacterId } from '../data/uiContent'
import { decodeCallChunk } from '../services/callAudioDecode'

// Headless auto-player for the voice-call page. Plays a character reply
// PROGRESSIVELY via the Web Audio API: the backend streams audio frames the
// instant each is synthesized, so we decode + SCHEDULE each frame on the
// AudioContext timeline the moment it lands. The character starts speaking
// while later frames are still being generated — that's the latency win, and
// timeline scheduling makes the frames play gaplessly (no click between them).
//
// Why Web Audio and not one <audio> element per frame: realtime frames are
// slices of one continuous stream (Fish wav = header + PCM continuation) and
// are NOT independently decodable — a lone slice fails silently in <audio>,
// which was the "call has no sound" bug. We hand-build AudioBuffers from the
// linear PCM instead (see callAudioDecode). mp3 frames (REST fallback, which
// sends one self-contained file per sentence) go through decodeAudioData.
//
// Half-duplex: the call page gates the mic on `isSpeaking`. `stop()` (barge-in,
// also called before recording a new turn) halts playback and clears the queue.
type QueueItem = {
  turnId: string
  seq: number
  dataB64: string
  format: 'wav' | 'mp3'
  sampleRate?: number
}

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

export function useCallAudioPlayer(characterId: CharacterId) {
  const messages = useChatStore((s) => s.messages[characterId] ?? [])
  const streaming = useChatStore((s) => s.isStreaming[characterId] ?? false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  const ctxRef = useRef<AudioContext | null>(null)
  const queueRef = useRef<QueueItem[]>([])
  const enqueuedRef = useRef<Set<string>>(new Set()) // `${turnId}:${seq}` already queued
  const pumpingRef = useRef(false)
  const genRef = useRef(0) // bumped on stop() to invalidate in-flight playback
  const streamingRef = useRef(false)
  const seededRef = useRef(false)
  // The AudioContext-clock time at which the next frame should start. When the
  // queue keeps up this stays ahead of currentTime and frames butt seamlessly;
  // when it falls behind (currentTime caught up) we resync to "play now".
  const nextStartRef = useRef(0)
  const activeSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set())

  useEffect(() => { streamingRef.current = streaming }, [streaming])

  // Lazily create (and resume) the AudioContext. Called from a user gesture
  // (mic press) so iOS/Android unlock it; safe to call repeatedly.
  const ensureCtx = useCallback((): AudioContext | null => {
    if (!ctxRef.current) {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Ctor) return null
      ctxRef.current = new Ctor()
    }
    if (ctxRef.current.state === 'suspended') void ctxRef.current.resume()
    return ctxRef.current
  }, [])

  // Seed every message already on screen as "handled" so a fresh call opens
  // silently — the character speaks only in reply, never by re-reading history.
  if (!seededRef.current) {
    for (const m of messages) {
      const chunks = m.audioChunks ?? []
      for (const c of chunks) enqueuedRef.current.add(`${m.id}:${c.seq}`)
      // Historical bubbles carry concatenated audioData (no live chunks); mark a
      // sentinel so the enqueue effect below never replays them.
      if (!chunks.length) enqueuedRef.current.add(`${m.id}:full`)
    }
    seededRef.current = true
  }

  const stop = useCallback(() => {
    genRef.current += 1 // invalidate any awaiting pump / scheduled tail
    queueRef.current = []
    pumpingRef.current = false
    nextStartRef.current = 0
    for (const src of activeSourcesRef.current) {
      try { src.onended = null; src.stop() } catch { /* already stopped */ }
    }
    activeSourcesRef.current.clear()
    setIsSpeaking(false)
  }, [])

  // Turn one chunk's bytes into an AudioBuffer. wav/pcm frames are hand-built
  // from linear PCM (they are NOT standalone-decodable); mp3 frames are
  // self-contained REST files decoded by the browser. Returns null on any
  // failure so the pump just skips that frame.
  const decodeToBuffer = useCallback(
    async (item: QueueItem, ctx: AudioContext): Promise<AudioBuffer | null> => {
      const bytes = b64ToBytes(item.dataB64)
      if (item.format === 'mp3') {
        try {
          const copy = bytes.slice().buffer
          return await ctx.decodeAudioData(copy)
        } catch {
          return null
        }
      }
      const decoded = decodeCallChunk(bytes, item.sampleRate ?? 0)
      if (!decoded || decoded.samples.length === 0) return null
      const buf = ctx.createBuffer(1, decoded.samples.length, decoded.sampleRate)
      buf.getChannelData(0).set(decoded.samples)
      return buf
    },
    [],
  )

  // Schedule a decoded buffer to start exactly when the previous one ends, so
  // frames play back-to-back with no click. Resyncs to "now" if we fell behind.
  const scheduleBuffer = useCallback((buf: AudioBuffer, ctx: AudioContext, gen: number) => {
    if (genRef.current !== gen) return
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)
    const now = ctx.currentTime
    const startAt = Math.max(now, nextStartRef.current)
    src.start(startAt)
    nextStartRef.current = startAt + buf.duration
    activeSourcesRef.current.add(src)
    src.onended = () => { activeSourcesRef.current.delete(src) }
  }, [])

  // Drain the queue in seq order: decode each frame and schedule it on the
  // timeline immediately (non-blocking — scheduling returns at once, the audio
  // plays later). Keeps `isSpeaking` true until the queue is empty, the turn has
  // stopped streaming, AND the scheduled tail has finished playing — only then
  // is the mic released.
  const pump = useCallback(async () => {
    if (pumpingRef.current) return
    const ctx = ensureCtx()
    if (!ctx) return
    pumpingRef.current = true
    const gen = genRef.current
    setIsSpeaking(true)
    while (genRef.current === gen) {
      const item = queueRef.current.shift()
      if (item) {
        const buf = await decodeToBuffer(item, ctx)
        if (buf && genRef.current === gen) scheduleBuffer(buf, ctx, gen)
        continue
      }
      // Queue drained. Still streaming → wait for more frames. Otherwise wait
      // out any audio still scheduled ahead of the clock before releasing.
      if (streamingRef.current || ctx.currentTime < nextStartRef.current) {
        await new Promise((r) => setTimeout(r, 80))
        continue
      }
      break
    }
    if (genRef.current === gen) {
      pumpingRef.current = false
      if (queueRef.current.length === 0) setIsSpeaking(false)
    }
  }, [ensureCtx, decodeToBuffer, scheduleBuffer])

  // Watch the latest assistant voice turn and enqueue any chunk we haven't seen.
  // Fires on every appendMessageAudio (store returns a fresh array per chunk).
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last || last.role !== 'assistant' || last.kind !== 'voice') return
    const chunks = last.audioChunks ?? []
    let added = false
    for (const c of chunks) {
      const key = `${last.id}:${c.seq}`
      if (enqueuedRef.current.has(key)) continue
      enqueuedRef.current.add(key)
      queueRef.current.push({
        turnId: last.id,
        seq: c.seq,
        dataB64: c.dataB64,
        format: c.format === 'mp3' ? 'mp3' : 'wav',
        sampleRate: c.sampleRate,
      })
      added = true
    }
    if (added) {
      queueRef.current.sort((a, b) => a.seq - b.seq)
      void pump()
    }
  }, [messages, pump])

  useEffect(() => {
    return () => {
      genRef.current += 1
      for (const src of activeSourcesRef.current) {
        try { src.onended = null; src.stop() } catch { /* already stopped */ }
      }
      activeSourcesRef.current.clear()
      const ctx = ctxRef.current
      ctxRef.current = null
      if (ctx) void ctx.close().catch(() => {})
    }
  }, [])

  // Unlock the AudioContext from a real user gesture (the mic press). iOS/
  // Android block audio until a gesture resumes a context; doing it here means
  // the later WS-driven scheduling actually produces sound.
  const unlock = useCallback(() => { ensureCtx() }, [ensureCtx])

  return { isSpeaking, stop, unlock }
}
