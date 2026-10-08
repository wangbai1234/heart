import { useTranslation } from 'react-i18next'
import { uiText, uiLabel } from '../../i18n/text'
import { useState } from 'react'
import { FieldCard, SectionHeading, textInputCls } from '../../components/create/CreateShell'
import { THEME_PRESETS } from '../../data/characterThemePresets'
import { CHARACTER_ROLE_TAGS } from '../../data/uiContent'
import { VoicePickerSheet } from '../../components/VoicePickerSheet'
import type { WorkshopState } from './workshopTypes'

export interface StepProps {
  state: WorkshopState
  updateField: <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => void
}

type Row = { label: string; value: string }

const MAX_TAGS = 10
const MAX_TAG_LEN = 20

/** 标签选择器：预设标签 pill 可点选 + 自定义标签输入（复用角色创建的标签选择方式）。 */
function TagPicker({ tags, onChange }: { tags: string[]; onChange: (t: string[]) => void }) {
  useTranslation()
  const [custom, setCustom] = useState('')
  const toggle = (tag: string) =>
    onChange(tags.includes(tag) ? tags.filter((t) => t !== tag) : tags.length < MAX_TAGS ? [...tags, tag] : tags)
  const addCustom = () => {
    const t = custom.trim().slice(0, MAX_TAG_LEN)
    if (t && !tags.includes(t) && tags.length < MAX_TAGS) onChange([...tags, t])
    setCustom('')
  }
  const customTags = tags.filter((t) => !(CHARACTER_ROLE_TAGS as readonly string[]).includes(t))
  const pill = (active: boolean) =>
    `h-[32px] px-3.5 rounded-full text-[13px] font-medium border transition-all active:scale-[0.96] ${
      active
        ? 'bg-[rgba(255,183,197,0.22)] border-[rgba(255,183,197,0.55)] text-[#E86083]'
        : 'bg-[var(--color-glass-55)] border-[var(--color-border-glass)] text-[var(--color-text-secondary)]'
    }`
  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3">
        {CHARACTER_ROLE_TAGS.map((tag) => (
          <button key={tag} type="button" onClick={() => toggle(tag)} className={pill(tags.includes(tag))}>
            {uiLabel(tag)}
          </button>
        ))}
        {customTags.map((tag) => (
          <button key={tag} type="button" onClick={() => toggle(tag)} className={pill(true)}>
            {uiLabel(tag)}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustom() } }}
          placeholder={uiText('ui588')}
          maxLength={MAX_TAG_LEN}
          className={`${textInputCls} flex-1 h-[42px]`}
        />
        <button
          type="button"
          onClick={addCustom}
          className="w-[52px] h-[42px] shrink-0 rounded-[14px] bg-[rgba(255,183,197,0.22)] text-[#E86083] text-[20px] font-medium leading-none active:scale-[0.96] transition-transform"
        >
          ＋
        </button>
      </div>
    </div>
  )
}

