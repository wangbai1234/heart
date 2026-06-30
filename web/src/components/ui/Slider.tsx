interface SliderProps {
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
}

export function Slider({ value, onChange, min = 0, max = 100 }: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100

  return (
    <div className="flex items-center gap-2 w-full">
      <span className="text-xs text-[var(--color-text-muted)]">A</span>
      <div className="relative flex-1 h-[4px] rounded-full bg-[var(--color-slider-track)]">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-[var(--color-primary)]"
          style={{ width: `${pct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[22px] h-[22px] rounded-full bg-[var(--color-primary)] shadow-[var(--shadow-soft)] pointer-events-none"
          style={{ left: `${pct}%` }}
        />
      </div>
      <span className="text-base text-[var(--color-text-muted)] font-bold">A</span>
    </div>
  )
}
