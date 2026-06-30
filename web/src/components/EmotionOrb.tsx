import { useRef, useEffect } from 'react'
import { useChatStore } from '../stores/chatStore'

const SIZE = 120
const CENTER = SIZE / 2
const BASE_R = 35

function moodToValence(mood: string): number {
  switch (mood) {
    case 'happy': return 0.7
    case 'sad': return -0.5
    case 'angry': return -0.4
    case 'fearful': return -0.3
    case 'surprised': return 0.3
    default: return 0
  }
}

export function EmotionOrb() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const frameRef = useRef(0)
  const { energy, mood, intimacy } = useChatStore((s) => s.vad)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const valence = moodToValence(mood)
    const hue = 220 + valence * 60
    const saturation = 60 + 30 * Math.abs(valence)
    const lightness = 50

    let running = true
    const start = performance.now()

    const draw = () => {
      if (!running) return
      const t = (performance.now() - start) / 1000

      ctx.clearRect(0, 0, SIZE, SIZE)

      const breathe = Math.sin(t * (1 + energy * 3)) * 6
      const r = BASE_R + breathe
      const glowR = r + 8 + intimacy * 12

      const grad = ctx.createRadialGradient(CENTER, CENTER, r * 0.3, CENTER, CENTER, glowR)
      grad.addColorStop(0, `hsl(${hue} ${saturation}% ${lightness + 20}%)`)
      grad.addColorStop(0.6, `hsl(${hue} ${saturation}% ${lightness}%)`)
      grad.addColorStop(1, `hsl(${hue} ${saturation}% ${lightness}% / 0)`)

      ctx.beginPath()
      ctx.arc(CENTER, CENTER, glowR, 0, Math.PI * 2)
      ctx.fillStyle = grad
      ctx.fill()

      ctx.beginPath()
      ctx.arc(CENTER, CENTER, r, 0, Math.PI * 2)
      ctx.fillStyle = `hsl(${hue} ${saturation}% ${lightness}%)`
      ctx.fill()

      frameRef.current = requestAnimationFrame(draw)
    }

    frameRef.current = requestAnimationFrame(draw)
    return () => {
      running = false
      cancelAnimationFrame(frameRef.current)
    }
  }, [energy, mood, intimacy])

  return (
    <div className="flex flex-col items-center gap-1">
      <canvas
        ref={canvasRef}
        width={SIZE}
        height={SIZE}
        className="w-20 h-20"
      />
      <span className="text-xs text-[var(--color-text-muted)] capitalize">{mood}</span>
    </div>
  )
}
