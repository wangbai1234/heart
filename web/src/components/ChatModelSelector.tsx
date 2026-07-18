import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { useMembershipStore } from '../stores/membershipStore'
import { getPricing, type PricingModel } from '../services/api'
import { BottomSheet } from './ui/BottomSheet'

const MODEL_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  grok: 'Grok',
  claude: 'Claude',
}

// Fallback so the selector still renders if pricing fails to load.
const FALLBACK_MODELS: PricingModel[] = [
  { id: 'deepseek', label: 'DeepSeek', cost: 0, tiers_allowed: ['free', 'plus', 'immersive'] },
  { id: 'grok', label: 'Grok', cost: 3, tiers_allowed: ['plus', 'immersive'] },
  { id: 'claude', label: 'Claude', cost: 12, tiers_allowed: ['immersive'] },
]

export function ChatModelSelector({ characterId, isDark }: { characterId: string; isDark: boolean }) {
  const navigate = useNavigate()
  const model = useAppStore((s) => s.chatModel[characterId] ?? 'deepseek')
  const setChatModel = useAppStore((s) => s.setChatModel)
  const allowedModels = useMembershipStore((s) => s.entitlements.models)
  const membershipLoaded = useMembershipStore((s) => s.loaded)
  const refreshMembership = useMembershipStore((s) => s.refresh)
  const [models, setModels] = useState<PricingModel[]>(FALLBACK_MODELS)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!membershipLoaded) refreshMembership()
  }, [membershipLoaded, refreshMembership])

  useEffect(() => {
    getPricing()
      .then((p) => { if (p.models?.length) setModels(p.models) })
      .catch(() => { /* keep fallback */ })
  }, [])

  const isAllowed = (id: string) => id === 'deepseek' || allowedModels.includes(id)

  const pick = (m: PricingModel) => {
    if (!isAllowed(m.id)) {
      setOpen(false)
      navigate('/membership')
      return
    }
    setChatModel(characterId, m.id)
    setOpen(false)
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-medium active:scale-[0.96] transition-transform ${
          isDark
            ? 'bg-[rgba(255,255,255,0.08)] text-[rgba(228,228,231,0.85)]'
            : 'bg-[var(--color-glass-55)] text-[var(--color-text-secondary)]'
        }`}
        aria-label="选择对话模型"
      >
        <span>{MODEL_LABELS[model] ?? model}</span>
        <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="4,6 8,10 12,6" />
        </svg>
      </button>

      <BottomSheet open={open} onClose={() => setOpen(false)}>
        <div className="px-5 pt-2 pb-4">
          <p className="text-[16px] font-semibold text-[var(--color-ink)] text-center mb-1">选择对话模型</p>
          <p className="text-[12px] text-[var(--color-text-muted)] text-center mb-4">按次消耗 yuoyuo币，DeepSeek 免费</p>
          <div className="space-y-2">
            {models.map((m) => {
              const allowed = isAllowed(m.id)
              const selected = m.id === model
              return (
                <button
                  key={m.id}
                  onClick={() => pick(m)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-[14px] bg-[var(--color-glass-card)] border active:scale-[0.98] transition-transform"
                  style={{ borderColor: selected ? 'var(--color-primary)' : 'var(--color-border-glass)' }}
                >
                  <div className="flex items-center gap-2">
                    {!allowed && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    )}
                    <span className={`text-[15px] ${allowed ? 'text-[var(--color-ink)]' : 'text-[var(--color-text-muted)]'}`}>
                      {MODEL_LABELS[m.id] ?? m.label}
                    </span>
                  </div>
                  {allowed ? (
                    <span className="text-[13px] text-[var(--color-text-secondary)]">
                      {m.cost === 0 ? '免费' : `${m.cost} 币/次`}
                    </span>
                  ) : (
                    <span className="text-[12px] font-medium text-[var(--color-primary)]">升级会员解锁</span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </BottomSheet>
    </>
  )
}
