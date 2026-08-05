import { BottomSheet } from './ui/BottomSheet'

interface ChatPlusMenuProps {
  open: boolean
  onClose: () => void
  isDark: boolean
  onVoiceChat: () => void
  onVoiceCall: () => void
}

// 发送键右侧 "+" 展开菜单：语音聊天（开关弹窗）/ 语音通话（全屏页）。
export function ChatPlusMenu({ open, onClose, isDark, onVoiceChat, onVoiceCall }: ChatPlusMenuProps) {
  const itemBase = `w-full flex items-center gap-4 rounded-[18px] border px-4 py-4 text-left transition-transform active:scale-[0.99] ${
    isDark ? 'bg-[rgba(255,255,255,0.05)]' : 'bg-[rgba(255,255,255,0.5)]'
  }`
  const itemBorder = { borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)' }
  const titleCls = `text-[15px] font-medium ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`
  const subCls = `text-[13px] leading-[1.5] ${isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]'}`
  const iconBubble = `flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-full ${
    isDark ? 'bg-[rgba(255,183,197,0.12)]' : 'bg-[rgba(255,183,197,0.16)]'
  }`

  return (
    <BottomSheet open={open} onClose={onClose}>
      <div className="space-y-2.5">
        <button className={itemBase} style={itemBorder} onClick={() => { onClose(); onVoiceChat() }}>
          <span className={iconBubble}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF7DA1" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
              <path d="M19 11.5a7 7 0 0 1-14 0" />
              <path d="M12 18.5v3" />
            </svg>
          </span>
          <span className="min-w-0 flex-1">
            <span className={`block ${titleCls}`}>语音聊天</span>
            <span className={`block ${subCls}`}>开启后 Ta 的回复转为语音</span>
          </span>
        </button>

        <button className={itemBase} style={itemBorder} onClick={() => { onClose(); onVoiceCall() }}>
          <span className={iconBubble}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FF7DA1" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z" />
            </svg>
          </span>
          <span className="min-w-0 flex-1">
            <span className={`block ${titleCls}`}>语音通话</span>
            <span className={`block ${subCls}`}>和 Ta 实时语音通话</span>
          </span>
        </button>
      </div>
    </BottomSheet>
  )
}
