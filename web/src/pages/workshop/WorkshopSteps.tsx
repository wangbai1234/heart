import { FieldCard, SectionHeading, textInputCls } from '../../components/create/CreateShell'
import { THEME_PRESETS } from '../../data/characterThemePresets'
import type { WorkshopState } from './workshopTypes'

export interface StepProps {
  state: WorkshopState
  updateField: <K extends keyof WorkshopState>(key: K, value: WorkshopState[K]) => void
}

type Row = { label: string; value: string }

/** 通用 label/value 行列表编辑器（档案/时间线/物件/对照/档案卡共用）。 */
function RowListEditor({
  rows,
  onChange,
  labelPlaceholder,
  valuePlaceholder,
  max,
  addLabel,
}: {
  rows: Row[]
  onChange: (rows: Row[]) => void
  labelPlaceholder: string
  valuePlaceholder: string
  max: number
  addLabel: string
}) {
  const update = (i: number, patch: Partial<Row>) =>
    onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i))
  return (
    <div className="space-y-3">
      {rows.map((row, i) => (
        <div key={i} className="flex gap-2 items-start">
          <input
            value={row.label}
            onChange={(e) => update(i, { label: e.target.value.slice(0, 20) })}
            placeholder={labelPlaceholder}
            className={`${textInputCls} w-[34%] h-[46px]`}
          />
          <input
            value={row.value}
            onChange={(e) => update(i, { value: e.target.value.slice(0, 120) })}
            placeholder={valuePlaceholder}
            className={`${textInputCls} flex-1 h-[46px]`}
          />
          <button
            onClick={() => remove(i)}
            aria-label="删除该行"
            className="w-[46px] h-[46px] shrink-0 rounded-[14px] flex items-center justify-center text-[var(--color-text-muted)] bg-[var(--color-glass-35)] border border-[var(--color-border-glass)] active:scale-95 transition-transform"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
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
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="档案信息" hint="职业、身份、状态——填几条关键设定" />
      <FieldCard label="档案条目" hint={`${state.dossierItems.length}/10 · 填满 3 条详情页更完整`}>
        <RowListEditor
          rows={state.dossierItems}
          onChange={(r) => updateField('dossierItems', r)}
          labelPlaceholder="身份"
          valuePlaceholder="例：帝国近卫军统领"
          max={10}
          addLabel="添加一条"
        />
      </FieldCard>
    </div>
  )
}

/** 第 4 步：独白 / 语气样本 → quote 区块。 */
export function Step4({ state, updateField }: StepProps) {
  const len = state.quote.length
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="独白样本" hint="一段第一人称的话，让人听见 Ta 的声音" />
      <FieldCard label="独白" hint={`${len}/200`}>
        <textarea
          value={state.quote}
          onChange={(e) => updateField('quote', e.target.value.slice(0, 200))}
          placeholder="用 Ta 的口吻说一句话。可以是态度、习惯、或对世界的看法。"
          rows={4}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label="署名" hint="可选，例：— 深夜值勤时">
        <input
          value={state.quoteAttribution}
          onChange={(e) => updateField('quoteAttribution', e.target.value.slice(0, 40))}
          placeholder="这句话出自什么场景"
          className={textInputCls}
        />
      </FieldCard>
    </div>
  )
}

const BG_OPTIONS: Array<{ id: 'timeline' | 'objects' | 'contrast'; name: string; desc: string }> = [
  { id: 'timeline', name: '时间线', desc: '按时间讲 Ta 的经历' },
  { id: 'objects', name: '随身物件', desc: '几件物品，各有来历' },
  { id: 'contrast', name: '表里反差', desc: '外表与内里的对照' },
]

/** 第 5 步：背景故事，三选一 → 对应区块出现。 */
export function Step5({ state, updateField }: StepProps) {
  const t = state.backgroundType
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="背景故事" hint="选一种最适合 Ta 的讲法" />
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
        <FieldCard label="时间线" hint={`${state.timelineItems.length}/8`}>
          <RowListEditor
            rows={state.timelineItems}
            onChange={(r) => updateField('timelineItems', r)}
            labelPlaceholder="时间"
            valuePlaceholder="例：十六岁，入伍"
            max={8}
            addLabel="添加一段经历"
          />
        </FieldCard>
      )}
      {t === 'objects' && (
        <FieldCard label="随身物件" hint={`${state.objectItems.length}/6`}>
          <RowListEditor
            rows={state.objectItems}
            onChange={(r) => updateField('objectItems', r)}
            labelPlaceholder="物件"
            valuePlaceholder="例：一枚旧怀表——父亲的遗物"
            max={6}
            addLabel="添加一件物品"
          />
        </FieldCard>
      )}
      {t === 'contrast' && (
        <>
          <div className="flex gap-2 mb-3">
            <input
              value={state.contrastLeftLabel}
              onChange={(e) => updateField('contrastLeftLabel', e.target.value.slice(0, 20))}
              placeholder="表（如：人前）"
              className={`${textInputCls} flex-1`}
            />
            <input
              value={state.contrastRightLabel}
              onChange={(e) => updateField('contrastRightLabel', e.target.value.slice(0, 20))}
              placeholder="里（如：人后）"
              className={`${textInputCls} flex-1`}
            />
          </div>
          <FieldCard label="对照项" hint={`${state.contrastPairs.length}/6`}>
            <RowListEditor
              rows={state.contrastPairs}
              onChange={(r) => updateField('contrastPairs', r)}
              labelPlaceholder="表现"
              valuePlaceholder="内里"
              max={6}
              addLabel="添加一组对照"
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
  return (
    <div className="space-y-2.5">
      {prompts.map((p, i) => (
        <div key={i} className="flex gap-2">
          <input
            value={p}
            onChange={(e) =>
              onChange(prompts.map((x, idx) => (idx === i ? e.target.value.slice(0, 60) : x)))
            }
            placeholder={`开场选项 ${i + 1}`}
            className={`${textInputCls} flex-1`}
          />
          <button
            onClick={() => onChange(prompts.filter((_, idx) => idx !== i))}
            aria-label="删除该选项"
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
          + 添加开场选项
        </button>
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
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="开场设计" hint="用户点进来看到的第一幕" />
      <FieldCard
        label="开场白"
        hint="首次对话逐字播放，不走实时生成"
      >
        <textarea
          value={state.opening}
          onChange={(e) => updateField('opening', e.target.value.slice(0, 1500))}
          placeholder="Ta 对用户说的第一段话，或第一幕场景。"
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
            富文本（含场景/心理描写）
          </label>
          <button
            onClick={onAssistOpening}
            disabled={assisting || state.persona.trim().length < 20}
            className="text-[13px] font-medium text-[var(--color-primary)] disabled:opacity-40"
          >
            {assisting ? '生成中...' : '帮我写'}
          </button>
        </div>
      </FieldCard>

      <FieldCard label="开场档案卡" hint="可选，聊天页顶部的一张设定卡">
        <input
          value={state.premiseLeadIn}
          onChange={(e) => updateField('premiseLeadIn', e.target.value.slice(0, 60))}
          placeholder="引导语（如：你被带到了……）"
          className={`${textInputCls} mb-2.5`}
        />
        <input
          value={state.premiseTitle}
          onChange={(e) => updateField('premiseTitle', e.target.value.slice(0, 40))}
          placeholder="卡片标题"
          className={`${textInputCls} mb-3`}
        />
        <RowListEditor
          rows={state.premiseRows}
          onChange={(r) => updateField('premiseRows', r)}
          labelPlaceholder="字段"
          valuePlaceholder="例：地点 / 深夜的军营"
          max={6}
          addLabel="添加一行"
        />
      </FieldCard>

      <FieldCard label="开场选项" hint="给用户 1-5 个开口的引子">
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
  { id: 'private', name: '私有', desc: '只有你能看到，立即可用' },
  { id: 'unlisted', name: '不公开', desc: '有链接可访问，需审核' },
  { id: 'public', name: '公开', desc: '出现在发现页，需审核' },
]

const HTML_MAX = 50 * 1024

/** 第 7 步：主题配色 + 可见性 + 高级 HTML（分层第二层）。 */
export function Step7({ state, updateField }: StepProps) {
  const htmlBytes = new Blob([state.customHtml]).size
  const htmlOver = htmlBytes > HTML_MAX
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="主题配色" hint="给详情页定个基调" />
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
                  Aa 示例文字
                </span>
              </div>
            </button>
          )
        })}
      </div>

      <SectionHeading index="" title="可见性" hint="公开与不公开会先进入审核" />
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

      <SectionHeading index="" title="高级模式" hint="会写 HTML？直接自定义详情页" />
      <FieldCard label="自定义 HTML" hint="开启后区块编辑器内容不再显示">
        <label className="flex items-center gap-2 text-[14px] text-[var(--color-ink)] mb-3">
          <input
            type="checkbox"
            checked={state.advancedHtmlMode}
            onChange={(e) => updateField('advancedHtmlMode', e.target.checked)}
            className="w-4 h-4 accent-[var(--color-primary)]"
          />
          启用高级 HTML
        </label>
        {state.advancedHtmlMode && (
          <>
            <textarea
              value={state.customHtml}
              onChange={(e) => updateField('customHtml', e.target.value)}
              placeholder="<section>...</section>（脚本与事件属性会被自动移除）"
              rows={8}
              spellCheck={false}
              className="w-full px-4 py-3 rounded-[14px] text-[13px] font-mono leading-[1.6] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]"
            />
            <div className="mt-2 text-[12px] text-right">
              <span className={htmlOver ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}>
                {(htmlBytes / 1024).toFixed(1)}KB / 50KB
                {htmlOver ? `（超出 ${((htmlBytes - HTML_MAX) / 1024).toFixed(1)}KB）` : ''}
              </span>
            </div>
          </>
        )}
      </FieldCard>
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
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="核心身份" hint="名字、性别、封面、一句话钩子——第一印象" />
      <label
        className={`relative block w-full aspect-[3/4] max-h-[360px] rounded-[20px] cursor-pointer overflow-hidden mb-4 ${
          state.coverUrl
            ? 'shadow-[0_12px_40px_-8px_rgba(0,0,0,0.3)]'
            : 'border-2 border-dashed border-[var(--color-border-glass)] bg-[var(--color-glass-35)]'
        }`}
      >
        {uploading ? (
          <div className="w-full h-full flex items-center justify-center text-[14px] text-[var(--color-text-secondary)]">上传中...</div>
        ) : state.coverUrl ? (
          <>
            <img src={state.coverUrl} alt="封面" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent" />
            <span className="absolute bottom-3 left-4 text-[13px] text-white/90 font-medium">点击更换封面</span>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2.5">
            <div className="w-[52px] h-[52px] rounded-full bg-gradient-to-br from-[#FFB7C5]/30 to-[#FF8FAB]/20 flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
            </div>
            <span className="text-[14px] text-[var(--color-ink)] font-medium">
              <span className="text-[var(--color-error)] mr-0.5">*</span>上传封面
            </span>
            <span className="text-[12px] text-[var(--color-text-muted)]">建议 3:4 竖图</span>
          </div>
        )}
        <input type="file" accept="image/*" onChange={onCoverUpload} className="hidden" />
      </label>

      <FieldCard label="名字" required>
        <input
          value={state.displayName}
          onChange={(e) => updateField('displayName', e.target.value.slice(0, 20))}
          placeholder="角色叫什么名字"
          className={textInputCls}
        />
      </FieldCard>
      <FieldCard label="性别" required>
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
              {g === 'male' ? '男' : '女'}
            </button>
          ))}
        </div>
      </FieldCard>
      <FieldCard label="一句话钩子" hint="荷尔蒙 / 危险感 / 反差，别平铺直叙">
        <input
          value={state.tagline}
          onChange={(e) => updateField('tagline', e.target.value.slice(0, 60))}
          placeholder="让人第一眼想点进去的一句话"
          className={textInputCls}
        />
      </FieldCard>
    </div>
  )
}

