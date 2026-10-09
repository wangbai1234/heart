import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import i18n, { languageNames, locales, supportedLocale } from '../i18n'
import { getLanguagePreferences, saveLanguagePreferences, type LanguagePreferences as Preferences } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'

export function withInterfaceLanguage(preferences: Preferences, language: typeof locales[number]): Preferences {
  return {
    ...preferences, interface_language: language,
    response_language: preferences.response_follows_interface ? language : preferences.response_language,
    action_style: 'fullwidth',
  }
}

/** Autosave changes for the next turn; no reload or WebSocket reconnect. */
export function LanguagePreferences() {
  const { t } = useTranslation()
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let active = true
    void getLanguagePreferences().then(p => { if (active) setPreferences(p) })
      .catch(() => { if (active) setNotice(i18n.t('error')) })
    return () => { active = false }
  }, [])
  const save = async (next: Preferences) => {
    setBusy(true)
    setNotice('')
    try {
      const saved = await saveLanguagePreferences(next)
      setPreferences(saved)
      await i18n.changeLanguage(saved.interface_language)
      setNotice(i18n.t('saved'))
    } catch { setNotice(i18n.t('error')) }
    finally { setBusy(false) }
  }
  const selectClass = 'rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-3 py-2 text-[14px] text-[var(--color-ink)]'
  const language = preferences?.interface_language ?? supportedLocale(i18n.language)
  return (
    <div className="my-3 rounded-[14px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4">
      <h3 className="mb-3 text-[15px] font-semibold text-[var(--color-ink)]">{t('preferences')}</h3>
      <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">
        {t('interfaceLanguage')}
        <select className={selectClass} value={language} disabled={busy || !preferences} onChange={e => {
          if (preferences) void save(withInterfaceLanguage(preferences, supportedLocale(e.target.value)))
        }}>
          {locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}
        </select>
      </label>
      <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">
        {t('responseLanguage')}
        <select className={selectClass} value={preferences?.response_follows_interface !== false ? 'follow' : preferences.response_language} disabled={busy || !preferences} onChange={e => {
          if (preferences) void save({
            ...preferences, response_follows_interface: e.target.value === 'follow',
            response_language: e.target.value === 'follow' ? language : supportedLocale(e.target.value),
            action_style: 'fullwidth',
          })
        }}>
          <option value="follow">{t('followInterface')}</option>
          {locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}
        </select>
      </label>
      <p className="text-[13px] text-[var(--color-text-secondary)]">{t('languageNextReply')}</p>
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
        await saveLanguagePreferences(withInterfaceLanguage(preferences, locale))
      }
      await i18n.changeLanguage(locale)
    } catch { useToastStore.getState().show(i18n.t('error'), 'error') }
    finally { setSaving(false) }
  }
  return <select aria-label={t('interfaceLanguage')} value={supportedLocale(current.language)} className="rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-2 py-1 text-[13px] text-[var(--color-ink)]" disabled={saving} onChange={e => void selectLanguage(supportedLocale(e.target.value))}>{locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}</select>
}