/** 通用 label/value 行列表编辑器（档案/时间线/物件/对照/档案卡共用）。 */
function RowListEditor({
  rows,
  onChange,
  labelPlaceholder,
  valuePlaceholder,
  labelHeader,
  valueHeader,
  equalWidth = false,
  max,
  addLabel,
}: {
  rows: Row[]
  onChange: (rows: Row[]) => void
  labelPlaceholder: string
  valuePlaceholder: string
  /** 左列表头（可选）——不传则不显示表头行。 */
  labelHeader?: string
  /** 右列表头（可选）。 */
  valueHeader?: string
  /** true = 两列 50/50 等宽（表里反差用）；false = 左列窄右列宽。 */
  equalWidth?: boolean
  max: number
  addLabel: string
}) {
  useTranslation()
  const update = (i: number, patch: Partial<Row>) =>
    onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i))
  // min-w-0 是关键：input 默认 min-width:auto 会撑破 flex-1，导致右列被挤成小条。
  const labelCls = equalWidth ? 'flex-1 min-w-0' : 'w-[34%] shrink-0'
  const valueCls = equalWidth ? 'flex-1 min-w-0' : 'flex-1 min-w-0'
  return (
    <div className="space-y-3">
      {(labelHeader || valueHeader) && rows.length > 0 && (
        <div className="flex gap-1.5 items-center px-1">
          <span className={`${labelCls} text-[12px] text-[var(--color-text-muted)]`}>{labelHeader}</span>
          <span className={`${valueCls} text-[12px] text-[var(--color-text-muted)]`}>{valueHeader}</span>
          <span className="w-[40px] shrink-0" />
        </div>
      )}
      {rows.map((row, i) => (
        <div key={i} className="flex gap-1.5 items-start">
          <input
            value={row.label}
            onChange={(e) => update(i, { label: e.target.value.slice(0, 20) })}
            placeholder={labelPlaceholder}
            className={`${textInputCls} ${labelCls} h-[46px]`}
          />
          <input
            value={row.value}
            onChange={(e) => update(i, { value: e.target.value.slice(0, 120) })}
            placeholder={valuePlaceholder}
            className={`${textInputCls} ${valueCls} h-[46px]`}
          />
          <button
            onClick={() => remove(i)}
            aria-label={uiText('ui589')}
            className="w-[40px] h-[40px] shrink-0 rounded-[14px] flex items-center justify-center text-[var(--color-text-muted)] bg-[var(--color-glass-35)] border border-[var(--color-border-glass)] active:scale-95 transition-transform"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
      {rows.length < max && (
        <button
          onClick={() => onChange([...rows, { label: '', value: '' }])}
          className="w-full h-[46px] rounded-[14px] border border-dashed border-[var(--color-border-glass)] text-[14px] text-[var(--color-text-secondary)] active:bg-[var(--color-glass-35)] transition-colors"
        >
          + {addLabel}
        </button>
      )}
    </div>
  )
}

/** 第 3 步：档案信息 → dossier 区块。填够 1 条即在详情页出现。 */
export function Step3({ state, updateField }: StepProps) {
  useTranslation()
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui590')} hint={uiText('ui591')} />
      <FieldCard label={uiText('ui592')} hint={uiText('dynamic36', { v0: state.dossierItems.length })}>
        <RowListEditor
          rows={state.dossierItems}
          onChange={(r) => updateField('dossierItems', r)}
          labelHeader={uiText('ui593')}
          valueHeader={uiText('ui594')}
          labelPlaceholder={uiText('ui595')}
          valuePlaceholder={uiText('ui596')}
          max={10}
          addLabel={uiText('ui597')}
        />
      </FieldCard>
    </div>
  )
}

/** 第 4 步：独白 / 语气样本 → quote 区块。 */
export function Step4({ state, updateField }: StepProps) {
  useTranslation()
  const len = state.quote.length
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui598')} hint={uiText('ui599')} />
      <FieldCard label={uiText('ui600')} hint={`${len}/200`}>
        <textarea
          value={state.quote}
          onChange={(e) => updateField('quote', e.target.value.slice(0, 200))}
          placeholder={uiText('ui601')}
          rows={4}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label={uiText('ui602')} hint={uiText('ui603')}>
        <input
          value={state.quoteAttribution}
          onChange={(e) => updateField('quoteAttribution', e.target.value.slice(0, 40))}
          placeholder={uiText('ui604')}
          className={textInputCls}
        />
      </FieldCard>
    </div>
  )
}

const BG_OPTIONS: Array<{ id: 'timeline' | 'objects' | 'contrast'; name: string; desc: string }> = [
  { id: 'timeline', get name() { return uiText('ui605') }, get desc() { return uiText('ui606') } },
  { id: 'objects', get name() { return uiText('ui607') }, get desc() { return uiText('ui608') } },
  { id: 'contrast', get name() { return uiText('ui609') }, get desc() { return uiText('ui610') } },
]

