import type {
  CharacterDraftDTO,
  ProfileBlock,
  PremiseCardData,
  StarterConfig,
} from '../../services/api'
import type { ChromePalette } from '../CharacterProfilePage'
import { getThemePresetById, findThemePresetIdByPalette } from '../../data/characterThemePresets'

export type QualityLevel = 'sketch' | 'draft' | 'shaped' | 'finished'

export interface WorkshopState {
  // Step 1 — 核心身份
  displayName: string
  gender: 'male' | 'female' | ''
  coverUrl: string
  tagline: string
  // Step 2 — 人设与介绍
  persona: string
  intro: string
  tags: string[]
  // Step 3 — 档案信息 → dossier
  dossierItems: Array<{ label: string; value: string }>
  // Step 4 — 独白 → quote
  quote: string
  quoteAttribution: string
  // Step 5 — 背景故事（三选一）
  backgroundType: 'timeline' | 'objects' | 'contrast' | ''
  timelineItems: Array<{ label: string; value: string }>
  objectItems: Array<{ label: string; value: string }>
  contrastLeftLabel: string
  contrastRightLabel: string
  contrastPairs: Array<{ label: string; value: string }>
  // Step 6 — 开场设计
  opening: string
  openingFormat: 'plain' | 'rich'
  premiseLeadIn: string
  premiseTitle: string
  premiseRows: Array<{ label: string; value: string }>
  premiseNote: string
  premiseWarning: string
  starterPrompts: string[]
  // Step 7 — 主题配色 + 可见性 + 高级 HTML
  uiChromeThemeId: string
  visibility: 'public' | 'unlisted' | 'private'
  advancedHtmlMode: boolean
  customHtml: string
}

export const EMPTY_STATE: WorkshopState = {
  displayName: '',
  gender: '',
  coverUrl: '',
  tagline: '',
  persona: '',
  intro: '',
  tags: [],
  dossierItems: [],
  quote: '',
  quoteAttribution: '',
  backgroundType: '',
  timelineItems: [],
  objectItems: [],
  contrastLeftLabel: '',
  contrastRightLabel: '',
  contrastPairs: [],
  opening: '',
  openingFormat: 'plain',
  premiseLeadIn: '',
  premiseTitle: '',
  premiseRows: [],
  premiseNote: '',
  premiseWarning: '',
  starterPrompts: [],
  uiChromeThemeId: '',
  visibility: 'private',
  advancedHtmlMode: false,
  customHtml: '',
}

export const STORAGE_KEY = 'workshop_draft_state'

export const QUALITY_LABELS: Record<QualityLevel, string> = {
  sketch: '素描',
  draft: '半成品',
  shaped: '有模样',
  finished: '成品',
}

/** 质感分级：每级对应新增区块，让用户看到"再填一步能得到什么"。 */
export function getQualityLevel(s: WorkshopState): QualityLevel {
  if (!s.displayName || s.persona.trim().length < 20) return 'sketch'
  if (!s.intro && s.tags.length === 0 && s.dossierItems.length < 3) return 'draft'
  const hasBackground =
    !!s.backgroundType &&
    (s.timelineItems.length > 0 || s.objectItems.length > 0 || s.contrastPairs.length > 0)
  if (!s.quote && !hasBackground && !s.opening) return 'shaped'
  return 'finished'
}

// 后端 SliderSet 要求 0.0–1.0 浮点，中性值 0.5（不是 0–100 UI 刻度）。
const DEFAULT_SLIDERS = {
  warmth: 0.5,
  talkativeness: 0.5,
  directness: 0.5,
  humor: 0.5,
  playfulness: 0.5,
  steadiness: 0.5,
}

/** 内容→区块：用户填什么，系统生成对应区块（反转"先选版式"）。 */
export function buildProfileBlocks(s: WorkshopState): ProfileBlock[] {
  const blocks: ProfileBlock[] = []
  const dossierRows = s.dossierItems.filter((r) => r.label.trim() && r.value.trim())
  if (dossierRows.length >= 1) {
    blocks.push({ type: 'dossier', title: '档案', rows: dossierRows.slice(0, 10) })
  }
  if (s.quote.trim()) {
    blocks.push({
      type: 'quote',
      text: s.quote.trim().slice(0, 200),
      ...(s.quoteAttribution.trim() ? { attribution: s.quoteAttribution.trim().slice(0, 40) } : {}),
    })
  }
  if (s.backgroundType === 'timeline') {
    const events = s.timelineItems.filter((r) => r.label.trim() && r.value.trim())
    if (events.length) blocks.push({ type: 'timeline', title: '经历', events: events.slice(0, 8) })
  } else if (s.backgroundType === 'objects') {
    const items = s.objectItems.filter((r) => r.label.trim() && r.value.trim())
    if (items.length) blocks.push({ type: 'objects', title: '随身之物', items: items.slice(0, 6) })
  } else if (s.backgroundType === 'contrast') {
    const pairs = s.contrastPairs.filter((r) => r.label.trim() && r.value.trim())
    if (pairs.length) {
      blocks.push({
        type: 'contrast',
        leftLabel: s.contrastLeftLabel.trim().slice(0, 20) || '表',
        rightLabel: s.contrastRightLabel.trim().slice(0, 20) || '里',
        pairs: pairs.slice(0, 6),
      })
    }
  }
  return blocks
}

