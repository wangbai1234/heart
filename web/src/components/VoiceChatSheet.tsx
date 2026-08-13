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
      showToast('该角色暂未配置音色，请先选择一个音色', 'info')
      setVoicePickerOpen(true)
      return
    }
    setVoiceChatEnabled(characterId, value)
    try {
      await updateCharacterSettings(characterId, value)
    } catch (err: any) {
      // 409 = 服务端 has_voice 标记过期，角色实际无音色行。
      if (err?.status === 409) {
        showToast('请先为该角色配置音色，才能开启语音聊天', 'info')
        setVoiceChatEnabled(characterId, false)
        setVoicePickerOpen(true)
        return
      }
      // 网络抖动可能误报失败——先和服务端真实状态核对再决定是否回滚。
      try {
        const actual = await getCharacterSettings(characterId)
        setVoiceChatEnabled(characterId, actual.voice_enabled)
        if (actual.voice_enabled !== value) {
          showToast('语音开关切换失败，请稍后重试', 'error')
        }
      } catch {
        setVoiceChatEnabled(characterId, !value)
        showToast('语音开关切换失败，请稍后重试', 'error')
      }
    }
  }

  const handleVoicePickerConfirm = async (selection: VoiceSelection) => {
    setVoiceConfiguring(true)
    try {
      if (selection.type === 'preset' && selection.presetVoiceId) {
        // 配置预设音色
        await setPresetVoice(characterId, selection.presetVoiceId)
        showToast(`已配置音色：${selection.presetName || '预设音色'}`, 'success')
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
            showToast('文件过大（超过 20MB），请上传更短的录音', 'error')
            return
          }
        } catch {
          if (selection.cloneFile.size > 20 * 1024 * 1024) {
            showToast('无法处理该文件，请上传 10–30 秒的清晰录音', 'error')
            return
          }
        }
        await uploadVoiceClone(characterId, fileToUpload, 'fish')
        showToast('音色克隆已提交，处理中…', 'info')
        // 克隆需要等待，暂不自动开启语音聊天
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '音色配置失败，请重试'
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
                onClick={() => setVoicePickerOpen(true)}
                disabled={voiceConfiguring}
                className="rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
              >
                {voiceConfiguring ? '配置中…' : '去配置'}
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
