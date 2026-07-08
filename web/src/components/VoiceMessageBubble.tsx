import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'
import { FEEDBACK_COPY } from '../data/uiContent'

interface VoiceMessageBubbleProps {
  audioData: string
  duration: number
  format: string
  isDark?: boolean
}

const PLAYING_LEVELS = [
  [10, 16, 12],
  [16, 10, 18],
  [11, 18, 9],
  [18, 12, 15],
]

export default function VoiceMessageBubble({
  audioData,
  duration,
  format,
  isDark = false,
}: VoiceMessageBubbleProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [frameIndex, setFrameIndex] = useState(0)
  const [loadFailed, setLoadFailed] = useState(false)
  const [retryTick, setRetryTick] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const setGlobalPlaying = useChatStore((s) => s.setPlaying)

  useEffect(() => {
    if (!audioData) return
    let cancelled = false
    let blobUrl: string | null = null
    setLoadFailed(false)

    if (audioData.startsWith('http') || audioData.startsWith('blob:')) {
      setAudioUrl(audioData)
      return
    }

    if (audioData.startsWith('/api/')) {
      const { accessToken } = useAuthStore.getState()
      fetch(audioData, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      })
        .then((res) => {
          if (!res.ok) throw new Error(`Audio fetch failed: ${res.status}`)
          return res.blob()
        })
        .then((blob) => {
          if (cancelled) return
          blobUrl = URL.createObjectURL(blob)
          setAudioUrl(blobUrl)
        })
        .catch((err) => {
          if (cancelled) return
          // Previously swallowed silently (SUG-1). 401/403 → provider/auth
          // failure (treat as unavailable); otherwise transient → retryable.
          setLoadFailed(true)
          const permanent = /\b(401|403)\b/.test(String(err?.message ?? ''))
          useToastStore
            .getState()
            .show(permanent ? FEEDBACK_COPY.voiceUnavailable : FEEDBACK_COPY.voiceLoadFailed, 'error')
        })
      return () => {
        cancelled = true
        if (blobUrl) URL.revokeObjectURL(blobUrl)
      }
    }

    if (audioData.startsWith('/')) {
      setAudioUrl(audioData)
      return
    }

    const mimeType = format === 'mp3' ? 'audio/mpeg' : 'audio/wav'
    const byteCharacters = atob(audioData)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: mimeType })
    const url = URL.createObjectURL(blob)
    setAudioUrl(url)

    return () => {
      URL.revokeObjectURL(url)
    }
  }, [audioData, format, retryTick])

  useEffect(() => {
    setGlobalPlaying(isPlaying)
    return () => {
      setGlobalPlaying(false)
    }
  }, [isPlaying, setGlobalPlaying])

  useEffect(() => {
    if (!isPlaying) {
      setFrameIndex(0)
      return
    }
    const timer = window.setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % PLAYING_LEVELS.length)
    }, 220)
    return () => window.clearInterval(timer)
  }, [isPlaying])

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    setIsPlaying(false)
  }, [])

  useEffect(() => {
    return () => {
      stopPlayback()
    }
  }, [stopPlayback])

  useEffect(() => {
    const handleVisibilityStop = () => {
      if (document.hidden) {
        stopPlayback()
      }
    }

    const handlePageHide = () => {
      stopPlayback()
    }

    document.addEventListener('visibilitychange', handleVisibilityStop)
    window.addEventListener('pagehide', handlePageHide)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityStop)
      window.removeEventListener('pagehide', handlePageHide)
    }
  }, [stopPlayback])

  const handlePlayPause = useCallback(() => {
    // Failed to load earlier → tapping retries the fetch instead of a dead no-op.
    if (loadFailed) {
      setRetryTick((t) => t + 1)
      return
    }
    if (!audioUrl) return

    if (isPlaying) {
      stopPlayback()
      return
    }

    const audio = new Audio(audioUrl)
    audioRef.current = audio
    audio.onended = () => stopPlayback()
    audio.onerror = () => {
      stopPlayback()
      useToastStore.getState().show(FEEDBACK_COPY.voiceRetry, 'error')
    }
    audio
      .play()
      .then(() => setIsPlaying(true))
      .catch(() => {
        stopPlayback()
        useToastStore.getState().show(FEEDBACK_COPY.voiceRetry, 'error')
      })
  }, [audioUrl, isPlaying, loadFailed, stopPlayback])

  const durationSeconds = Math.max(1, Math.ceil(duration / 1000))
  const durationLabel = `${durationSeconds}''`
  const bubbleWidth = Math.min(196, Math.max(152, 110 + durationSeconds * 7))
  const bars = isPlaying ? PLAYING_LEVELS[frameIndex] : [8, 12, 16]
  const label = useMemo(
    () => (loadFailed ? '加载失败 · 点此重试' : isPlaying ? '播放中' : '点击收听'),
    [isPlaying, loadFailed],
  )

  return (
    <button
      type="button"
      onClick={handlePlayPause}
      className={`flex h-[56px] items-center gap-3 rounded-[28px] px-4 py-2.5 text-left transition-colors ${
        isDark
          ? 'bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.08))] border border-[rgba(255,255,255,0.08)] hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.16),rgba(255,255,255,0.1))]'
          : 'bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(255,255,255,0.64))] border border-[rgba(255,255,255,0.72)] hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.7))]'
      }`}
      style={{ width: `${bubbleWidth}px`, maxWidth: '100%' }}
    >
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
          isDark ? 'bg-[rgba(255,255,255,0.12)]' : 'bg-[rgba(255,255,255,0.9)]'
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className={`h-[16px] w-[16px] ${isDark ? 'fill-[#F5ECF7]' : 'fill-[#6F7489]'}`}
          aria-hidden="true"
        >
          <path d="M13.5 5.25a.75.75 0 0 1 .75.75v12a.75.75 0 0 1-1.28.53L8.9 14.47H6.75A1.75 1.75 0 0 1 5 12.72V11.3c0-.97.78-1.75 1.75-1.75H8.9l4.07-4.08a.75.75 0 0 1 .53-.22Zm3.31 2.16a.75.75 0 0 1 1.06.06 6.8 6.8 0 0 1 0 9.06.75.75 0 0 1-1.12-1 5.3 5.3 0 0 0 0-7.06.75.75 0 0 1 .06-1.06Zm-1.9 1.78a.75.75 0 0 1 1.06.06 4 4 0 0 1 0 5.3.75.75 0 1 1-1.12-1 2.5 2.5 0 0 0 0-3.3.75.75 0 0 1 .06-1.06Z" />
        </svg>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex h-[18px] items-end gap-[3px]">
          {bars.map((height, index) => (
            <span
              key={index}
              className={`block w-[3px] shrink-0 self-end rounded-full transition-[height,opacity] duration-150 ${
                isDark ? 'bg-[#EED9E8]' : 'bg-[#9196AA]'
              }`}
              style={{ height: `${height}px`, opacity: isPlaying ? 1 : 0.72 }}
            />
          ))}
        </div>
        <p className={`mt-1 whitespace-nowrap text-[11px] leading-none ${isDark ? 'text-[rgba(245,236,247,0.68)]' : 'text-[rgba(111,116,137,0.72)]'}`}>
          {label}
        </p>
      </div>

      <span className={`shrink-0 text-[13px] font-medium ${isDark ? 'text-[rgba(245,236,247,0.78)]' : 'text-[rgba(111,116,137,0.88)]'}`}>
        {durationLabel}
      </span>
    </button>
  )
}
