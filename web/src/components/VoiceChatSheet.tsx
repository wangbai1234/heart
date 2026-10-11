import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { useEffect, useState } from 'react'
import { BottomSheet } from './ui/BottomSheet'
import { Switch } from './ui/Switch'
import { useAppStore } from '../stores/appStore'
import { getCharacterSettings, updateCharacterSettings, getCharacterVoice, setPresetVoice, uploadVoiceClone, ApiError } from '../services/api'
import { useToastStore } from '../stores/toastStore'
import type { CharacterId } from '../data/uiContent'
import { VoicePickerSheet, type VoiceSelection } from './VoicePickerSheet'
import { canPreprocess, preprocessForClone } from '../services/audioPreprocess'

interface VoiceChatSheetProps {
  open: boolean
  onClose: () => void
  characterId: CharacterId
  isDark: boolean
}

// 语音聊天开关（原 CharacterBackstagePage 迁移）：开启后 AI 文字回复转为语音气泡。
// 依赖角色已配置音色，未配置则弹出音色选择弹窗。
export function VoiceChatSheet({ open, onClose, characterId, isDark }: VoiceChatSheetProps) {
  useTranslation()
  const voiceChatEnabled = useAppStore((s) => s.voiceChatEnabled[characterId] ?? false)
  const setVoiceChatEnabled = useAppStore((s) => s.setVoiceChatEnabled)
  const [hasVoice, setHasVoice] = useState(false)
  const [characterGender, setCharacterGender] = useState<'male' | 'female' | undefined>(undefined)
  const [voicePickerOpen, setVoicePickerOpen] = useState(false)
  const [voiceConfiguring, setVoiceConfiguring] = useState(false)
  const showToast = useToastStore((s) => s.show)

  useEffect(() => {
    if (!open) return
    getCharacterSettings(characterId)
      .then((res) => setVoiceChatEnabled(characterId, res.voice_enabled))
      .catch(() => { /* keep local value */ })
    getCharacterVoice(characterId)
      .then((res) => {
        setHasVoice(res.has_voice ?? res.clone_status === 'ready')
      })
      .catch(() => { /* keep local value */ })
    // 获取角色性别信息用于音色筛选
    import('../services/api').then(({ getCharacterDraft }) => {
      getCharacterDraft(characterId)
        .then((draft) => {
          setCharacterGender(draft.gender)
        })
        .catch(() => { /* keep local value */ })
    })
  }, [open, characterId, setVoiceChatEnabled])

  const handleToggle = async (value: boolean) => {
    // 未配音色：显式提示 + 打开音色选择弹窗
    if (value && !hasVoice) {
      showToast(uiText('ui66'), 'info')
      setVoicePickerOpen(true)
      return
    }
    setVoiceChatEnabled(characterId, value)
    try {
      await updateCharacterSettings(characterId, value)
    } catch (err: any) {
      // 409 = 服务端 has_voice 标记过期，角色实际无音色行。
      if (err?.status === 409) {
        showToast(uiText('more86'), 'info')
        setVoiceChatEnabled(characterId, false)
        setVoicePickerOpen(true)
        return
      }
      // 网络抖动可能误报失败——先和服务端真实状态核对再决定是否回滚。
      try {
        const actual = await getCharacterSettings(characterId)
        setVoiceChatEnabled(characterId, actual.voice_enabled)
        if (actual.voice_enabled !== value) {
          showToast(uiText('more87'), 'error')
        }
      } catch {
        setVoiceChatEnabled(characterId, !value)
        showToast(uiText('more87'), 'error')
      }
    }
  }

  const handleVoicePickerConfirm = async (selection: VoiceSelection) => {
    setVoiceConfiguring(true)
    try {
      if (selection.type === 'preset' && selection.presetVoiceId) {
        // 配置预设音色
        await setPresetVoice(characterId, selection.presetVoiceId)
        showToast(uiText('dynamic6', { v0: selection.presetName || uiText('ui72') }), 'success')
        setHasVoice(true)
        // 配置成功后自动开启语音聊天
        setVoiceChatEnabled(characterId, true)
        await updateCharacterSettings(characterId, true)
      } else if (selection.type === 'clone' && selection.cloneFile) {
        // 上传克隆音色
        let fileToUpload = selection.cloneFile
        // 客户端预处理：视频提取音频，音频标准化
        try {
          if (canPreprocess()) {
            const processed = await preprocessForClone(selection.cloneFile)
            fileToUpload = processed.file
          } else if (selection.cloneFile.size > 20 * 1024 * 1024) {
            showToast(uiText('ui73'), 'error')
            return
          }
        } catch {
          if (selection.cloneFile.size > 20 * 1024 * 1024) {
            showToast(uiText('ui74'), 'error')
            return
          }
        }
        await uploadVoiceClone(characterId, fileToUpload, 'fish')
        showToast(uiText('ui75'), 'info')
        // 克隆需要等待，暂不自动开启语音聊天
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : uiText('ui76')
      showToast(msg, 'error')
    } finally {
      setVoiceConfiguring(false)
    }
  }

  const subtle = isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]'

  return (
    <>
      <BottomSheet open={open} onClose={onClose}>
        <h2 className={`mb-4 text-[18px] font-semibold tracking-[-0.02em] ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
          {uiText('more7')}</h2>
        <div className="flex items-center gap-4 rounded-[18px] border px-4 py-4"
          style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)' }}
        >
          <div className="min-w-0 flex-1">
            <p className={`mb-1 text-[15px] font-medium ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
              {hasVoice ? uiText('more88') : uiText('more89')}
            </p>
            <p className={`text-[13px] leading-[1.5] ${subtle}`}>
              {hasVoice
                ? uiText('more90')
                : uiText('more91')}
            </p>
          </div>
          <div className="shrink-0">
            {hasVoice ? (
              <Switch checked={voiceChatEnabled} onChange={handleToggle} />
            ) : (
              <button
                onClick={() => setVoicePickerOpen(true)}
                disabled={voiceConfiguring}
                className="rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
              >
                {voiceConfiguring ? uiText('more92') : uiText('more93')}
              </button>
            )}
          </div>
        </div>
      </BottomSheet>

      {/* 音色选择弹窗 */}
      <VoicePickerSheet
        open={voicePickerOpen}
        onClose={() => setVoicePickerOpen(false)}
        gender={characterGender}
        onConfirm={handleVoicePickerConfirm}
      />
    </>
  )
}
