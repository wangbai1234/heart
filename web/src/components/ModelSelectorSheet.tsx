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

type Brand = 'gemini' | 'deepseek' | 'claude' | 'grok' | 'gpt'

const BRAND_META: Record<Brand, { label: string; icon: string }> = {
  gemini: { label: '双子座', icon: '/assets/models/gemini.svg' },
  deepseek: { label: 'DeepSeek', icon: '/assets/models/deepseek.svg' },
  claude: { label: '小克', icon: '/assets/models/claude.svg' },
  grok: { label: 'Grok', icon: '/assets/models/grok.svg' },
  gpt: { label: 'GPT', icon: '/assets/models/openai.svg' },
}

function brandFor(modelId: string): Brand {
  if (modelId.startsWith('gemini')) return 'gemini'
  if (modelId.startsWith('deepseek')) return 'deepseek'
  if (modelId.startsWith('claude')) return 'claude'
  if (modelId.startsWith('grok')) return 'grok'
  return 'gpt'
}

function ModelBrandIcon({ brand, size = 42 }: { brand: Brand; size?: number }) {
  const meta = BRAND_META[brand]
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-[8px] bg-white shadow-[0_3px_12px_rgba(8,5,12,0.2)]"
      style={{ width: size, height: size }}
    >
      <img
        src={meta.icon}
        alt={`${meta.label}品牌图标`}
        className="h-[62%] w-[62%] object-contain"
      />
    </span>
  )
}

