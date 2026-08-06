import { useState } from 'react'
import { Button } from './ui/Button'

interface TransferSheetProps {
  open: boolean
  onClose: () => void
  characterName: string
  isDark: boolean
  onConfirm: (amount: number, note: string) => void
}

const MIN_AMOUNT = 0.001 // easter egg floor; display still follows accounting style
const MAX_AMOUNT = 999_999_999

// Format an amount WeChat/accounting style: thousands separators + 2 decimals
// (e.g. 11,111.01). The 0.001 easter egg keeps its third decimal so it isn't
// swallowed to 0.00.
function formatAmount(n: number): string {
  const decimals = n < 0.01 && n > 0 ? 3 : 2
  return n.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// WeChat-style transfer page (full screen). Dark mode = pure dark background,
// light mode = off-white. Reference: Image #7.
export function TransferSheet({ open, onClose, characterName, isDark, onConfirm }: TransferSheetProps) {
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')

  if (!open) return null

  const parsed = parseFloat(amount)
  const isValid = !isNaN(parsed) && parsed >= MIN_AMOUNT && parsed <= MAX_AMOUNT

  const handleConfirm = () => {
    if (!isValid) return
    onConfirm(parsed, note.trim())
    onClose()
    setAmount('')
    setNote('')
  }

  const bg = isDark ? '#0B0B0D' : '#F2F2F4'
  const card = isDark ? '#161618' : '#FFFFFF'
  const ink = isDark ? '#EFE7DD' : '#1A1A1E'
  const sub = isDark ? 'rgba(228,228,231,0.5)' : 'rgba(60,60,67,0.5)'
  const divider = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(60,60,67,0.12)'

  return (
    <div className="fixed inset-0 z-[60] flex flex-col" style={{ background: bg }}>
      {/* Header */}
      <div className="flex items-center px-3 pb-3" style={{ paddingTop: 'calc(var(--safe-top, 0px) + 12px)' }}>
        <button
          onClick={onClose}
          aria-label="返回"
          className="w-[44px] h-[44px] flex items-center justify-center active:opacity-60 transition-opacity"
        >
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke={ink} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <h2 className="flex-1 text-center text-[17px] font-semibold pr-[44px]" style={{ color: ink }}>
          转账
        </h2>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 pt-3">
        <div className="rounded-[14px] px-5 pt-6 pb-2" style={{ background: card }}>
          <div className="text-[15px] mb-6" style={{ color: ink }}>
            转账给 {characterName}
          </div>

          {/* Amount */}
          <div className="text-[13px] mb-1" style={{ color: sub }}>转账金额</div>
          <div className="flex items-baseline pb-4" style={{ borderBottom: `1px solid ${divider}` }}>
            <span className="text-[34px] font-medium mr-1.5" style={{ color: ink }}>¥</span>
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(e) => {
                // Allow digits + one dot, up to 3 decimals (easter egg).
                const v = e.target.value.replace(/[^\d.]/g, '')
                if (/^\d*\.?\d{0,3}$/.test(v)) setAmount(v)
              }}
              placeholder="0.00"
              autoFocus
              className="flex-1 bg-transparent text-[40px] font-medium outline-none w-full"
              style={{ color: ink }}
            />
          </div>
          {isValid && parsed > 0 && (
            <div className="text-[13px] mt-2" style={{ color: sub }}>
              ¥{formatAmount(parsed)}
            </div>
          )}

          {/* Note */}
          <div className="mt-5 pb-4">
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value.slice(0, 60))}
              placeholder="添加转账说明"
              maxLength={60}
              className="w-full bg-transparent text-[15px] outline-none"
              style={{ color: ink }}
            />
          </div>
        </div>

        <Button
          variant="primary"
          size="lg"
          disabled={!isValid}
          onClick={handleConfirm}
          className="mt-8"
        >
          转账
        </Button>
      </div>
    </div>
  )
}
