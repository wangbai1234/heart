import { useEffect, useMemo, useState } from 'react'
import { saveModelPreference, type ChatModelInfo } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { useModelsStore } from '../stores/modelsStore'
import { useToastStore } from '../stores/toastStore'
import { BottomSheet } from './ui/BottomSheet'

interface ModelSelectorSheetProps {
  open: boolean
  onClose: () => void
  characterId: string
}

const STATUS_COLOR: Record<ChatModelInfo['status'], string> = {
  smooth: '#22C55E',
  available: '#22C55E',
  slow: '#F59E0B',
  unavailable: '#9CA3AF',
}

function ModelRow({
  model,
  selected,
  onSelect,
}: {
  model: ChatModelInfo
  selected: boolean
  onSelect: () => void
}) {
  const unavailable = model.status === 'unavailable'
  return (
    <button
      type="button"
      disabled={unavailable}
      onClick={onSelect}
      className={`w-full rounded-[8px] border px-3.5 py-3 text-left transition-colors ${
        unavailable ? 'opacity-45' : 'active:bg-[var(--color-glass-75)]'
      }`}
      style={{ borderColor: selected ? 'var(--color-primary)' : 'var(--color-border-glass)' }}
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border"
          style={{ borderColor: selected ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
        >
          {selected && <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-primary)]" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center justify-between gap-3">
            <span className="text-[15px] font-semibold text-[var(--color-ink)]">{model.label}</span>
            <span className="shrink-0 text-[12px] font-medium text-[var(--color-primary)]">
              {model.included ? '会员免费' : `${model.cost_coins}币/次`}
            </span>
          </span>
          <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)]">
            {model.tags.map((tag) => <span key={tag}>{tag}</span>)}
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: STATUS_COLOR[model.status] }} />
              {model.status_label}
            </span>
          </span>
          <span className="mt-1 block text-[12px] leading-[1.45] text-[var(--color-text-muted)]">
            {model.description}
          </span>
        </span>
      </div>
    </button>
  )
}

export function ModelSelectorSheet({ open, onClose, characterId }: ModelSelectorSheetProps) {
  const models = useModelsStore((state) => state.models)
  const loading = useModelsStore((state) => state.loading)
  const refresh = useModelsStore((state) => state.refresh)
  const chatModel = useAppStore((state) => state.chatModel[characterId] ?? 'gemini-3.1')
  const setChatModel = useAppStore((state) => state.setChatModel)
  const [tab, setTab] = useState<'recommended' | 'all'>('recommended')
  const [candidate, setCandidate] = useState(chatModel)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!open) return
    setCandidate(chatModel)
    setTab('recommended')
    void refresh().catch(() => useToastStore.getState().show('模型列表加载失败', 'error'))
  }, [open, chatModel, refresh])

  const visibleModels = tab === 'recommended'
    ? models.filter((model) => model.status === 'smooth')
    : models
  const families = useMemo(
    () => Array.from(new Set(visibleModels.map((model) => model.family))),
    [visibleModels],
  )
  const selected = models.find((model) => model.id === candidate)
  const canConfirm = Boolean(selected && selected.status !== 'unavailable')

  const confirm = async () => {
    if (!canConfirm) return
    setConfirming(true)
    try {
      await saveModelPreference(characterId, candidate)
      setChatModel(characterId, candidate)
      onClose()
    } catch {
      useToastStore.getState().show('模型切换失败，请稍后重试', 'error')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <BottomSheet open={open} onClose={onClose}>
      <div className="flex h-[min(82dvh,720px)] flex-col">
        <div className="shrink-0">
          <h2 className="text-center text-[18px] font-semibold text-[var(--color-ink)]">选择对话模型</h2>
          <div className="mx-auto mt-3 grid h-9 w-full max-w-[240px] grid-cols-2 rounded-[8px] bg-[var(--color-glass-75)] p-1">
            {([['recommended', '推荐'], ['all', '全部']] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`rounded-[6px] text-[13px] font-medium ${
                  tab === key ? 'bg-[var(--color-surface)] text-[var(--color-ink)] shadow-sm' : 'text-[var(--color-text-muted)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-0.5">
          {loading && models.length === 0 && (
            <p className="py-12 text-center text-[13px] text-[var(--color-text-muted)]">正在查看模型状态…</p>
          )}
          {!loading && tab === 'recommended' && visibleModels.length === 0 && (
            <p className="py-12 text-center text-[13px] leading-6 text-[var(--color-text-muted)]">
              暂无流畅模型<br />可前往“全部”选择当前可用模型
            </p>
          )}
          {families.map((family) => (
            <section key={family} className="mb-4">
              {tab === 'all' && <h3 className="mb-2 text-[12px] font-medium text-[var(--color-text-muted)]">{family}</h3>}
              <div className="space-y-2">
                {visibleModels.filter((model) => model.family === family).map((model) => (
                  <ModelRow
                    key={model.id}
                    model={model}
                    selected={candidate === model.id}
                    onSelect={() => setCandidate(model.id)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="shrink-0 border-t border-[var(--color-border-glass)] bg-[var(--color-surface)] pt-3">
          <button
            type="button"
            disabled={!canConfirm || confirming}
            onClick={() => void confirm()}
            className="h-12 w-full rounded-[8px] bg-[var(--color-primary)] text-[15px] font-semibold text-white disabled:opacity-40"
          >
            {confirming ? '确认中…' : '确认'}
          </button>
        </div>
      </div>
    </BottomSheet>
  )
}
