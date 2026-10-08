import i18n from './index'
import legacy from './legacy.json'

export const international = import.meta.env.VITE_INTERNATIONAL === 'true'
export function uiText(key: keyof typeof legacy, values: Record<string, string | number> = {}): string {
  return international ? i18n.t(key, values) : legacy[key].replace(/{{(\w+)}}/g, (_, name: string) => String(values[name] ?? ''))
}

// Only use on application-owned labels. Never pass user-authored content here.
const labelKeys = new Map(Object.entries(legacy).map(([key, value]) => [value, key as keyof typeof legacy]))
export function uiLabel(label: string): string {
  const key = labelKeys.get(label)
  return key ? uiText(key) : label
}