function buildPremiseCard(s: WorkshopState, palette: ChromePalette | null): PremiseCardData | null {
  const rows = s.premiseRows.filter((r) => r.label.trim() && r.value.trim())
  if (!s.premiseTitle.trim() && rows.length === 0 && !s.premiseLeadIn.trim()) return null
  return {
    accent: palette?.taglineColor || '#E08298',
    leadIn: s.premiseLeadIn.trim().slice(0, 60),
    title: s.premiseTitle.trim().slice(0, 40) || s.displayName,
    rows: rows.slice(0, 6),
    ...(s.premiseNote.trim() ? { note: s.premiseNote.trim().slice(0, 200) } : {}),
    ...(s.premiseWarning.trim() ? { warning: s.premiseWarning.trim().slice(0, 200) } : {}),
  }
}

function buildStarterConfig(s: WorkshopState): StarterConfig | null {
  const prompts = s.starterPrompts.map((p) => p.trim()).filter(Boolean).slice(0, 5)
  if (prompts.length === 0) return null
  return { type: 'flat', prompts }
}

/** 汇总当前 state 成一份完整草稿。PATCH 是整体替换，每步都要重发全量。 */
export function buildDraft(s: WorkshopState): CharacterDraftDTO {
  const preset = s.uiChromeThemeId ? getThemePresetById(s.uiChromeThemeId) : undefined
  const palette = preset?.palette ?? null
  const blocks = buildProfileBlocks(s)
  const premise = buildPremiseCard(s, palette)
  const starter = buildStarterConfig(s)
  const useHtml = s.advancedHtmlMode && s.customHtml.trim().length > 0
  return {
    display_name: { zh: s.displayName.trim() },
    gender: s.gender || undefined,
    cover_url: s.coverUrl || undefined,
    tagline: s.tagline.trim() || undefined,
    intro: s.intro.trim() || undefined,
    persona: s.persona,
    tags: s.tags.length ? s.tags.slice(0, 10) : undefined,
    greeting_style: 'warm',
    sliders: DEFAULT_SLIDERS,
    creation_mode: 'workshop',
    visibility: s.visibility,
    opening: s.opening.trim() || undefined,
    opening_format: s.openingFormat,
    ui_chrome: palette,
    profile_blocks: useHtml ? [] : blocks,
    custom_html: useHtml ? s.customHtml : null,
    premise_card: premise,
    starter_config: starter,
  }
}

/**
 * Reverse of buildDraft: hydrate a WorkshopState from a saved draft (edit flow).
 * The draft stores resolved blocks/palette rather than the raw form fields, so
 * we unpack profile_blocks → dossier/quote/background and match the palette back
 * to a preset id. Unknown/legacy shapes degrade to empty (never throw).
 */
export function draftToWorkshopState(d: CharacterDraftDTO): WorkshopState {
  const s: WorkshopState = { ...EMPTY_STATE }
  s.displayName = d.display_name?.zh ?? d.display_name?.en ?? ''
  s.gender = d.gender === 'male' || d.gender === 'female' ? d.gender : ''
  s.coverUrl = d.cover_url ?? ''
  s.tagline = d.tagline ?? ''
  s.persona = d.persona ?? ''
  s.intro = d.intro ?? ''
  s.tags = Array.isArray(d.tags) ? d.tags.slice(0, 10) : []
  s.opening = d.opening ?? ''
  s.openingFormat = d.opening_format === 'rich' ? 'rich' : 'plain'
  s.visibility =
    d.visibility === 'public' || d.visibility === 'unlisted' ? d.visibility : 'private'
  s.uiChromeThemeId = findThemePresetIdByPalette(d.ui_chrome ?? null)

  // Advanced HTML takes precedence; otherwise unpack the structured blocks.
  if (d.custom_html && d.custom_html.trim()) {
    s.advancedHtmlMode = true
    s.customHtml = d.custom_html
  }
  for (const block of d.profile_blocks ?? []) {
    if (block.type === 'dossier') {
      s.dossierItems = block.rows.map((r) => ({ label: r.label, value: r.value }))
    } else if (block.type === 'quote') {
      s.quote = block.text
      s.quoteAttribution = block.attribution ?? ''
    } else if (block.type === 'timeline') {
      s.backgroundType = 'timeline'
      s.timelineItems = block.events.map((r) => ({ label: r.label, value: r.value }))
    } else if (block.type === 'objects') {
      s.backgroundType = 'objects'
      s.objectItems = block.items.map((r) => ({ label: r.label, value: r.value }))
    } else if (block.type === 'contrast') {
      s.backgroundType = 'contrast'
      s.contrastLeftLabel = block.leftLabel
      s.contrastRightLabel = block.rightLabel
      s.contrastPairs = block.pairs.map((r) => ({ label: r.label, value: r.value }))
    }
  }

  if (d.premise_card) {
    s.premiseLeadIn = d.premise_card.leadIn ?? ''
    s.premiseTitle = d.premise_card.title ?? ''
    s.premiseRows = (d.premise_card.rows ?? []).map((r) => ({ label: r.label, value: r.value }))
    s.premiseNote = d.premise_card.note ?? ''
    s.premiseWarning = d.premise_card.warning ?? ''
  }

  if (d.starter_config && d.starter_config.type === 'flat') {
    s.starterPrompts = d.starter_config.prompts.slice(0, 5)
  }

  return s
}
