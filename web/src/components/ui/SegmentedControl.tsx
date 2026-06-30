interface SegmentedControlProps {
  options: string[]
  value: string
  onChange: (v: string) => void
}

export function SegmentedControl({ options, value, onChange }: SegmentedControlProps) {
  return (
    <div className="flex bg-[var(--color-segment-container)] rounded-[10px] p-[2px]">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`
            flex-1 py-[6px] text-[13px] rounded-[8px] transition-all duration-[var(--duration-base)]
            ${value === opt
              ? 'bg-white text-[var(--color-ink)] font-medium shadow-[0_1px_4px_rgba(0,0,0,0.08)]'
              : 'bg-transparent text-[var(--color-text-muted)]'
            }
          `}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
