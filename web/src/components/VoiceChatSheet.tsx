import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BottomSheet } from './ui/BottomSheet'
import { Switch } from './ui/Switch'
import { useAppStore } from '../stores/appStore'
import { getCharacterSettings, updateCharacterSettings, getCharacterVoice } from '../services/api'
import { useToastStore } from '../stores/toastStore'
import type { CharacterId } from '../data/uiContent'

interface VoiceChatSheetProps {
  open: boolean
  onClose: () => void
  characterId: CharacterId
  isDark: boolean
}

// 语音聊天开关（原 CharacterBackstagePage 迁移）：开启后 AI 文字回复转为语音气泡。
// 依赖角色已配置音色，未配置则引导去 /characters/new?voice=。
export function VoiceChatSheet({ open, onClose, characterId, isDark }: VoiceChatSheetProps) {
  const navigate = useNavigate()
  const voiceChatEnabled = useAppStore((s) => s.voiceChatEnabled[characterId] ?? false)
  const setVoiceChatEnabled = useAppStore((s) => s.setVoiceChatEnabled)
  const [hasVoice, setHasVoice] = useState(false)

  useEffect(() => {
    if (!open) return
    getCharacterSettings(characterId)
      .then((res) => setVoiceChatEnabled(characterId, res.voice_enabled))
      .catch(() => { /* keep local value */ })
    getCharacterVoice(characterId)
      .then((res) => setHasVoice(res.has_voice ?? res.clone_status === 'ready'))
      .catch(() => { /* keep local value */ })
  }, [open, characterId, setVoiceChatEnabled])

  const handleToggle = async (value: boolean) => {
    // 未配音色：显式提示 + 引导，不静默跳转（原后台页血泪教训 BUG-2）。
    if (value && !hasVoice) {
      useToastStore.getState().show('该角色暂未配置音色，请先选择一个音色', 'info')
      onClose()
      navigate(`/characters/new?voice=${characterId}`)
      return
    }
    setVoiceChatEnabled(characterId, value)
    try {
      await updateCharacterSettings(characterId, value)
    } catch (err: any) {
      // 409 = 服务端 has_voice 标记过期，角色实际无音色行。
      if (err?.status === 409) {
        useToastStore.getState().show('请先为该角色配置音色，才能开启语音聊天', 'info')
        setVoiceChatEnabled(characterId, false)
        onClose()
        navigate(`/characters/new?voice=${characterId}`)
        return
      }
      // 网络抖动可能误报失败——先和服务端真实状态核对再决定是否回滚。
      try {
        const actual = await getCharacterSettings(characterId)
        setVoiceChatEnabled(characterId, actual.voice_enabled)
        if (actual.voice_enabled !== value) {
          useToastStore.getState().show('语音开关切换失败，请稍后重试', 'error')
        }
      } catch {
        setVoiceChatEnabled(characterId, !value)
        useToastStore.getState().show('语音开关切换失败，请稍后重试', 'error')
      }
    }
  }

  const subtle = isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]'

  return (
    <BottomSheet open={open} onClose={onClose}>
      <h2 className={`mb-4 text-[18px] font-semibold tracking-[-0.02em] ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
        语音聊天
      </h2>
      <div className="flex items-center gap-4 rounded-[18px] border px-4 py-4"
        style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)' }}
      >
        <div className="min-w-0 flex-1">
          <p className={`mb-1 text-[15px] font-medium ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
            {hasVoice ? '开启语音回复' : '配置音色'}
          </p>
          <p className={`text-[13px] leading-[1.5] ${subtle}`}>
            {hasVoice
              ? '开启后 Ta 的回复将转为语音，会额外消耗 yuoyuo币'
              : '先选择预设音色或克隆专属音色，才能开启语音聊天'}
          </p>
        </div>
        <div className="shrink-0">
          {hasVoice ? (
            <Switch checked={voiceChatEnabled} onChange={handleToggle} />
          ) : (
            <button
              onClick={() => { onClose(); navigate(`/characters/new?voice=${characterId}`) }}
              className="rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] px-4 py-2 text-[13px] font-semibold text-white"
            >
              去配置
            </button>
          )}
        </div>
      </div>
    </BottomSheet>
  )
}
