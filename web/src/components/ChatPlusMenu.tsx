interface ChatPlusMenuProps {
  open: boolean
  isDark: boolean
  onVoiceChat: () => void
  onVoiceCall: () => void
  onTransfer: () => void
  onMasks: () => void
  onRestart: () => void
}

// Embedded content for the chat composer surface. The parent owns the glass
// background and border so the input row and this grid read as one panel.
export function ChatPlusMenu({ open, isDark, onVoiceChat, onVoiceCall, onTransfer, onMasks, onRestart }: ChatPlusMenuProps) {
  const tile = `flex h-[58px] w-[58px] items-center justify-center rounded-[14px] border active:scale-95 transition-transform ${
    isDark
      ? 'border-white/6 bg-white/7'
      : 'border-black/[0.035] bg-white/70 shadow-[0_1px_5px_rgba(45,35,40,0.04)]'
  }`
  const label = `mt-2 text-[12px] ${isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.64)]'}`
  const stroke = isDark ? '#F3B9C8' : '#FF7DA1'

  return (
    <div
      className={`grid transition-[grid-template-rows,opacity] duration-200 ease-out ${
        open ? 'grid-rows-[1fr] opacity-100' : 'pointer-events-none grid-rows-[0fr] opacity-0'
      }`}
      aria-hidden={!open}
    >
      <div className="min-h-0 overflow-hidden">
        <div className={`mx-3 grid grid-cols-4 gap-y-4 border-t px-1 pb-4 pt-4 ${isDark ? 'border-white/8' : 'border-black/[0.055]'}`}>
          <button type="button" disabled={!open} className="flex flex-col items-center" onClick={onVoiceChat}>
            <span className={tile}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
                <path d="M19 11.5a7 7 0 0 1-14 0" />
                <path d="M12 18.5v3" />
              </svg>
            </span>
            <span className={label}>语音聊天</span>
          </button>

          <button type="button" disabled={!open} className="flex flex-col items-center" onClick={onVoiceCall}>
            <span className={tile}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z" />
              </svg>
            </span>
            <span className={label}>语音通话</span>
          </button>

          <button type="button" disabled={!open} className="flex flex-col items-center" onClick={onTransfer}>
            <span className={tile}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </span>
            <span className={label}>转账</span>
          </button>

          <button type="button" disabled={!open} className="flex flex-col items-center" onClick={onMasks}>
            <span className={tile}>
              <svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3.5 7.5c2.7-1.6 5.5-2.2 8.5-2.2s5.8.6 8.5 2.2c-.2 5.9-3.3 10.2-8.5 11.2C6.8 17.7 3.7 13.4 3.5 7.5Z" />
                <path d="M7 10.7c1.1-.7 2.2-.7 3.3 0M13.7 10.7c1.1-.7 2.2-.7 3.3 0M9.7 15c1.5.7 3.1.7 4.6 0" />
              </svg>
            </span>
            <span className={label}>我的面具</span>
          </button>

          <button type="button" disabled={!open} className="flex flex-col items-center" onClick={onRestart}>
            <span className={tile}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                <path d="M3 3v5h5" />
              </svg>
            </span>
            <span className={label}>重新开始</span>
          </button>
        </div>
      </div>
    </div>
  )
}