/** 第 5 步：背景故事，三选一 → 对应区块出现。 */
export function Step5({ state, updateField }: StepProps) {
  useTranslation()
  const t = state.backgroundType
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui611')} hint={uiText('ui612')} />
      <div className="grid grid-cols-3 gap-2.5 mb-5">
        {BG_OPTIONS.map((o) => (
          <button
            key={o.id}
            onClick={() => updateField('backgroundType', t === o.id ? '' : o.id)}
            className={`rounded-[16px] p-3 text-left border transition-all ${
              t === o.id
                ? 'border-[var(--color-primary)] bg-[var(--color-glass-75)] shadow-[0_4px_16px_rgba(255,143,171,0.18)]'
                : 'border-[var(--color-border-glass)] bg-[var(--color-glass-35)]'
            }`}
          >
            <div className="text-[14px] font-semibold text-[var(--color-ink)] mb-1">{o.name}</div>
            <div className="text-[11px] leading-[1.4] text-[var(--color-text-muted)]">{o.desc}</div>
          </button>
        ))}
      </div>

      {t === 'timeline' && (
        <FieldCard label={uiText('ui605')} hint={`${state.timelineItems.length}/8`}>
          <RowListEditor
            rows={state.timelineItems}
            onChange={(r) => updateField('timelineItems', r)}
            labelHeader={uiText('ui613')}
            valueHeader={uiText('ui614')}
            labelPlaceholder={uiText('ui615')}
            valuePlaceholder={uiText('ui616')}
            max={8}
            addLabel={uiText('ui617')}
          />
        </FieldCard>
      )}
      {t === 'objects' && (
        <FieldCard label={uiText('ui607')} hint={`${state.objectItems.length}/6`}>
          <RowListEditor
            rows={state.objectItems}
            onChange={(r) => updateField('objectItems', r)}
            labelHeader={uiText('ui618')}
            valueHeader={uiText('ui619')}
            labelPlaceholder={uiText('ui620')}
            valuePlaceholder={uiText('ui621')}
            max={6}
            addLabel={uiText('ui622')}
          />
        </FieldCard>
      )}
      {t === 'contrast' && (
        <>
          <FieldCard label={uiText('ui623')} hint={uiText('ui624')}>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-[12px] text-[var(--color-text-muted)] mb-1.5">{uiText('ui625')}</label>
                <input
                  value={state.contrastLeftLabel}
                  onChange={(e) => updateField('contrastLeftLabel', e.target.value.slice(0, 20))}
                  placeholder={uiText('ui626')}
                  className={textInputCls}
                />
              </div>
              <div className="flex-1">
                <label className="block text-[12px] text-[var(--color-text-muted)] mb-1.5">{uiText('ui627')}</label>
                <input
                  value={state.contrastRightLabel}
                  onChange={(e) => updateField('contrastRightLabel', e.target.value.slice(0, 20))}
                  placeholder={uiText('ui628')}
                  className={textInputCls}
                />
              </div>
            </div>
          </FieldCard>
          <FieldCard label={uiText('ui629')} hint={uiText('dynamic37', { v0: state.contrastPairs.length })}>
            <RowListEditor
              rows={state.contrastPairs}
              onChange={(r) => updateField('contrastPairs', r)}
              labelHeader={state.contrastLeftLabel.trim() || uiText('ui625')}
              valueHeader={state.contrastRightLabel.trim() || uiText('ui627')}
              labelPlaceholder={uiText('ui630')}
              valuePlaceholder={uiText('ui631')}
              equalWidth
              max={6}
              addLabel={uiText('ui632')}
            />
          </FieldCard>
        </>
      )}
    </div>
  )
}

