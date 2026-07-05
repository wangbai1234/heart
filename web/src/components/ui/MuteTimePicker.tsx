import { useRef, useEffect } from 'react'
import { Button } from './Button'

interface MuteTimePickerProps {
  startHour: string
  startMin: string
  endHour: string
  endMin: string
  isNever: boolean
  onChangeTime: (start: string, startMin: string, end: string, endMin: string) => void
  onChangeNever: (v: boolean) => void
  onConfirm: () => void
}

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const MINUTES = ['00', '15', '30', '45']
const ITEM_H = 44
const VISIBLE = 5
const PAD = (ITEM_H * (VISIBLE - 1)) / 2

export function MuteTimePicker({
  startHour,
  startMin,
  endHour,
  endMin,
  isNever,
  onChangeTime,
  onChangeNever,
  onConfirm,
}: MuteTimePickerProps) {
  const startMinutes = parseInt(startHour) * 60 + parseInt(startMin)
  const endMinutes = parseInt(endHour) * 60 + parseInt(endMin)
  const isValidRange = isNever || endMinutes > startMinutes

  return (
    <div>
      <h3 className="text-[18px] font-semibold text-[var(--color-ink)] text-center mb-4">
        静音时段
      </h3>

      {/* Never / Custom toggle */}
      <div className="flex bg-[var(--color-segment-container)] rounded-[10px] p-[2px] mb-5">
        {(['自定义', '永不'] as const).map((opt) => {
          const active = opt === '永不' ? isNever : !isNever
          return (
            <button
              key={opt}
              onClick={() => onChangeNever(opt === '永不')}
              className={`flex-1 py-[8px] text-[14px] rounded-[8px] transition-all duration-200 ${
                active
                  ? 'bg-white text-[var(--color-ink)] font-medium shadow-[0_1px_4px_rgba(0,0,0,0.08)]'
                  : 'bg-transparent text-[var(--color-text-muted)]'
              }`}
            >
              {opt}
            </button>
          )
        })}
      </div>

      {/* Time wheels */}
      <div className={`transition-opacity duration-200 ${isNever ? 'opacity-30 pointer-events-none' : ''}`}>
        {/* Labels */}
        <div className="flex mb-2">
          <div className="flex-1 flex justify-center">
            <span className="text-[13px] text-[var(--color-text-muted)]">开始</span>
          </div>
          <div className="w-10" />
          <div className="flex-1 flex justify-center">
            <span className="text-[13px] text-[var(--color-text-muted)]">结束</span>
          </div>
        </div>

        {/* Wheel pairs */}
        <div className="flex">
          {/* Start */}
          <div className="flex-1 flex justify-center gap-1">
            <Wheel
              items={HOURS}
              value={startHour}
              onChange={(v) => onChangeTime(v, startMin, endHour, endMin)}
              suffix="时"
            />
            <Wheel
              items={MINUTES}
              value={startMin}
              onChange={(v) => onChangeTime(startHour, v, endHour, endMin)}
              suffix="分"
            />
          </div>
          {/* Separator */}
          <div className="flex items-center justify-center px-1">
            <span className="text-[20px] font-medium text-[var(--color-text-muted)]">–</span>
          </div>
          {/* End */}
          <div className="flex-1 flex justify-center gap-1">
            <Wheel
              items={HOURS}
              value={endHour}
              onChange={(v) => onChangeTime(startHour, startMin, v, endMin)}
              suffix="时"
            />
            <Wheel
              items={MINUTES}
              value={endMin}
              onChange={(v) => onChangeTime(startHour, startMin, endHour, v)}
              suffix="分"
            />
          </div>
        </div>
      </div>

      {/* Validation warning */}
      {!isValidRange && (
        <p className="text-[12px] text-[var(--color-primary)] text-center mt-3">
          结束时间不能早于或等于开始时间
        </p>
      )}

      {/* Confirm */}
      <Button variant="primary" size="sm" onClick={onConfirm} disabled={!isValidRange} className="mt-5 w-full">
        完成
      </Button>
    </div>
  )
}

/* ── Single column wheel ──────────────────────────────────────── */
function Wheel({
  items,
  value,
  onChange,
  suffix,
}: {
  items: string[]
  value: string
  onChange: (v: string) => void
  suffix: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const scrollingRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const idx = items.indexOf(value)

  useEffect(() => {
    if (containerRef.current && !scrollingRef.current) {
      containerRef.current.scrollTop = idx * ITEM_H
    }
  }, [idx])

  const handleScroll = () => {
    if (!containerRef.current) return
    scrollingRef.current = true
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      scrollingRef.current = false
      if (!containerRef.current) return
      const raw = containerRef.current.scrollTop / ITEM_H
      const snapped = Math.round(raw)
      const clamped = Math.max(0, Math.min(snapped, items.length - 1))
      containerRef.current.scrollTo({ top: clamped * ITEM_H, behavior: 'smooth' })
      if (items[clamped] !== value) {
        onChange(items[clamped])
      }
    }, 80)
  }

  const handleClick = (item: string) => {
    onChange(item)
    const newIdx = items.indexOf(item)
    containerRef.current?.scrollTo({ top: newIdx * ITEM_H, behavior: 'smooth' })
  }

  return (
    <div className="relative w-[52px]">
      {/* Highlight band */}
      <div
        className="absolute left-0 right-0 pointer-events-none z-10"
        style={{ top: PAD, height: ITEM_H }}
      >
        <div className="w-full h-full rounded-[8px] bg-[rgba(255,183,197,0.10)]" />
      </div>
      {/* Scroll container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="overflow-y-auto snap-y snap-mandatory scrollbar-hide"
        style={{ height: ITEM_H * VISIBLE, scrollPaddingTop: PAD }}
      >
        <div style={{ height: PAD }} />
        {items.map((item) => {
          const selected = item === value
          return (
            <button
              key={item}
              onClick={() => handleClick(item)}
              className={`snap-center w-full flex items-center justify-center transition-colors ${
                selected
                  ? 'text-[var(--color-primary)] font-semibold text-[16px]'
                  : 'text-[var(--color-text-muted)] text-[14px]'
              }`}
              style={{ height: ITEM_H }}
            >
              {item}{suffix}
            </button>
          )
        })}
        <div style={{ height: PAD }} />
      </div>
    </div>
  )
}
