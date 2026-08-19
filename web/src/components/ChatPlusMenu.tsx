import { BottomSheet } from './ui/BottomSheet'

interface ChatPlusMenuProps {
  open: boolean
  onClose: () => void
  isDark: boolean
  onVoiceChat: () => void
  onVoiceCall: () => void
  onTransfer: () => void
  onRestart: () => void
}

// 发送键右侧 "+" 展开的底部宫格面板（微信样式）：圆角方块图标 + 下方文字。
// 语音聊天（开关弹窗）/ 语音通话（全屏页）/ 转账（转账输入页）/ 重新开始（回到开场，二次确认）。
export function ChatPlusMenu({ open, onClose, isDark, onVoiceChat, onVoiceCall, onTransfer, onRestart }: ChatPlusMenuProps) {
  const tile = `flex h-[62px] w-[62px] items-center justify-center rounded-[18px] active:scale-95 transition-transform ${
    isDark ? 'bg-[rgba(255,255,255,0.08)]' : 'bg-[rgba(255,255,255,0.72)] shadow-[0_2px_10px_rgba(0,0,0,0.05)]'
  }`
  const label = `mt-2 text-[12px] ${isDark ? 'text-[rgba(236,233,244,0.7)]' : 'text-[rgba(47,54,74,0.62)]'}`
  const stroke = isDark ? '#F3B9C8' : '#FF7DA1'

  return (
    <BottomSheet open={open} onClose={onClose}>
      <div className="grid grid-cols-4 gap-y-5 pt-1 pb-2">
        <button className="flex flex-col items-center" onClick={() => { onClose(); onVoiceChat() }}>
          <span className={tile}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16a4 4 0 0 0 4-4V8a4 4 0 1 0-8 0v4a4 4 0 0 0 4 4Z" />
              <path d="M19 11.5a7 7 0 0 1-14 0" />
              <path d="M12 18.5v3" />
            </svg>
          </span>
          <span className={label}>语音聊天</span>
        </button>

        <button className="flex flex-col items-center" onClick={() => { onClose(); onVoiceCall() }}>
          <span className={tile}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z" />
            </svg>
          </span>
          <span className={label}>语音通话</span>
        </button>

        <button className="flex flex-col items-center" onClick={() => { onClose(); onTransfer() }}>
          <span className={tile}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </span>
          <span className={label}>转账</span>
        </button>

        <button className="flex flex-col items-center" onClick={() => { onClose(); onRestart() }}>
          <span className={tile}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
              <path d="M3 3v5h5" />
            </svg>
          </span>
          <span className={label}>重新开始</span>
        </button>
      </div>
    </BottomSheet>
  )
}
