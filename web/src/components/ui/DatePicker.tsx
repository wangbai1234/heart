import { useRef, useEffect, useState, useCallback } from 'react'
import { Button } from './Button'

const ITEM_H = 44
const VISIBLE = 5
const PAD = (ITEM_H * (VISIBLE - 1)) / 2

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function range(start: number, end: number): number[] {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

const YEARS = range(1940, 2012)
const MONTHS = range(1, 12)

interface DatePickerProps {
  value: string // YYYY-MM-DD or empty
  onChange: (date: string) => void
  onConfirm: () => void
}

export function DatePicker({ value, onChange, onConfirm }: DatePickerProps) {
  const parsed = value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  const initYear = parsed ? parseInt(parsed[1]) : 2000
  const initMonth = parsed ? parseInt(parsed[2]) : 1
  const initDay = parsed ? parseInt(parsed[3]) : 1

  const [year, setYear] = useState(initYear)
  const [month, setMonth] = useState(initMonth)
  const [day, setDay] = useState(initDay)

  const maxDay = daysInMonth(year, month)
  const days = range(1, maxDay)

  // Clamp day when month/year changes
  useEffect(() => {
    if (day > maxDay) setDay(maxDay)
  }, [maxDay, day])

  // Sync back to parent
  useEffect(() => {
    const m = String(month).padStart(2, '0')
    const d = String(day).padStart(2, '0')
    onChange(`${year}-${m}-${d}`)
  }, [year, month, day])

  return (
    <div>
      <h3 className="text-[18px] font-semibold text-[var(--color-ink)] text-center mb-5">
        出生日期
      </h3>

      <div className="flex justify-center gap-2">
        {/* Year */}
        <Wheel
          items={YEARS.map(String)}
          value={String(year)}
          onChange={(v) => setYear(parseInt(v))}
          suffix="年"
        />
        {/* Month */}
        <Wheel
          items={MONTHS.map((m) => String(m).padStart(2, '0'))}
          value={String(month).padStart(2, '0')}
          onChange={(v) => setMonth(parseInt(v))}
          suffix="月"
        />
        {/* Day */}
        <Wheel
          items={days.map((d) => String(d).padStart(2, '0'))}
          value={String(day).padStart(2, '0')}
          onChange={(v) => setDay(parseInt(v))}
          suffix="日"
        />
      </div>

      <Button variant="primary" size="sm" onClick={onConfirm} className="mt-5 w-full">
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

  const handleScroll = useCallback(() => {
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
  }, [items, value, onChange])

  const handleClick = useCallback((item: string) => {
    onChange(item)
    const newIdx = items.indexOf(item)
    containerRef.current?.scrollTo({ top: newIdx * ITEM_H, behavior: 'smooth' })
  }, [items, onChange])

  return (
    <div className="relative w-[72px]">
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
