interface SwitchProps {
  checked: boolean
  onChange: (v: boolean) => void
}

export function Switch({ checked, onChange }: SwitchProps) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`
        relative w-[51px] h-[31px] rounded-full transition-colors duration-[var(--duration-base)]
        ${checked
          ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF85A1]'
          : 'bg-[var(--color-toggle-track-off)]'
        }
      `}
    >
      <span
        className={`
          absolute top-[2px] left-[2px] w-[27px] h-[27px] rounded-full bg-white
          shadow-[0_2px_6px_rgba(0,0,0,0.10)]
          transition-transform duration-[var(--duration-base)]
          ${checked ? 'translate-x-[20px]' : 'translate-x-0'}
        `}
      />
    </button>
  )
}