function SignalBadge({ model }: { model: ChatModelInfo }) {
  const smooth = model.status === 'smooth' || model.status === 'available'
  const color = model.status === 'unavailable' ? '#9B94A3' : model.status === 'slow' ? '#F0B46B' : '#56DCA0'
  return (
    <span
      className="inline-flex h-6 shrink-0 items-end gap-[2px] rounded-[5px] px-2 pb-[5px] pt-1 text-[11px] font-medium"
      style={{ color, backgroundColor: `${color}1A` }}
    >
      <span className="mb-[1px] flex h-3 items-end gap-[1.5px]" aria-hidden="true">
        {[4, 7, 10, 13].map((height) => (
          <span key={height} className="w-[2px] rounded-full" style={{ height, backgroundColor: color }} />
        ))}
      </span>
      <span>{smooth ? '流畅' : model.status_label}</span>
    </span>
  )
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
      aria-pressed={selected}
      className={`relative w-full overflow-hidden rounded-[8px] border px-3.5 py-3 text-left transition-[border-color,background-color,transform,box-shadow] ${
        unavailable ? 'cursor-not-allowed opacity-45' : 'active:scale-[0.99]'
      }`}
      style={{
        borderColor: selected ? '#C09BFF' : 'rgba(255,255,255,0.1)',
        backgroundColor: selected ? 'rgba(173,126,232,0.18)' : 'rgba(255,255,255,0.07)',
        boxShadow: selected
          ? 'inset 0 0 0 1px rgba(192,155,255,0.7), 0 8px 24px rgba(10,5,15,0.16)'
          : '0 5px 18px rgba(10,5,15,0.1)',
      }}
    >
      {selected && <span className="absolute inset-y-0 left-0 w-[3px] bg-[#D7B6FF]" aria-hidden="true" />}
      <span className="flex min-w-0 items-start gap-2.5">
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center gap-2">
            <SignalBadge model={model} />
            <span className="min-w-0 truncate text-[15px] font-semibold text-white">{model.label}</span>
          </span>
          <span className="mt-2 flex flex-wrap items-center gap-1.5">
            {model.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex h-6 items-center rounded-[5px] border border-white/8 bg-black/12 px-2 text-[11px] text-[#E8DDEB]"
              >
                {tag}
              </span>
            ))}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-2">
          <span className="rounded-[6px] bg-black/22 px-2.5 py-1.5 text-[12px] font-semibold tabular-nums text-[#F6E8CF]">
            {model.included ? '会员免费' : `${model.cost_coins}币/次`}
          </span>
          <span
            className={`flex h-5 w-5 items-center justify-center rounded-full border ${
              selected
                ? 'border-[#D8BBFF] bg-[#D8BBFF] text-[#33263F]'
                : 'border-white/25 text-transparent'
            }`}
            aria-hidden="true"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2.3 6.1 4.8 8.4 9.7 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        </span>
      </span>
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
  const [expandedBrand, setExpandedBrand] = useState<Brand | null>(brandFor(chatModel))
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!open) return
    setCandidate(chatModel)
    setTab('recommended')
    setExpandedBrand(brandFor(chatModel))
    void refresh().catch(() => useToastStore.getState().show('模型列表加载失败', 'error'))
  }, [open, chatModel, refresh])

  const visibleModels = tab === 'recommended'
    ? models.filter((model) => model.status === 'smooth')
    : models
  const brands = useMemo(
    () => Array.from(new Set(visibleModels.map((model) => brandFor(model.id)))),
    [visibleModels],
  )
  const openBrand = expandedBrand && brands.includes(expandedBrand) ? expandedBrand : brands[0]
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
    <BottomSheet
      open={open}
      onClose={onClose}
      sheetClassName="overflow-hidden bg-[linear-gradient(180deg,#4B3A58_0%,#2A2133_30%,#1C1722_100%)] shadow-[0_-18px_60px_rgba(12,7,18,0.42)]"
      handleClassName="bg-white/28"
      contentClassName="px-4 pb-4 sm:px-5"
    >
      <div className="mx-auto flex h-[min(86dvh,760px)] w-full max-w-[520px] flex-col text-white">
        <div className="shrink-0 pb-3 text-center">
          <div className="flex items-center justify-center gap-2">
            <span className="text-[13px] text-[#F3C6D7]" aria-hidden="true">✦</span>
            <h2 className="text-[21px] font-semibold tracking-[0] text-white">模型选择</h2>
            <span className="text-[13px] text-[#F3C6D7]" aria-hidden="true">✦</span>
          </div>
          <p className="mt-1 text-[13px] text-[#CCBFCE]">今晚，想让谁陪你聊？</p>
          <div className="mx-auto mt-3 grid h-9 w-full max-w-[238px] grid-cols-2 rounded-[8px] border border-white/8 bg-black/18 p-1">
            {([['recommended', '推荐'], ['all', '全部']] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`rounded-[6px] text-[13px] font-medium transition-colors ${
                  tab === key
                    ? 'bg-white/16 text-white shadow-[0_2px_10px_rgba(10,5,15,0.2)]'
                    : 'text-[#BFB2C2]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="scrollbar-hide min-h-0 flex-1 overflow-y-auto px-0.5 pb-3">
          {loading && models.length === 0 && (
            <p className="py-12 text-center text-[13px] text-[#BFB2C2]">正在查看模型状态…</p>
          )}
          {!loading && tab === 'recommended' && visibleModels.length === 0 && (
            <p className="py-12 text-center text-[13px] leading-6 text-[#BFB2C2]">
              暂无流畅模型<br />可前往“全部”选择当前可用模型
            </p>
          )}
          <div className="space-y-3">
            {brands.map((brand) => {
              const meta = BRAND_META[brand]
              const brandModels = visibleModels.filter((model) => brandFor(model.id) === brand)
              const isOpen = openBrand === brand
              const smooth = brandModels.some((model) => model.status === 'smooth')
              const selectableCount = brandModels.filter((model) => model.status !== 'unavailable').length
              return (
                <section key={brand}>
                  <button
                    type="button"
                    onClick={() => setExpandedBrand(isOpen ? null : brand)}
                    aria-expanded={isOpen}
                    className={`relative flex w-full items-center gap-3 rounded-[8px] border px-3 py-3 text-left transition-colors ${
                      isOpen ? 'border-white/18 bg-white/12' : 'border-white/8 bg-white/8'
                    }`}
                  >
                    {smooth && (
                      <span className="absolute -top-[7px] left-3 rounded-[4px] bg-[#2CA76C] px-2 py-0.5 text-[10px] font-semibold text-white shadow-[0_2px_8px_rgba(44,167,108,0.35)]">
                        流畅
                      </span>
                    )}
                    <ModelBrandIcon brand={brand} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[17px] font-semibold text-white">{meta.label}</span>
                      <span className="mt-0.5 block text-[11px] text-[#BFB2C2]">
                        {brandModels.length} 个聊天风格
                      </span>
                    </span>
                    <span className="inline-flex shrink-0 items-center gap-2 rounded-[7px] bg-black/20 px-2.5 py-2 text-[11px] text-[#DED2E0]">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          selectableCount > 0
                            ? 'bg-[#56DCA0] shadow-[0_0_8px_rgba(86,220,160,0.65)]'
                            : 'bg-[#8B8490]'
                        }`}
                      />
                      {selectableCount} 个可选
                    </span>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 18 18"
                      fill="none"
                      className={`shrink-0 text-[#D8CCDA] transition-transform ${isOpen ? 'rotate-180' : ''}`}
                      aria-hidden="true"
                    >
                      <path d="m4.5 6.75 4.5 4.5 4.5-4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>

                  {isOpen && (
                    <div className="mt-2 space-y-2 pl-2 sm:pl-3">
                      {brandModels.map((model) => (
                        <ModelRow
                          key={model.id}
                          model={model}
                          selected={candidate === model.id}
                          onSelect={() => setCandidate(model.id)}
                        />
                      ))}
                    </div>
                  )}
                </section>
              )
            })}
          </div>
        </div>

        <div className="shrink-0 border-t border-white/10 bg-[#1C1722]/92 pt-3">
          <button
            type="button"
            disabled={!canConfirm || confirming}
            onClick={() => void confirm()}
            className="h-12 w-full rounded-[8px] bg-[linear-gradient(100deg,#F1D8C9_0%,#E9AFC7_34%,#C878DE_67%,#A748F2_100%)] text-[15px] font-semibold text-white shadow-[0_8px_26px_rgba(193,88,221,0.3)] transition-transform active:scale-[0.99] disabled:opacity-40"
          >
            {confirming ? '确认中…' : '确认'}
          </button>
        </div>
      </div>
    </BottomSheet>
  )
}
