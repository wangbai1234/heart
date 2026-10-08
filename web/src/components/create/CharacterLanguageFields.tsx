import { useTranslation } from 'react-i18next'
import { FieldCard, textInputCls } from './CreateShell'

export type CharacterLanguage = 'en' | 'ja' | 'ko'
export function CharacterLanguageFields({ language, worldBook, onLanguage, onWorldBook, castType, contentRating, onCastType, onContentRating }: {
  castType?: "single" | "multiple"
  contentRating?: "general" | "mature"
  onCastType?: (value: "single" | "multiple") => void
  onContentRating?: (value: "general" | "mature") => void
  language: CharacterLanguage
  worldBook: string
  onLanguage: (value: CharacterLanguage) => void
  onWorldBook: (value: string) => void
}) {
  const { t } = useTranslation()
  return <>
    <FieldCard label={t('characterReplyLanguage')} hint={t('characterReplyLanguageHint')}>
      <select aria-label={t('characterReplyLanguage')} className={`${textInputCls} h-[44px]`} value={language}
        onChange={e => onLanguage(e.target.value as CharacterLanguage)}>
        <option value="ja">日本語</option><option value="ko">한국어</option><option value="en">English</option>
      </select>
    </FieldCard>
    {onCastType && <FieldCard label={t('castType')}>
      <select className={`${textInputCls} h-[44px]`} value={castType} onChange={e => onCastType(e.target.value as 'single' | 'multiple')}>
        <option value="single">{t('singleCast')}</option><option value="multiple">{t('multipleCast')}</option>
      </select>
    </FieldCard>}
    {onContentRating && <FieldCard label={t('contentRating')}>
      <select className={`${textInputCls} h-[44px]`} value={contentRating} onChange={e => onContentRating(e.target.value as 'general' | 'mature')}>
        <option value="general">{t('generalRating')}</option><option value="mature">{t('matureRating')}</option>
      </select>
    </FieldCard>}
    <FieldCard label={t('worldBook')} hint={t('worldBookHint')}>
      <textarea aria-label={t('worldBook')} className={`${textInputCls} min-h-[120px] resize-y`} value={worldBook}
        onChange={e => onWorldBook(Array.from(e.target.value).slice(0, 10000).join(''))} />
      <p className="text-right text-[12px] text-[var(--color-text-muted)]">{Array.from(worldBook).length}/10000</p>
    </FieldCard>
  </>
}
