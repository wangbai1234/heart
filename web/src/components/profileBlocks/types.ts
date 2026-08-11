import type { ChromePalette } from '../../pages/CharacterProfilePage'
import type { ProfileBlock } from '../../services/api'

/** 每个区块组件收到的 props：窄化后的区块数据 + 配色。 */
export interface BlockProps<T extends ProfileBlock = ProfileBlock> {
  block: T
  chrome: ChromePalette
}

/** 从配色里取语义色，集中一处，改配色不用动区块。 */
export function blockColors(chrome: ChromePalette) {
  return {
    accent: chrome.taglineColor,
    primary: chrome.nameColor,
    muted: chrome.ageColor,
    hairline: 'rgba(255,255,255,0.08)',
    panel: 'rgba(255,255,255,0.03)',
  }
}
