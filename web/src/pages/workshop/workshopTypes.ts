import type {
  CharacterDraftDTO,
  ProfileBlock,
  PremiseCardData,
  StarterConfig,
} from '../../services/api'
import type { ChromePalette } from '../CharacterProfilePage'
import { getThemePresetById } from '../../data/characterThemePresets'

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

const DEFAULT_SLIDERS = {
  warmth: 50,
  talkativeness: 50,
  directness: 50,
  humor: 50,
  playfulness: 50,
  steadiness: 50,
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
