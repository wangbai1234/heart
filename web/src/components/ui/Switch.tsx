interface SwitchProps {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}

export function Switch({ checked, onChange, disabled }: SwitchProps) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`
        relative w-[51px] h-[31px] rounded-full transition-colors duration-[var(--duration-base)]
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
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