/** 第 2 步：人设与介绍。 */
export function Step2({ state, updateField }: StepProps) {
  const len = state.persona.length
  return (
    <div className="max-w-[560px] mx-auto">
      <SectionHeading title="人设与介绍" hint="人设至少 20 字，介绍和标签显示在详情页顶部" />
      <FieldCard label="人设描述" required hint={`${len}/1500 · 最少 20 字`}>
        <textarea
          value={state.persona}
          onChange={(e) => updateField('persona', e.target.value.slice(0, 1500))}
          placeholder="性格、特质、说话风格、核心设定……"
          rows={6}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label="简介" hint="显示在详情页名字下方">
        <textarea
          value={state.intro}
          onChange={(e) => updateField('intro', e.target.value.slice(0, 600))}
          placeholder="一段简短的介绍"
          rows={3}
          className="w-full px-4 py-3 rounded-[14px] text-[15px] leading-[1.7] resize-none bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </FieldCard>
      <FieldCard label="标签" hint="逗号分隔，最多 10 个">
        <input
          value={state.tags.join(', ')}
          onChange={(e) =>
            updateField('tags', e.target.value.split(',').map((t) => t.trim()).filter(Boolean).slice(0, 10))
          }
          placeholder="温柔, 强攻, 危险"
          className={textInputCls}
        />
      </FieldCard>
    </div>
  )
}