/** 简单字符串列表编辑器（开场选项）。 */
function PromptListEditor({
  prompts,
  onChange,
  max,
}: {
  prompts: string[]
  onChange: (p: string[]) => void
  max: number
}) {
  useTranslation()
  return (
    <div className="space-y-2.5">
      {prompts.map((p, i) => (
        <div key={i} className="flex gap-2">
          <input
            value={p}
            onChange={(e) =>
              onChange(prompts.map((x, idx) => (idx === i ? e.target.value.slice(0, 60) : x)))
            }
            placeholder={uiText('dynamic38', { v0: i + 1 })}
            className={`${textInputCls} flex-1`}
          />
          <button
            onClick={() => onChange(prompts.filter((_, idx) => idx !== i))}
            aria-label={uiText('ui633')}
            className="w-[46px] h-[50px] shrink-0 rounded-[14px] flex items-center justify-center text-[var(--color-text-muted)] bg-[var(--color-glass-35)] border border-[var(--color-border-glass)]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
      {prompts.length < max && (
        <button
          onClick={() => onChange([...prompts, ''])}
          className="w-full h-[46px] rounded-[14px] border border-dashed border-[var(--color-border-glass)] text-[14px] text-[var(--color-text-secondary)]"
        >
          {uiText('ui634')}</button>
      )}
    </div>
  )
}

/** 第 6 步：开场设计 — opening + premise_card + starter_config。 */
export function Step6({
  state,
  updateField,
  onAssistOpening,
  assisting,
}: StepProps & { onAssistOpening: () => void; assisting: boolean }) {
  useTranslation()
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui635')} hint={uiText('ui636')} />
      <FieldCard
        label={uiText('ui449')}
        hint={uiText('ui637')}
      >
        <textarea
          value={state.opening}
          onChange={(e) => updateField('opening', e.target.value.slice(0, 1500))}
          placeholder={uiText('ui638')}
          rows={5}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
        <div className="mt-2 flex items-center justify-between">
          <label className="flex items-center gap-2 text-[13px] text-[var(--color-text-secondary)]">
            <input
              type="checkbox"
              checked={state.openingFormat === 'rich'}
              onChange={(e) => updateField('openingFormat', e.target.checked ? 'rich' : 'plain')}
              className="w-4 h-4 accent-[var(--color-primary)]"
            />
            {uiText('ui639')}</label>
          <button
            onClick={onAssistOpening}
            disabled={assisting || state.persona.trim().length < 20}
            className="text-[13px] font-medium text-[var(--color-primary)] disabled:opacity-40"
          >
            {assisting ? uiText('ui450') : uiText('ui640')}
          </button>
        </div>
      </FieldCard>

      <FieldCard label={uiText('ui641')} hint={uiText('ui642')}>
        <input
          value={state.premiseLeadIn}
          onChange={(e) => updateField('premiseLeadIn', e.target.value.slice(0, 60))}
          placeholder={uiText('ui643')}
          className={`${textInputCls} mb-2.5`}
        />
        <input
          value={state.premiseTitle}
          onChange={(e) => updateField('premiseTitle', e.target.value.slice(0, 40))}
          placeholder={uiText('ui644')}
          className={`${textInputCls} mb-3`}
        />
        <RowListEditor
          rows={state.premiseRows}
          onChange={(r) => updateField('premiseRows', r)}
          labelPlaceholder={uiText('ui645')}
          valuePlaceholder={uiText('ui646')}
          max={6}
          addLabel={uiText('ui647')}
        />
      </FieldCard>

      <FieldCard label={uiText('ui648')} hint={uiText('ui649')}>
        <PromptListEditor
          prompts={state.starterPrompts}
          onChange={(p) => updateField('starterPrompts', p)}
          max={5}
        />
      </FieldCard>
    </div>
  )
}

const VISIBILITY_OPTIONS: Array<{
  id: 'private' | 'unlisted' | 'public'
  name: string
  desc: string
}> = [
  { id: 'private', get name() { return uiText('ui650') }, get desc() { return uiText('ui651') } },
  { id: 'unlisted', get name() { return uiText('ui652') }, get desc() { return uiText('ui653') } },
  { id: 'public', get name() { return uiText('ui44') }, get desc() { return uiText('ui654') } },
]

const HTML_MAX = 50 * 1024

/** 第 7 步：主题配色 + 可见性 + 高级 HTML（分层第二层）。
 * voicePickerOpen 由父组件持有——底部「创建角色」按钮需要在弹窗打开时隐藏，避免重叠。 */
export function Step7({
  state,
  updateField,
  voicePickerOpen,
  setVoicePickerOpen,
}: StepProps & {
  voicePickerOpen: boolean
  setVoicePickerOpen: (open: boolean) => void
}) {
  useTranslation()
  const htmlBytes = new Blob([state.customHtml]).size
  const htmlOver = htmlBytes > HTML_MAX
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui452')} hint={uiText('ui655')} />
      <div className="grid grid-cols-2 gap-2.5 mb-6">
        {THEME_PRESETS.map((p) => {
          const active = state.uiChromeThemeId === p.id
          return (
            <button
              key={p.id}
              onClick={() => updateField('uiChromeThemeId', active ? '' : p.id)}
              className={`relative rounded-[16px] overflow-hidden h-[76px] border-2 transition-all ${
                active ? 'border-[var(--color-primary)] scale-[0.98]' : 'border-transparent'
              }`}
              style={{ background: p.palette.bg }}
            >
              <div className="absolute inset-0" style={{ background: p.palette.scrimGradient }} />
              <div className="absolute inset-0 flex flex-col justify-end p-3">
                <span className="text-[14px] font-semibold" style={{ color: p.palette.nameColor }}>
                  {p.name}
                </span>
                <span
                  className="text-[11px] mt-0.5"
                  style={{ color: p.palette.taglineColor }}
                >
                  {uiText('ui656')}</span>
              </div>
            </button>
          )
        })}
      </div>

      <SectionHeading index="" title={uiText('ui657')} hint={uiText('ui658')} />
      <div className="space-y-2.5 mb-6">
        {VISIBILITY_OPTIONS.map((o) => (
          <button
            key={o.id}
            onClick={() => updateField('visibility', o.id)}
            className={`w-full flex items-center justify-between p-3.5 rounded-[16px] border text-left transition-all ${
              state.visibility === o.id
                ? 'border-[var(--color-primary)] bg-[var(--color-glass-75)]'
                : 'border-[var(--color-border-glass)] bg-[var(--color-glass-35)]'
            }`}
          >
            <div>
              <div className="text-[15px] font-medium text-[var(--color-ink)]">{o.name}</div>
              <div className="text-[12px] text-[var(--color-text-muted)] mt-0.5">{o.desc}</div>
            </div>
            <div
              className={`w-[20px] h-[20px] rounded-full border-2 shrink-0 ${
                state.visibility === o.id
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)]'
                  : 'border-[var(--color-border-glass)]'
              }`}
            />
          </button>
        ))}
      </div>

      <SectionHeading index="" title={uiText('ui457')} hint={uiText('ui460')} />
      <button
        onClick={() => setVoicePickerOpen(true)}
        className="w-full flex items-center justify-between p-3.5 rounded-[16px] border border-[var(--color-border-glass)] bg-[var(--color-glass-35)] text-left transition-all active:scale-[0.98] mb-6"
      >
        <div>
          <div className="text-[15px] font-medium text-[var(--color-ink)]">
            {state.voiceSelection.type === 'preset'
              ? state.voiceSelection.presetName
              : state.voiceSelection.type === 'clone'
                ? uiText('ui458')
                : uiText('ui659')}
          </div>
          {!state.voiceSelection.type && (
            <div className="text-[12px] text-[var(--color-text-muted)] mt-0.5">
              {uiText('ui660')}</div>
          )}
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-text-muted)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9,6 15,12 9,18" />
        </svg>
      </button>

      <SectionHeading index="" title={uiText('ui661')} hint={uiText('ui662')} />
      <FieldCard label={uiText('ui663')} hint={uiText('ui664')}>
        <label className="flex items-center gap-2 text-[14px] text-[var(--color-ink)] mb-3">
          <input
            type="checkbox"
            checked={state.advancedHtmlMode}
            onChange={(e) => updateField('advancedHtmlMode', e.target.checked)}
            className="w-4 h-4 accent-[var(--color-primary)]"
          />
          {uiText('ui665')}</label>
        {state.advancedHtmlMode && (
          <>
            <textarea
              value={state.customHtml}
              onChange={(e) => updateField('customHtml', e.target.value)}
              placeholder={uiText('ui666')}
              rows={8}
              spellCheck={false}
              className="w-full px-4 py-3 rounded-[14px] text-[13px] font-mono leading-[1.6] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
            />
            <div className="mt-2 text-[12px] text-right">
              <span className={htmlOver ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}>
                {(htmlBytes / 1024).toFixed(1)}KB / 50KB
                {htmlOver ? uiText('dynamic39', { v0: ((htmlBytes - HTML_MAX) / 1024).toFixed(1) }) : ''}
              </span>
            </div>
          </>
        )}
      </FieldCard>

      <VoicePickerSheet
        open={voicePickerOpen}
        onClose={() => setVoicePickerOpen(false)}
        gender={state.gender === 'male' || state.gender === 'female' ? state.gender : undefined}
        onConfirm={(selection) => updateField('voiceSelection', selection)}
        initialSelection={state.voiceSelection}
      />
    </div>
  )
}

