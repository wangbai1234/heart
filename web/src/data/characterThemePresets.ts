/**
 * 主题配色预置 - UGC 创建重构批 2
 *
 * 从现有 45 个内置角色配色中提炼出 8 套预置，供用户自建角色选择。
 * 复用既有 ChromePalette 类型，不新建第四套配色结构。
 */

import type { ChromePalette } from '../pages/CharacterProfilePage'

export interface ThemePreset {
  id: string
  name: string // 中文名，UI 直接显示
  palette: ChromePalette
}

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: 'night_velvet',
    name: '夜色丝绒',
    palette: {
      bg: '#171019',
      coverBg: '#1B1320',
      scrimGradient: 'linear-gradient(to top,#171019 6%,rgba(23,16,25,.4) 40%,transparent 100%)',
      nameColor: '#ECE2E7',
      ageColor: '#B4A4AF',
      taglineColor: '#E08298',
      chipActiveBg: 'rgba(194,74,99,.08)',
      chipActiveBorder: 'rgba(194,74,99,.32)',
      chipActiveText: '#E08298',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#B4A4AF',
      ctaGradient: 'linear-gradient(105deg,#C24A63,#9C3A55)',
      ctaShadow: '0 10px 26px rgba(194,74,99,0.32)',
    },
  },
  {
    id: 'crimson_noir',
    name: '暗红黑金',
    palette: {
      bg: '#0F0B0D',
      coverBg: '#1A1315',
      scrimGradient: 'linear-gradient(to top,#0F0B0D 6%,rgba(15,11,13,.4) 40%,transparent 100%)',
      nameColor: '#EDE3E5',
      ageColor: '#B8A8AB',
      taglineColor: '#D85B74',
      chipActiveBg: 'rgba(184,58,82,.08)',
      chipActiveBorder: 'rgba(184,58,82,.32)',
      chipActiveText: '#D85B74',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#B8A8AB',
      ctaGradient: 'linear-gradient(105deg,#B83A52,#8C2D3E)',
      ctaShadow: '0 10px 26px rgba(184,58,82,0.38)',
    },
  },
  {
    id: 'amber_warm',
    name: '琥珀暖调',
    palette: {
      bg: '#13151A',
      coverBg: '#1B1D22',
      scrimGradient: 'linear-gradient(to top,#13151A 6%,rgba(19,21,26,.4) 40%,transparent 100%)',
      nameColor: '#EDE8E3',
      ageColor: '#B8AFA7',
      taglineColor: '#EAA968',
      chipActiveBg: 'rgba(208,138,78,.12)',
      chipActiveBorder: 'rgba(208,138,78,.32)',
      chipActiveText: '#EAA968',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#B8AFA7',
      ctaGradient: 'linear-gradient(105deg,#D08A4E,#B8743A)',
      ctaShadow: '0 10px 26px rgba(208,138,78,0.36)',
    },
  },
  {
    id: 'royal_gold',
    name: '皇室金',
    palette: {
      bg: '#0D0A0E',
      coverBg: '#1A0F16',
      scrimGradient: 'linear-gradient(to top,#0D0A0E 6%,rgba(13,10,14,.4) 40%,transparent 100%)',
      nameColor: '#EDE7E3',
      ageColor: '#B39A90',
      taglineColor: '#E4C482',
      chipActiveBg: 'rgba(212,165,87,.12)',
      chipActiveBorder: 'rgba(212,165,87,.32)',
      chipActiveText: '#E4C482',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#B39A90',
      ctaGradient: 'linear-gradient(105deg,#B8294B,#8C1F38)',
      ctaShadow: '0 10px 26px rgba(184,41,75,0.4)',
    },
  },
  {
    id: 'earth_sage',
    name: '大地灰褐',
    palette: {
      bg: '#0C0C0E',
      coverBg: '#141312',
      scrimGradient: 'linear-gradient(to top,#0C0C0E 6%,rgba(12,12,14,.4) 40%,transparent 100%)',
      nameColor: '#F2EDE6',
      ageColor: '#9A938A',
      taglineColor: '#C4937D',
      chipActiveBg: 'rgba(196,147,125,.1)',
      chipActiveBorder: 'rgba(196,147,125,.34)',
      chipActiveText: '#C4937D',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#9A938A',
      ctaGradient: 'linear-gradient(105deg,#C4937D,#9C6E58)',
      ctaShadow: '0 10px 26px rgba(196,147,125,0.32)',
    },
  },
  {
    id: 'ocean_depth',
    name: '深海青',
    palette: {
      bg: '#0A0C10',
      coverBg: '#12161C',
      scrimGradient: 'linear-gradient(to top,#0A0C10 6%,rgba(10,12,16,.4) 40%,transparent 100%)',
      nameColor: '#E2E8F0',
      ageColor: '#8B95A1',
      taglineColor: '#7FB0CE',
      chipActiveBg: 'rgba(51,96,126,.16)',
      chipActiveBorder: 'rgba(127,176,206,.32)',
      chipActiveText: '#9FC4DC',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#8B95A1',
      ctaGradient: 'linear-gradient(105deg,#33607E,#274A63)',
      ctaShadow: '0 10px 26px rgba(51,96,126,0.36)',
    },
  },
  {
    id: 'bright_warm',
    name: '明亮暖调',
    palette: {
      bg: '#16171B',
      coverBg: '#1E2025',
      scrimGradient: 'linear-gradient(to top,#16171B 6%,rgba(22,23,27,.4) 40%,transparent 100%)',
      nameColor: '#F2F0EC',
      ageColor: '#9AA0A8',
      taglineColor: '#FF8C42',
      chipActiveBg: 'rgba(255,140,66,.12)',
      chipActiveBorder: 'rgba(255,140,66,.34)',
      chipActiveText: '#FFB37A',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#9AA0A8',
      ctaGradient: 'linear-gradient(105deg,#FF8C42,#E86E1F)',
      ctaShadow: '0 10px 26px rgba(255,140,66,0.34)',
    },
  },
  {
    id: 'forest_mint',
    name: '森林薄荷',
    palette: {
      bg: '#080A0B',
      coverBg: '#101616',
      scrimGradient: 'linear-gradient(to top,#080A0B 6%,rgba(8,10,11,.4) 40%,transparent 100%)',
      nameColor: '#E6EFEE',
      ageColor: '#8A9A98',
      taglineColor: '#5AC8B4',
      chipActiveBg: 'rgba(90,200,180,.12)',
      chipActiveBorder: 'rgba(90,200,180,.34)',
      chipActiveText: '#7FD8C6',
      chipInactiveBg: 'rgba(255,255,255,.05)',
      chipInactiveBorder: 'rgba(255,255,255,.1)',
      chipInactiveText: '#8A9A98',
      ctaGradient: 'linear-gradient(105deg,#2E9E8C,#1F7566)',
      ctaShadow: '0 10px 26px rgba(46,158,140,0.34)',
    },
  },
]

export const DEFAULT_THEME_PRESET_ID = 'night_velvet'

// 根据 id 查找预置
export function getThemePresetById(id: string): ThemePreset | undefined {
  return THEME_PRESETS.find((p) => p.id === id)
}

// 获取默认预置
export function getDefaultThemePreset(): ThemePreset {
  return getThemePresetById(DEFAULT_THEME_PRESET_ID) ?? THEME_PRESETS[0]
}

/**
 * Reverse-lookup a preset id from a stored palette (edit flow). A UGC character
 * persists the resolved ChromePalette, not the preset id it came from, so on
 * edit we match by the distinctive bg + ctaGradient. Returns '' if no preset
 * matches (custom/legacy palette) — the editor then keeps the stored palette.
 */
export function findThemePresetIdByPalette(palette: { bg?: string; ctaGradient?: string } | null | undefined): string {
  if (!palette) return ''
  const match = THEME_PRESETS.find(
    (p) => p.palette.bg === palette.bg && p.palette.ctaGradient === palette.ctaGradient,
  )
  return match?.id ?? ''
}
