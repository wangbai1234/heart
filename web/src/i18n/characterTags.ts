import i18n, { supportedLocale } from './index'
import labels from './characterTags.json'
import { localized } from './text'

/** Display only. Never replace stored tags or filter keys with a translation. */
export function characterTagLabel(tag: string, language = i18n.language): string {
  if (!localized) return tag
  const locale = supportedLocale(language)
  if (locale === 'zh') return tag
  const row = (labels as Record<string, Partial<Record<string, string>>>)[tag]
  return row?.[locale] ?? tag
}

/** Launch locales expose only reviewed taxonomy entries; source tags stay intact. */
export function restrictCharacterTags(language = i18n.language): boolean {
  return localized && ['en', 'vi', 'bn'].includes(supportedLocale(language))
}

export function visibleCharacterTags(tags: readonly string[], language = i18n.language): string[] {
  if (!restrictCharacterTags(language)) return [...tags]
  const locale = supportedLocale(language)
  return tags.filter(tag => Boolean((labels as Record<string, Partial<Record<string, string>>>)[tag]?.[locale]))
}
