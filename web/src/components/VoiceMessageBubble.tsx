import { useState, useEffect, useCallback } from 'react'

interface VoiceMessageBubbleProps {
  audioData: string // base64 WAV 音频
  duration: number  // 时长（毫秒）
  format: string    // "wav"
}

export default function VoiceMessageBubble({ audioData, duration, format }: VoiceMessageBubbleProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

  // 将 base64 转为 Blob URL
  useEffect(() => {
    if (!audioData) return

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
  }, [audioData, format])

  const handlePlayPause = useCallback(() => {
    if (!audioUrl) return

    const audio = new Audio(audioUrl)

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      audio.play().then(() => {
        setIsPlaying(true)
        audio.onended = () => setIsPlaying(false)
      }).catch(console.error)
    }
  }, [audioUrl, isPlaying])

  const durationSeconds = Math.ceil(duration / 1000)
  const bubbleWidth = Math.min(200, Math.max(80, durationSeconds * 10))

  return (
    <button
      onClick={handlePlayPause}
      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-surface-light)] hover:bg-[var(--color-surface)] transition-colors"
      style={{ width: `${bubbleWidth}px` }}
    >
      {/* 播放/暂停图标 */}
      <div className="w-4 h-4 flex-shrink-0">
        {isPlaying ? (
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-[var(--color-primary)]">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-[var(--color-text-secondary)]">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </div>

      {/* 播放动画条纹 */}
      <div className="flex items-center gap-1 flex-1">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={`w-1 bg-[var(--color-text-secondary)] rounded-full ${
              isPlaying ? 'animate-pulse' : ''
            }`}
            style={{
              height: `${8 + Math.random() * 8}px`,
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>

      {/* 时长显示 */}
      <span className="text-xs text-[var(--color-text-secondary)] flex-shrink-0">
        {durationSeconds}s
      </span>
    </button>
  )
}
