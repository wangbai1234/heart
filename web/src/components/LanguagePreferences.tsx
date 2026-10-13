import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import i18n, { availableLocales, languageNames, selectDeviceLocale, supportedLocale, type Locale } from '../i18n'
import type { LanguagePreferences as Preferences } from '../services/api'
import { useLanguageStore } from '../stores/languageStore'
import { useAuthStore } from '../stores/authStore'
import { useToastStore } from '../stores/toastStore'

export function withInterfaceLanguage(preferences: Preferences, language: Locale): Preferences {
  return { ...preferences, interface_language: language,
    response_language: preferences.response_follows_interface ? language : preferences.response_language, action_style: 'fullwidth' }
}
const selectClass = 'rounded-[10px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-3 py-2 text-[14px] text-[var(--color-ink)]'
function LanguageOptions({ retained }: { retained?: Locale }) {
  const codes = availableLocales()
  return <>{retained && !codes.includes(retained) && <option value={retained} disabled>{languageNames[retained]} ({i18n.t('languageUnavailable')})</option>}{codes.map(code => <option key={code} value={code}>{languageNames[code]}</option>)}</>
}

export function LanguagePreferences() {
  const { t } = useTranslation()
  const userId = useAuthStore(s => s.user?.id)
  const { preferences, busy, load } = useLanguageStore()
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let active = true
    setNotice('')
    void load().catch(() => { if (active) setNotice(i18n.t('error')) })
    return () => { active = false }
  }, [userId, load])
  const save = async (next: Preferences) => {
    setNotice('')
    try {
      await useLanguageStore.getState().save(next)
      if (useAuthStore.getState().user?.id === userId) setNotice(i18n.t('saved'))
    } catch { if (useAuthStore.getState().user?.id === userId) setNotice(i18n.t('error')) }
  }
  const language = preferences?.interface_language ?? supportedLocale(i18n.language)
  const mode = preferences?.response_mode ?? (preferences?.response_follows_interface === false ? 'fixed' : 'auto')
  return <div className="my-3 rounded-[14px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4">
    <h3 className="mb-3 text-[15px] font-semibold text-[var(--color-ink)]">{t('preferences')}</h3>
    <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">{t('interfaceLanguage')}
      <select className={selectClass} value={language} disabled={busy || !preferences} onChange={e => { if (preferences) void save(withInterfaceLanguage(preferences, supportedLocale(e.target.value))) }}><LanguageOptions retained={language} /></select>
    </label>
    <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">{t('responseMode')}
      <select className={selectClass} value={mode} disabled={busy || !preferences} onChange={e => { if (preferences) void save({ ...preferences, response_mode: e.target.value as Preferences['response_mode'], response_follows_interface: e.target.value !== 'fixed', response_language: language }) }}>
        <option value="auto">{t('responseAuto')}</option><option value="interface">{t('responseInterface')}</option><option value="character">{t('responseCharacter')}</option><option value="fixed">{t('responseFixed')}</option>
      </select>
    </label>
    {mode === 'fixed' && <label className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[14px] text-[var(--color-ink)]">{t('responseLanguage')}
      <select className={selectClass} value={preferences?.response_language} disabled={busy || !preferences} onChange={e => { if (preferences) void save({ ...preferences, response_mode: 'fixed', response_follows_interface: false, response_language: supportedLocale(e.target.value) }) }}><LanguageOptions retained={preferences?.response_language} /></select>
    </label>}
    <p className="text-[13px] text-[var(--color-text-secondary)]">{t('languageNextReply')}</p>
    {notice && <p className="mt-2 text-[13px] text-[var(--color-text-secondary)]" role="status">{notice}</p>}
  </div>
}

export function InterfaceLanguageSelect() {
  const { t, i18n: current } = useTranslation()
  const userId = useAuthStore(s => s.user?.id)
  const saving = useLanguageStore(s => s.busy)
  const selectLanguage = async (locale: Locale) => {
    try {
      if (userId) await useLanguageStore.getState().save({ interface_language: locale })
      else if (!useAuthStore.getState().user) await selectDeviceLocale(locale)
    } catch { if (useAuthStore.getState().user?.id === userId) useToastStore.getState().show(i18n.t('error'), 'error') }
  }
  return <select aria-label={t('interfaceLanguage')} value={supportedLocale(current.language)} className={selectClass} disabled={saving} onChange={e => void selectLanguage(supportedLocale(e.target.value))}><LanguageOptions /></select>
}
