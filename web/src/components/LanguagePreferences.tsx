import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import i18n, { languageNames, locales, supportedLocale } from '../i18n'
import { getLanguagePreferences, saveLanguagePreferences, type LanguagePreferences as Preferences } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'
import { Button } from './ui/Button'

/** Fits the existing settings sheet; no separate international account page. */
export function LanguagePreferences() {
  const { t } = useTranslation()
  const [preferences, setPreferences] = useState<Preferences>({
    interface_language: supportedLocale(i18n.language),
    response_language: supportedLocale(i18n.language),
    action_style: 'parentheses',
  })
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let active = true
    void getLanguagePreferences().then(p => { if (active) { setPreferences(p); setLoaded(true) } }).catch(() => { if (active) setNotice(i18n.t('error')) })
    return () => { active = false }
  }, [])
  const save = async () => {
    setBusy(true)
    setNotice('')
    try {
      const saved = await saveLanguagePreferences(preferences)
      await i18n.changeLanguage(saved.interface_language)
      setNotice(i18n.t('saved'))
    } catch { setNotice(i18n.t('error')) }
    finally { setBusy(false) }
  }
  const selectClass = 'rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-3 py-2 text-[14px] text-[var(--color-ink)]'
  return (
    <div className="my-3 rounded-[14px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4">
      <h3 className="mb-3 text-[15px] font-semibold text-[var(--color-ink)]">{t('preferences')}</h3>
      {(['interface_language', 'response_language'] as const).map(key => (
        <label key={key} className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">
          {t(key === 'interface_language' ? 'interfaceLanguage' : 'responseLanguage')}
          <select className={selectClass} value={preferences[key]} disabled={busy || !loaded} onChange={e => setPreferences({ ...preferences, [key]: supportedLocale(e.target.value) })}>
            {locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}
          </select>
        </label>
      ))}
      <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">
        {t('actionStyle')}
        <select className={selectClass} value={preferences.action_style} disabled={busy || !loaded} onChange={e => setPreferences({ ...preferences, action_style: e.target.value as Preferences['action_style'] })}>
          {(['parentheses', 'asterisks', 'fullwidth'] as const).map(style => <option key={style} value={style}>{t(style)}</option>)}
        </select>
      </label>
      <Button size="sm" disabled={busy || !loaded} onClick={() => void save()}>{t('save')}</Button>
      {notice && <p className="mt-2 text-[13px] text-[var(--color-text-secondary)]" role="status">{notice}</p>}
    </div>
  )
}

export function InterfaceLanguageSelect() {
  const { t, i18n: current } = useTranslation()
  const userId = useAuthStore(s => s.user?.id)
  const [saving, setSaving] = useState(false)
  const selectLanguage = async (locale: typeof locales[number]) => {
    setSaving(true)
    try {
      if (userId) {
        const preferences = await getLanguagePreferences()
        await saveLanguagePreferences({ ...preferences, interface_language: locale })
      }
      await i18n.changeLanguage(locale)
    } catch { useToastStore.getState().show(i18n.t('error'), 'error') }
    finally { setSaving(false) }
  }
  return <select aria-label={t('interfaceLanguage')} value={supportedLocale(current.language)} className="rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-2 py-1 text-[13px] text-[var(--color-ink)]" disabled={saving} onChange={e => void selectLanguage(supportedLocale(e.target.value))}>{locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}</select>
}
