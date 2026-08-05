import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore, type Message } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import type { CharacterId } from '../data/uiContent'

// Headless auto-player for the voice-call page. Watches the character's message
// list and, when a NEW assistant voice message finalises (turn_end stamps a
// durable audioUrl OR live audioData is present), plays it automatically —
// no bubble tap. Mirrors VoiceMessageBubble's auth'd fetch path for /api URLs.
//
// Half-duplex: the call page gates the mic on `isSpeaking`; `stop()` (barge-in)
// halts playback immediately and is also invoked before recording a new turn.
export function useCallAudioPlayer(characterId: CharacterId) {
  const messages = useChatStore((s) => s.messages[characterId] ?? [])
  const [isSpeaking, setIsSpeaking] = useState(false)
  const audioElRef = useRef<HTMLAudioElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)
  const playedIdsRef = useRef<Set<string>>(new Set())
  const seededRef = useRef(false)

  // Seed every message already on screen as "played" BEFORE the auto-play effect
  // can fire. A user-initiated call must open silently — the character speaks
  // only in reply to the user, never by re-reading the last chat bubble on
  // entry (the "发起通话角色播放之前的语音" bug). Runs once, synchronously on the
  // first render, so no historical bubble is ever eligible for auto-play.
  if (!seededRef.current) {
    for (const m of messages) playedIdsRef.current.add(m.id)
    seededRef.current = true
  }

  const cleanupUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [])

  const stop = useCallback(() => {
    const el = audioElRef.current
    if (el) {
      el.pause()
      el.src = ''
    }
    cleanupUrl()
    setIsSpeaking(false)
  }, [cleanupUrl])

  // Resolve a playable object URL for a message's audio. blob:/http play直接；
  // /api 需带 token fetch（by-turn 端点刚落库可能短暂 404，重试几次）。
  const resolveSrc = useCallback(async (msg: Message): Promise<string | null> => {
    const src = msg.audioData?.startsWith('blob:')
      ? msg.audioData
      : (msg.audioUrl || msg.audioData || '')
    if (!src) return null
    if (src.startsWith('blob:') || src.startsWith('http')) return src
    if (!src.startsWith('/api/')) return src

    const { accessToken } = useAuthStore.getState()
    const isByTurn = src.includes('/by-turn/')
    const maxAttempts = isByTurn ? 4 : 1
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await fetch(src, {
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        })
        if (res.ok) {
          const blob = await res.blob()
          cleanupUrl()
          const url = URL.createObjectURL(blob)
          objectUrlRef.current = url
          return url
        }
        if (res.status !== 404 || attempt === maxAttempts - 1) return null
      } catch {
        if (attempt === maxAttempts - 1) return null
      }
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)))
    }
    return null
  }, [cleanupUrl])

  const play = useCallback(async (msg: Message) => {
    const url = await resolveSrc(msg)
    if (!url) return
    let el = audioElRef.current
    if (!el) {
      el = new Audio()
      el.onended = () => setIsSpeaking(false)
      el.onerror = () => setIsSpeaking(false)
      audioElRef.current = el
    }
    el.src = url
    setIsSpeaking(true)
    try {
      await el.play()
    } catch {
      // Autoplay blocked or decode failure — drop the speaking state so the
      // mic unlocks rather than hanging on "对方正在说话".
      setIsSpeaking(false)
    }
  }, [resolveSrc])

  // When the latest assistant message is a finalised voice bubble we haven't
  // played yet, auto-play it. A bubble is "ready" when it has live audioData or
  // a durable audioUrl (stamped at turn_end) — never mid-stream.
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last || last.role !== 'assistant') return
    if (last.kind !== 'voice') return
    if (!last.audioData && !last.audioUrl) return
    if (playedIdsRef.current.has(last.id)) return
    playedIdsRef.current.add(last.id)
    void play(last)
  }, [messages, play])

  useEffect(() => {
    return () => {
      const el = audioElRef.current
      if (el) { el.pause(); el.src = '' }
      cleanupUrl()
    }
  }, [cleanupUrl])

  return { isSpeaking, stop }
}