export { HTML_MAX }

/** 第 1 步：核心身份。 */
export function Step1({
  state,
  updateField,
  onCoverUpload,
  uploading,
}: StepProps & { onCoverUpload: (e: React.ChangeEvent<HTMLInputElement>) => void; uploading: boolean }) {
  useTranslation()
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui667')} hint={uiText('ui668')} />

      {/* 封面：小尺寸左置 + 右侧说明（对齐快速创建与 nimoo） */}
      <FieldCard label={uiText('ui440')} required>
        <div className="flex gap-3.5">
          <label
            className={`relative shrink-0 w-[104px] h-[140px] rounded-[12px] cursor-pointer overflow-hidden ${
              state.coverUrl ? '' : 'border-2 border-dashed border-[var(--color-border-glass)] bg-[var(--color-glass-55)]'
            }`}
          >
            {uploading ? (
              <div className="w-full h-full flex items-center justify-center text-[12px] text-[var(--color-text-secondary)]">{uiText('ui439')}</div>
            ) : state.coverUrl ? (
              <img src={state.coverUrl} alt={uiText('ui440')} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center gap-1.5">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                <span className="text-[12px] text-[var(--color-text-muted)]">{uiText('ui441')}</span>
              </div>
            )}
            <input type="file" accept="image/*" onChange={onCoverUpload} className="hidden" />
          </label>
          <ul className="flex-1 text-[12px] leading-[1.6] text-[var(--color-text-muted)] space-y-1.5 pt-0.5">
            <li>{uiText('ui442')}</li>
            <li>{uiText('ui443')}</li>
            <li>{uiText('ui489')}</li>
          </ul>
        </div>
      </FieldCard>

      <FieldCard label={uiText('ui669')} required>
        <input
          value={state.displayName}
          onChange={(e) => updateField('displayName', e.target.value.slice(0, 20))}
          placeholder={uiText('ui670')}
          className={textInputCls}
        />
      </FieldCard>
      <FieldCard label={uiText('ui398')} required>
        <div className="flex gap-3">
          {(['male', 'female'] as const).map((g) => (
            <button
              key={g}
              onClick={() => updateField('gender', g)}
              className={`flex-1 h-[48px] rounded-[14px] text-[15px] font-medium transition-all ${
                state.gender === g
                  ? 'bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white shadow-[0_4px_16px_rgba(255,143,171,0.32)]'
                  : 'bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)]'
              }`}
            >
              {g === 'male' ? uiText('ui381') : uiText('ui380')}
            </button>
          ))}
        </div>
      </FieldCard>
      <FieldCard label={uiText('ui671')} hint={uiText('ui672')}>
        <input
          value={state.tagline}
          onChange={(e) => updateField('tagline', e.target.value.slice(0, 60))}
          placeholder={uiText('ui673')}
          className={textInputCls}
        />
      </FieldCard>
    </div>
  )
}

/** 第 2 步：人设与介绍。 */
export function Step2({ state, updateField }: StepProps) {
  useTranslation()
  const len = state.persona.length
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title={uiText('ui674')} hint={uiText('ui675')} />
      <FieldCard label={uiText('ui676')} required hint={uiText('dynamic40', { v0: len })}>
        <textarea
          value={state.persona}
          onChange={(e) => updateField('persona', e.target.value.slice(0, 5000))}
          placeholder={uiText('ui677')}
          rows={6}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label={uiText('ui678')} hint={uiText('ui679')}>
        <textarea
          value={state.intro}
          onChange={(e) => updateField('intro', e.target.value.slice(0, 500))}
          placeholder={uiText('ui680')}
          rows={3}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label={uiText('ui681')} hint={uiText('dynamic41', { v0: state.tags.length })}>
        <TagPicker tags={state.tags} onChange={(t) => updateField('tags', t)} />
      </FieldCard>
    </div>
  )
}
