import { uiText } from '../i18n/text'
/** RAW 后端关系阶段 → 前端中文标签（恋爱意味但克制）。 */
const STAGE_LABELS: Record<string, string> = {
  get STRANGER() { return uiText('more405') },
  get ACQUAINTANCE() { return uiText('more406') },
  get FRIEND() { return uiText('more406') }, // 设计里 ACQUAINTANCE/FRIEND 同归「靠近」
  get CONFIDANT() { return uiText('more407') },
  get ROMANTIC_INTEREST() { return uiText('more408') },
  get LOVER() { return uiText('more409') },
  get BONDED() { return uiText('more410') },
  get cold_war() { return uiText('ui313') }, // 独立态，不混入 6 段进度
  get COLD_WAR() { return uiText('ui313') }, // 容错：万一后端给大写
}

/** 6 段主进度顺序（cold_war 不参与，是独立态）。 */
export const STAGE_ORDER = [
  'STRANGER',
  'ACQUAINTANCE',
  'FRIEND',
  'CONFIDANT',
  'ROMANTIC_INTEREST',
  'LOVER',
  'BONDED',
] as const

export function stageLabel(rawStage: string): string {
  return STAGE_LABELS[rawStage] ?? uiText('more405')
}

/** cold_war 是独立态，不参与「x 段进度」的进度条渲染。 */
export function isColdWar(rawStage: string): boolean {
  return rawStage.toLowerCase() === 'cold_war'
}

/** intimacy 0..1 → 显示百分比整数。 */
export function intimacyPercent(intimacy: number): number {
  return Math.round(Math.max(0, Math.min(1, intimacy)) * 100)
}

/** 「心动 · 68%」组合串（cold_war 不带百分比）。 */
export function stageWithIntimacy(rawStage: string, intimacy: number): string {
  if (isColdWar(rawStage)) return stageLabel(rawStage)
  return `${stageLabel(rawStage)} · ${intimacyPercent(intimacy)}%`
}

/**
 * Index of a stage in the 6-stage progression, for upgrade comparisons.
 * cold_war and unknown stages return -1 (never counts as an upgrade).
 */
export function stageOrderIndex(rawStage: string): number {
  return STAGE_ORDER.indexOf(rawStage as (typeof STAGE_ORDER)[number])
}
