import { useState, useRef, useCallback } from 'react'

interface OTPInputProps {
  length?: number
  groupSize?: number
  onComplete?: (code: string) => void
  onChange?: (code: string) => void
}

export function OTPInput({ length = 12, groupSize = 4, onComplete, onChange }: OTPInputProps) {
  const [digits, setDigits] = useState<string[]>(Array(length).fill(''))
  const inputs = useRef<(HTMLInputElement | null)[]>([])

  const handleChange = useCallback((index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1)
    if (!/^[a-zA-Z0-9]*$/.test(value)) return

    const next = [...digits]
    next[index] = value.toUpperCase()
    setDigits(next)

    const code = next.join('')
    onChange?.(code)

    if (value && index < length - 1) {
      inputs.current[index + 1]?.focus()
    }

    if (next.every((d) => d !== '')) {
      onComplete?.(code)
    }
  }, [digits, length, onComplete, onChange])

  const handleKeyDown = useCallback((index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputs.current[index - 1]?.focus()
    }
  }, [digits])

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/[^a-zA-Z0-9]/g, '').slice(0, length).toUpperCase()
    const next = Array(length).fill('')
    pasted.split('').forEach((char, i) => { next[i] = char })
    setDigits(next)
    onChange?.(next.join(''))
    if (pasted.length === length) {
      onComplete?.(pasted)
      inputs.current[length - 1]?.focus()
    } else {
      inputs.current[Math.min(pasted.length, length - 1)]?.focus()
    }
  }, [length, onComplete, onChange])

  const groups: { digits: typeof digits; startIndex: number }[] = []
  for (let i = 0; i < length; i += groupSize) {
    groups.push({ digits: digits.slice(i, i + groupSize), startIndex: i })
  }

  return (
    <div className="flex justify-center items-center gap-2">
      {groups.map((group, gi) => (
        <div key={gi} className="flex items-center gap-[6px]">
          {group.digits.map((digit, di) => {
            const index = group.startIndex + di
            return (
              <input
                key={index}
                ref={(el) => { inputs.current[index] = el }}
                type="text"
                inputMode="text"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                className={`
                  w-[44px] h-[52px] text-center text-[18px] font-semibold font-brand
                  rounded-[12px] border
                  bg-[var(--color-glass-35)] backdrop-blur-[12px]
                  outline-none transition-colors
                  ${digit
                    ? 'border-[var(--color-primary)] text-[var(--color-ink)]'
                    : 'border-[var(--color-divider-inset)] text-[var(--color-ink)]'
                  }
                  focus:border-[var(--color-primary)]
                `}
              />
            )
          })}
          {gi < groups.length - 1 && (
            <span className="text-[18px] text-[var(--color-text-muted)] mx-1">—</span>
          )}
        </div>
      ))}
    </div>
  )
}
