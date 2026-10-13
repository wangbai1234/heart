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
