import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import type { CharacterId } from '../data/uiContent'

// Headless auto-player for the voice-call page. Plays a character reply
// PROGRESSIVELY: the backend now streams one audio chunk per sentence (sentence
// pipeline), so instead of waiting for turn_end to concat the whole reply, we
// decode + play each sentence the instant it lands and queue the rest. The
// character starts speaking sentence 1 while sentences 2..N are still being
// generated — this is the latency win over the old "wait for full audioData".
//
// Half-duplex: the call page gates the mic on `isSpeaking`. `stop()` (barge-in,
// also called before recording a new turn) halts playback and clears the queue.
type QueueItem = { turnId: string; seq: number; dataB64: string; format: 'wav' | 'mp3' }

export function useCallAudioPlayer(characterId: CharacterId) {
  const messages = useChatStore((s) => s.messages[characterId] ?? [])
  const streaming = useChatStore((s) => s.isStreaming[characterId] ?? false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  const audioElRef = useRef<HTMLAudioElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)
  const queueRef = useRef<QueueItem[]>([])
  const enqueuedRef = useRef<Set<string>>(new Set()) // `${turnId}:${seq}` already queued
  const pumpingRef = useRef(false)
  const genRef = useRef(0) // bumped on stop() to invalidate in-flight playback
  const streamingRef = useRef(false)
  const seededRef = useRef(false)

  useEffect(() => { streamingRef.current = streaming }, [streaming])

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

  const cleanupUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [])

  const stop = useCallback(() => {
    genRef.current += 1 // invalidate any awaiting pump / play
    queueRef.current = []
    pumpingRef.current = false
    const el = audioElRef.current
    if (el) {
      el.pause()
      el.src = ''
    }
    cleanupUrl()
    setIsSpeaking(false)
  }, [cleanupUrl])

  // Decode one self-contained chunk (wav or mp3) to a blob URL and play it,
  // resolving when it finishes (or fails). Rejects nothing — a bad chunk just
  // resolves so the pump moves on.
  const playChunk = useCallback((item: QueueItem, gen: number): Promise<void> => {
    return new Promise((resolve) => {
      let buf: ArrayBuffer
      try {
        // Decode into a concrete ArrayBuffer and pass THAT as the BlobPart — a
        // Uint8Array infers Uint8Array<ArrayBufferLike> under tsc -b and fails
        // the BlobPart assignment (SharedArrayBuffer vs ArrayBuffer). ArrayBuffer
        // is unambiguously a BlobPart.
        const bin = atob(item.dataB64)
        buf = new ArrayBuffer(bin.length)
        const view = new Uint8Array(buf)
        for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i)
      } catch {
        resolve()
        return
      }
      const mime = item.format === 'mp3' ? 'audio/mpeg' : 'audio/wav'
      cleanupUrl()
      const url = URL.createObjectURL(new Blob([buf], { type: mime }))
      objectUrlRef.current = url

      let el = audioElRef.current
      if (!el) {
        el = new Audio()
        audioElRef.current = el
      }
      const done = () => {
        el!.onended = null
        el!.onerror = null
        resolve()
      }
      el.onended = done
      el.onerror = done
      el.src = url
      if (genRef.current !== gen) { resolve(); return } // stopped mid-setup
      void el.play().catch(() => resolve())
    })
  }, [cleanupUrl])

  // Drain the queue in seq order. Keeps `isSpeaking` true across the gap between
  // a played sentence and the next one still being synthesized — only releases
  // the mic when the queue is empty AND the turn has stopped streaming.
  const pump = useCallback(async () => {
    if (pumpingRef.current) return
    pumpingRef.current = true
    const gen = genRef.current
    setIsSpeaking(true)
    while (genRef.current === gen) {
      const item = queueRef.current.shift()
      if (item) {
        await playChunk(item, gen)
        continue
      }
      // Queue drained. If the turn is still streaming, wait for more sentences;
      // otherwise the reply is over.
      if (!streamingRef.current) break
      await new Promise((r) => setTimeout(r, 80))
    }
    if (genRef.current === gen) {
      pumpingRef.current = false
      if (queueRef.current.length === 0) setIsSpeaking(false)
    }
  }, [playChunk])

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
      const el = audioElRef.current
      if (el) { el.pause(); el.src = '' }
      cleanupUrl()
    }
  }, [cleanupUrl])

  return { isSpeaking, stop }
}
