import { useState, useEffect, useCallback, useRef } from 'react'

const BAR_COUNT = 5

interface VoiceMessageBubbleProps {
  audioData: string // base64 WAV 音频
  duration: number  // 时长（毫秒）
  format: string    // "wav"
  isDark?: boolean
}

export default function VoiceMessageBubble({ audioData, duration, format, isDark = false }: VoiceMessageBubbleProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [barHeights, setBarHeights] = useState<number[]>(Array(BAR_COUNT).fill(4))
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number | null>(null)

  // 将 base64 转为 Blob URL，或直接使用 URL
  useEffect(() => {
    if (!audioData) return

    // If it's already a URL (from history), use directly
    if (audioData.startsWith('http') || audioData.startsWith('blob:')) {
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
      if (!audioData.startsWith('http') && !audioData.startsWith('blob:')) {
        URL.revokeObjectURL(url)
      }
      stopVisualization()
    }
  }, [audioData, format])

  const stopVisualization = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close() } catch { /* ignore */ }
      audioCtxRef.current = null
      analyserRef.current = null
    }
  }, [])

  const startVisualization = useCallback(() => {
    const analyser = analyserRef.current
    if (!analyser) return

    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const updateBars = () => {
      if (!analyserRef.current) return
      analyserRef.current.getByteFrequencyData(dataArray)

      // Sample frequency bins into BAR_COUNT bars
      const binSize = Math.floor(dataArray.length / BAR_COUNT)
      const newHeights: number[] = []
      for (let i = 0; i < BAR_COUNT; i++) {
        let sum = 0
        for (let j = i * binSize; j < (i + 1) * binSize; j++) {
          sum += dataArray[j]
        }
        const avg = sum / binSize
        // Map 0-255 to 4-16px height
        const height = Math.max(4, Math.min(16, (avg / 255) * 16))
        newHeights.push(height)
      }
      setBarHeights(newHeights)
      rafRef.current = requestAnimationFrame(updateBars)
    }

    rafRef.current = requestAnimationFrame(updateBars)
  }, [])

  const handlePlayPause = useCallback(() => {
    if (!audioUrl) return

    if (isPlaying) {
      // Stop
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
      }
      stopVisualization()
      setIsPlaying(false)
      setBarHeights(Array(BAR_COUNT).fill(4))
    } else {
      // Play with AnalyserNode
      const audio = new Audio(audioUrl)
      audioRef.current = audio

      try {
        const audioCtx = new AudioContext()
        const source = audioCtx.createMediaElementSource(audio)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 128
        source.connect(analyser)
        analyser.connect(audioCtx.destination)

        audioCtxRef.current = audioCtx
        analyserRef.current = analyser
      } catch {
        // MediaElementSource already connected or unsupported — fallback to random bars
      }

      audio.play().then(() => {
        setIsPlaying(true)
        startVisualization()
        audio.onended = () => {
          setIsPlaying(false)
          stopVisualization()
          setBarHeights(Array(BAR_COUNT).fill(4))
        }
      }).catch(console.error)
    }
  }, [audioUrl, isPlaying, startVisualization, stopVisualization])

  const durationSeconds = Math.ceil(duration / 1000)
  const bubbleWidth = Math.min(200, Math.max(80, durationSeconds * 10))

  return (
    <button
      onClick={handlePlayPause}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
        isDark
          ? 'bg-[rgba(255,255,255,0.06)] hover:bg-[rgba(255,255,255,0.10)]'
          : 'bg-[var(--color-surface-light)] hover:bg-[var(--color-surface)]'
      }`}
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

      {/* 波形条 — AnalyserNode 驱动 or 静态 */}
      <div className="flex items-end gap-[2px] flex-1 h-[16px]">
        {barHeights.map((h, i) => (
          <div
            key={i}
            className={`flex-1 rounded-full transition-all ${
              isPlaying
                ? 'bg-gradient-to-t from-[var(--color-primary)] to-[var(--color-accent)]'
                : 'bg-[var(--color-text-secondary)]'
            }`}
            style={{
              height: `${h}px`,
              transitionDuration: isPlaying ? '60ms' : '200ms',
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
