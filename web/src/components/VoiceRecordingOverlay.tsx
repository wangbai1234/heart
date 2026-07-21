import { useEffect, useRef, useState } from 'react'

interface Props {
  durationMs: number
  willCancel: boolean
  cancelZoneRef: React.RefObject<HTMLDivElement | null>
}

export function VoiceRecordingOverlay({ durationMs, willCancel, cancelZoneRef }: Props) {
  const [elapsed, setElapsed] = useState(0)
  const startRef = useRef(Date.now())

  useEffect(() => {
    startRef.current = Date.now()
    const id = setInterval(() => setElapsed(Date.now() - startRef.current), 200)
    return () => clearInterval(id)
  }, [])

  const secs = Math.floor((durationMs > 0 ? durationMs : elapsed) / 1000)
  const mm = String(Math.floor(secs / 60)).padStart(2, '0')
  const ss = String(secs % 60).padStart(2, '0')

  return (
    <>
      {/* Full-screen backdrop — pointer-events: none so touches pass through to cancel zone */}
      <div
        className="fixed inset-0 z-40 pointer-events-none"
        style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(2px)' }}
      />

      {/* Cancel zone at top — receives pointer events */}
      <div
        ref={cancelZoneRef}
        className="fixed top-0 left-0 right-0 z-50 flex flex-col items-center justify-center"
        style={{ height: 120, pointerEvents: 'none' }}
      >
        <div
          className={`flex flex-col items-center justify-center rounded-2xl px-8 py-4 transition-colors ${
            willCancel
              ? 'bg-[rgba(220,38,38,0.75)]'
              : 'bg-[rgba(255,255,255,0.15)]'
          }`}
          style={{ minWidth: 180 }}
        >
          <span className="text-white text-[13px] font-medium">
            {willCancel ? '松开手指，取消发送' : '上滑取消'}
          </span>
          {willCancel && (
            <span className="text-[rgba(255,255,255,0.75)] text-[11px] mt-1">× 取消</span>
          )}
        </div>
      </div>

      {/* Recording indicator at bottom-center */}
      <div className="fixed bottom-24 left-0 right-0 z-50 flex flex-col items-center pointer-events-none">
        {/* Animated bars */}
        <div className="flex items-end gap-[3px] h-10 mb-3">
          {[0.4, 0.7, 1.0, 0.8, 0.5, 0.9, 0.6].map((scale, i) => (
            <div
              key={i}
              className="w-1 rounded-full bg-white"
              style={{
                height: `${scale * 100}%`,
                animation: `voiceBar 0.8s ease-in-out ${i * 0.1}s infinite alternate`,
                opacity: willCancel ? 0.4 : 1,
              }}
            />
          ))}
        </div>
        <span className="text-white text-[14px] font-mono tracking-widest">
          {mm}:{ss}
        </span>
        <span className={`text-[12px] mt-1 transition-colors ${willCancel ? 'text-red-300' : 'text-[rgba(255,255,255,0.7)]'}`}>
          {willCancel ? '松开手指，取消发送' : '手指上滑，取消发送'}
        </span>
      </div>

      <style>{`
        @keyframes voiceBar {
          from { transform: scaleY(0.3); }
          to { transform: scaleY(1); }
        }
      `}</style>
    </>
  )
}
