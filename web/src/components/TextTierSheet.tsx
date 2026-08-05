import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BottomSheet } from './ui/BottomSheet'
import { useAppStore } from '../stores/appStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing } from '../services/api'
import type { CharacterId } from '../data/uiContent'

// 文字聊天两档 → LLM 模型。普通交流=deepseek（会员免费，体验版按币）；私密陪伴=grok。
const TEXT_TIERS = [
  { key: 'daily', model: 'deepseek', title: '普通交流', sub: '日常陪伴，温柔自然' },
  { key: 'private', model: 'grok', title: '私密陪伴', sub: '回复更快，更聪明' },
] as const

interface TextTierSheetProps {
  open: boolean
  onClose: () => void
  characterId: CharacterId
  isDark: boolean
}

export function TextTierSheet({ open, onClose, characterId, isDark }: TextTierSheetProps) {
  const navigate = useNavigate()
  const chatModel = useAppStore((s) => s.chatModel[characterId] ?? 'deepseek')
  const setChatModel = useAppStore((s) => s.setChatModel)
  const allowedModels = useMembershipStore((s) => s.entitlements.models)
  const freeItems = useMembershipStore((s) => s.entitlements.free)
  const membershipLoaded = useMembershipStore((s) => s.loaded)
  const refreshMembership = useMembershipStore((s) => s.refresh)
  const [pricing, setPricing] = useState<{ deepseekCost: number; grokCost: number } | null>(null)

  useEffect(() => {
    if (!open) return
    if (!membershipLoaded) refreshMembership()
    getPricing()
      .then((data) => {
        const deepseekCost = data.models.find((m) => m.id === 'deepseek')?.cost ?? 1
        const grokCost = data.models.find((m) => m.id === 'grok')?.cost ?? 3
        setPricing({ deepseekCost, grokCost })
      })
      .catch(() => { /* keep defaults */ })
  }, [open, membershipLoaded, refreshMembership])

  // DeepSeek 永久免费；其余看会员权益。
  const isModelAllowed = (model: string) => model === 'deepseek' || allowedModels.includes(model)

  // 定价标签：会员档免费的项目显示「免费」，否则显示 X币/条。
  const getTierLabel = (key: string) => {
    if (key === 'daily') return freeItems.includes('deepseek') ? '免费' : `${pricing?.deepseekCost ?? 1}币/条`
    if (key === 'private') return freeItems.includes('grok') ? '免费' : `${pricing?.grokCost ?? 3}币/条`
    return ''
  }

  const handleTier = (model: string) => {
    if (!isModelAllowed(model)) {
      onClose()
      navigate('/membership')
      return
    }
    setChatModel(characterId, model)
    onClose()
  }

  return (
    <BottomSheet open={open} onClose={onClose}>
      <h2 className={`mb-1 text-[18px] font-semibold tracking-[-0.02em] ${isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]'}`}>
        文字聊天
      </h2>
      <p className={`mb-4 text-[13px] leading-[1.5] ${isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]'}`}>
        选择陪伴风格，进阶风格按会员解锁
      </p>
      <div className="space-y-2.5">
        {TEXT_TIERS.map((t) => {
          const allowed = isModelAllowed(t.model)
          const selected = chatModel === t.model
          return (
            <button
              key={t.key}
              onClick={() => handleTier(t.model)}
              className={`w-full rounded-[18px] border px-4 py-3.5 text-left transition-transform active:scale-[0.99] ${
                isDark ? 'bg-[rgba(255,255,255,0.05)]' : 'bg-[rgba(255,255,255,0.5)]'
              }`}
              style={{ borderColor: selected ? '#FF8FAB' : (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.4)') }}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  {!allowed && (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={isDark ? 'rgba(236,233,244,0.5)' : 'rgba(47,54,74,0.42)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  )}
                  <span className={`text-[15px] font-medium ${allowed ? (isDark ? 'text-[#F3EFF8]' : 'text-[#2D3248]') : (isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]')}`}>{t.title}</span>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
                    isDark ? 'bg-[rgba(255,255,255,0.1)] text-[rgba(236,233,244,0.5)]' : 'bg-[rgba(0,0,0,0.06)] text-[rgba(47,54,74,0.45)]'
                  }`}>
                    {getTierLabel(t.key)}
                  </span>
                </div>
                {selected ? (
                  <span className="text-[12px] font-semibold text-[#FF7DA1]">使用中</span>
                ) : allowed ? null : (
                  <span className="text-[12px] font-medium text-[#FF7DA1]">升级会员解锁</span>
                )}
              </div>
              <p className={`mt-1 text-[12.5px] leading-[1.5] ${isDark ? 'text-[rgba(236,233,244,0.68)]' : 'text-[rgba(47,54,74,0.54)]'}`}>{t.sub}</p>
            </button>
          )
        })}
      </div>
    </BottomSheet>
  )
}
