import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import i18n, { languageNames, locales, supportedLocale } from '../i18n'
import { useAuthStore } from '../stores/authStore'
import type { AuthUser, CharacterDTO, CharacterProfileDTO, TokenResponse } from '../services/api'
import { api, json, initialPreferences, type Preferences } from './api'
import { InternationalChat } from './InternationalChat'
import './international.css'

export function LanguageSelect() {
  const { t } = useTranslation()
  return <select aria-label={t('language')} value={supportedLocale(i18n.language)} onChange={event => void i18n.changeLanguage(event.target.value)}>
    {locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}
  </select>
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return children ? <p className={error ? 'intl-notice intl-error' : 'intl-notice'} role={error ? 'alert' : 'status'}>{children}</p> : null
}
function RequireAccount({ children }: { children: ReactNode }) {
  const user = useAuthStore(s => s.user)
  const token = useAuthStore(s => s.accessToken)
  const location = useLocation()
  if (!token) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (!user?.age_verified && location.pathname !== '/account') return <Navigate to="/account" replace />
  return children
}
export function InternationalApp() {
  const { t } = useTranslation()
  const token = useAuthStore(s => s.accessToken)
  const location = useLocation()
  useEffect(() => { document.getElementById('__initial_splash__')?.remove() }, [])
  useEffect(() => {
    let active = true
    if (!token) return
    void api<{ user: AuthUser }>('/auth/me').then(result => { if (active) useAuthStore.getState().setUser(result.user) }).catch(() => {})
    void api<Preferences>('/profile/preferences').then(result => { if (active) void i18n.changeLanguage(result.interface_language) }).catch(() => {})
    return () => { active = false }
  }, [token])
  useEffect(() => { document.title = 'yuoyuo — AI characters & stories' }, [])
  return <div className="intl-app">
    <header className="intl-header"><Link to="/" className="intl-brand">yuoyuo<span> / stories with you</span></Link><div className="intl-header-actions"><LanguageSelect />{!token && <Link className="intl-button small" to="/login">{t('signIn')}</Link>}</div></header>
    <nav className="intl-nav" aria-label={t('discover')}>{[['/', 'discover'], ['/chats', 'chats'], ['/create', 'create'], ['/account', 'account']].map(([to, label]) => <Link key={to} to={to} aria-current={location.pathname === to ? 'page' : undefined}>{t(label)}</Link>)}</nav>
    <main className="intl-main"><Routes>
      <Route path="/" element={<Discover />} />
      <Route path="/character" element={<Navigate to="/" replace />} />
      <Route path="/character/:id" element={<CharacterDetail />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Login initialMode="register" />} />
      <Route path="/account" element={token ? <Account /> : <Navigate to="/login" replace />} />
      <Route path="/settings/*" element={<Navigate to="/account" replace />} />
      <Route path="/create" element={<RequireAccount><CreateCharacter /></RequireAccount>} />
      <Route path="/chats" element={<RequireAccount><ChatList /></RequireAccount>} />
      <Route path="/chat/:characterId" element={<RequireAccount><InternationalChat /></RequireAccount>} />
      <Route path="/legal/:type" element={<Legal />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></main>
    <footer className="intl-footer"><p>{t('aiNotice')}</p><div>{['terms', 'privacy', 'contentPolicy', 'refunds', 'contact'].map(type => <Link key={type} to={`/legal/${type}`}>{t(type)}</Link>)}</div><small>© 2026 yuoyuo</small></footer>
  </div>
}
function Discover() {
  const { t } = useTranslation()
  const token = useAuthStore(s => s.accessToken)
  const [characters, setCharacters] = useState<CharacterDTO[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('loading')
  useEffect(() => { let active = true; api<{ characters: CharacterDTO[] }>('/characters').then(result => { if (active) { setCharacters(result.characters); setStatus('') } }).catch(() => { if (active) setStatus('error') }); return () => { active = false } }, [token, t])
  const filtered = characters.filter(c => `${c.display_name} ${c.tagline ?? ''}`.toLowerCase().includes(query.toLowerCase()))
  return <><section className="intl-hero"><div><p className="intl-eyebrow">{t('heroEyebrow')}</p><h1>{t('heroTitle')}</h1><p>{t('heroBody')}</p><Link className="intl-button" to="/create">{t('heroCta')} <span aria-hidden>↗</span></Link><small>{t('freePreview')}</small></div><div className="intl-hero-art" aria-hidden><div className="intl-orbit"/><span>Every story<br/>starts with hello.</span><b>y.</b></div></section>
    <section><div className="intl-section-heading"><h2>{t('catalogTitle')}</h2><input aria-label={t('search')} placeholder={t('search')} value={query} onChange={e => setQuery(e.target.value)} /></div>
      {status ? <Notice error={status === 'error'}>{t(status)}</Notice> : !filtered.length ? <div className="intl-empty">{t('catalogEmpty')}</div> : <div className="intl-grid">{filtered.map(c => <Link className="intl-character-card" to={`/character/${encodeURIComponent(c.id)}`} key={c.id}><div className="intl-cover">{c.cover_url && <img src={c.cover_url} alt="" loading="lazy" />}<span>{t('aiLabel')}</span></div><div><h3>{c.display_name}</h3><p>{c.tagline}</p>{c.is_owner && <small>{t('myCharacters')}</small>}</div></Link>)}</div>}
    </section></>
}
import { useParams } from 'react-router-dom'
function CharacterDetail() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const [character, setCharacter] = useState<CharacterProfileDTO | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { let active = true; setCharacter(null); api<CharacterProfileDTO>(`/characters/${encodeURIComponent(id)}/profile`).then(c => { if (active) setCharacter(c) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [id, t])
  if (!character) return <Notice error={!!error}>{error || t('loading')}</Notice>
  return <article className="intl-detail"><Link to="/">← {t('back')}</Link><div className="intl-detail-grid">{character.cover_url && <img className="intl-detail-cover" src={character.cover_url} alt="" />}<div><p className="intl-eyebrow">{t('aiLabel')}</p><h1>{character.display_name}</h1><p className="intl-lead">{character.tagline}</p><h2>{t('intro')}</h2><p className="intl-preserve">{character.intro}</p><p>{character.one_liner}</p><Link className="intl-button" to={`/chat/${encodeURIComponent(id)}`}>{t('startChat')}</Link><p><a href={`mailto:support@yuoyuo.app?subject=${encodeURIComponent(`Character report: ${id}`)}`}>{t('report')}</a></p></div></div></article>
}
function Login({ initialMode = 'login' }: { initialMode?: 'login' | 'register' }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<'login' | 'register' | 'reset'>(initialMode)
  const [email, setEmail] = useState(''), [password, setPassword] = useState(''), [code, setCode] = useState('')
  const [agree, setAgree] = useState(false), [busy, setBusy] = useState(false), [notice, setNotice] = useState(''), [error, setError] = useState(''), [cooldown, setCooldown] = useState(0)
  const [pending, setPending] = useState<TokenResponse | null>(null)
  useEffect(() => { if (!cooldown) return; const timer = setTimeout(() => setCooldown(cooldown - 1), 1000); return () => clearTimeout(timer) }, [cooldown])
  async function sendCode() {
    setBusy(true); setError('')
    try { const result = await api<{ cooldown: number }>('/auth/otp/request', json('POST', { email, purpose: mode === 'register' ? 'register' : 'password_reset' })); setCooldown(result.cooldown); setNotice(t('codeSent')) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const registrationPreferences = initialPreferences()
  async function finish(result: TokenResponse) {
    if (mode === 'register' && !result.needs_restoration) {
      await api('/profile/preferences', { ...json('PUT', registrationPreferences), headers: { Authorization: `Bearer ${result.access_token}` } })
      await i18n.changeLanguage(registrationPreferences.interface_language)
    }
    useAuthStore.getState().setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, user: result.user })
    if (result.needs_restoration) { setPending(result); return }
    const from = (location.state as { from?: string } | null)?.from
    navigate(result.user.age_verified ? (from?.startsWith('/') && !from.startsWith('//') ? from : '/') : '/account', { replace: true })
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setNotice('')
    if (mode === 'register' && !agree) { setError(t('legalRequired')); return }
    setBusy(true)
    try { const path = mode === 'login' ? '/auth/login/password' : mode === 'register' ? '/auth/register' : '/auth/password/reset'; const body = mode === 'login' ? { email, password } : mode === 'register' ? { email, password, otp_code: code } : { email, new_password: password, otp_code: code }; await finish(await api<TokenResponse>(path, json('POST', body))) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <section className="intl-panel intl-auth"><p className="intl-eyebrow">yuoyuo</p><h1>{t(mode === 'login' ? 'signIn' : mode === 'register' ? 'join' : 'resetPassword')}</h1><LanguageSelect /><Notice error>{error}</Notice><Notice>{notice}</Notice>{pending ? <><p>{t('restoreHint')}</p><button disabled={busy} onClick={async () => { setBusy(true); try { await api('/account/restore', json('POST', {})); navigate('/account') } catch (e) { setError((e as Error).message) } finally { setBusy(false) } }}>{t('restore')}</button></> : <form onSubmit={submit}><label>{t('email')}<input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></label><label>{t(mode === 'reset' ? 'newPassword' : 'password')}<input type="password" minLength={8} required autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={e => setPassword(e.target.value)} /></label>{mode !== 'login' && <label>{t('code')}<div className="intl-inline"><input required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" value={code} onChange={e => setCode(e.target.value)} /><button type="button" disabled={busy || cooldown > 0 || !email} onClick={() => void sendCode()}>{cooldown ? t('resendIn', { seconds: cooldown }) : t('sendCode')}</button></div></label>}{mode === 'register' && <label className="intl-check"><input type="checkbox" checked={agree} onChange={e => setAgree(e.target.checked)} />{t('legalAgree')}</label>}<button className="intl-button" disabled={busy}>{busy ? t('loading') : t(mode === 'login' ? 'signIn' : mode === 'register' ? 'join' : 'resetPassword')}</button><div className="intl-inline"><button type="button" className="intl-text-button" onClick={() => { setMode(mode === 'register' ? 'login' : 'register'); setError('') }}>{t(mode === 'register' ? 'signIn' : 'join')}</button><button type="button" className="intl-text-button" onClick={() => { setMode(mode === 'reset' ? 'login' : 'reset'); setError('') }}>{t(mode === 'reset' ? 'signIn' : 'forgot')}</button></div></form>}</section>
}
function Account() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const [preferences, setPreferences] = useState<Preferences>(initialPreferences)
  const [name, setName] = useState(user?.display_name ?? ''), [birthdate, setBirthdate] = useState(user?.birthdate ?? '')
  const [notice, setNotice] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [balance, setBalance] = useState(0), [confirm, setConfirm] = useState(''), [deleting, setDeleting] = useState(false)
  const [characters, setCharacters] = useState<CharacterDTO[]>([])
  useEffect(() => {
    let active = true
    void Promise.all([api<Preferences>('/profile/preferences'), api<{ balance: number }>('/credits/balance'), api<{ characters: CharacterDTO[] }>('/characters')]).then(([p, b, c]) => { if (active) { setPreferences(p); setBalance(b.balance); setCharacters(c.characters.filter(character => character.is_owner)) } }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [])
  async function action(run: () => Promise<void>) { setBusy(true); setError(''); setNotice(''); try { await run() } catch (e) { setError((e as Error).message) } finally { setBusy(false) } }
  return <div className="intl-account"><h1>{t('account')}</h1><Notice error>{error}</Notice><Notice>{notice}</Notice><section className="intl-panel"><h2>{user?.age_verified ? t('profile') : t('completeProfile')}</h2><p>{user?.email}</p><form onSubmit={e => { e.preventDefault(); void action(async () => { const result = await api<{ age_verified: boolean | null }>('/profile/complete', json('POST', { display_name: name, birthdate, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone })); const me = await api<{ user: AuthUser }>('/auth/me'); useAuthStore.getState().setUser(me.user); if (result.age_verified === false) setError(t('ageRequired')); else setNotice(t('saved')) }) }}><label>{t('displayName')}<input required maxLength={20} value={name} onChange={e => setName(e.target.value)} /></label><label>{t('birthdate')}<input required type="date" max={new Date().toISOString().slice(0, 10)} value={birthdate} onChange={e => setBirthdate(e.target.value)} /></label><small>{t('profileHint')}</small><button disabled={busy}>{t('save')}</button></form></section>
    <section className="intl-panel"><h2>{t('preferences')}</h2><p>{t('preferenceHint')}</p><form onSubmit={e => { e.preventDefault(); void action(async () => { await api('/profile/preferences', json('PUT', preferences)); await i18n.changeLanguage(preferences.interface_language); setNotice(i18n.t('saved')) }) }}>{(['interface_language', 'response_language'] as const).map(key => <label key={key}>{t(key === 'interface_language' ? 'interfaceLanguage' : 'responseLanguage')}<select value={preferences[key]} onChange={e => setPreferences({ ...preferences, [key]: supportedLocale(e.target.value) })}>{locales.map(locale => <option key={locale} value={locale}>{languageNames[locale]}</option>)}</select></label>)}<label>{t('actionStyle')}<select value={preferences.action_style} onChange={e => setPreferences({ ...preferences, action_style: e.target.value as Preferences['action_style'] })}>{['parentheses', 'asterisks', 'fullwidth'].map(style => <option key={style} value={style}>{t(style)}</option>)}</select></label><button disabled={busy}>{t('save')}</button></form></section>
    <section className="intl-panel"><h2>{t('balance', { count: balance })}</h2><p>{t('creditHint')}</p><p>{t('purchasesClosed')}</p><button disabled={busy} onClick={() => void action(async () => { const result = await api<{ granted: boolean; balance: number }>('/credits/checkin', json('POST', {})); setBalance(result.balance); setNotice(t(result.granted ? 'claimed' : 'alreadyClaimed')) })}>{t('checkin')}</button></section>
    <section className="intl-panel"><h2>{t('myCharacters')}</h2>{characters.length ? characters.map(c => <div className="intl-list-row" key={c.id}><Link to={`/character/${encodeURIComponent(c.id)}`}>{c.display_name}</Link><small>{t(c.review_status === 'pending' ? 'pendingReview' : c.visibility)}</small><Link to={`/create?edit=${encodeURIComponent(c.id)}`}>{t('edit')}</Link><button className="intl-text-button" disabled={busy} onClick={() => { if (window.confirm(t('disableConfirm'))) void action(async () => { await api(`/characters/${encodeURIComponent(c.id)}/disable`, { method: 'POST' }); setCharacters(characters.filter(item => item.id !== c.id)); setNotice(t('saved')) }) }}>{t('disableCharacter')}</button></div>) : <p>{t('empty')}</p>}<Link to="/create">{t('createCharacter')} →</Link></section>
    <section className="intl-panel"><button disabled={busy} onClick={() => void action(async () => { const data = await api<unknown>('/account/export', json('POST', {})); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = 'yuoyuo-export.json'; link.click(); URL.revokeObjectURL(url) })}>{t('export')}</button><button className="intl-text-button" disabled={busy} onClick={() => void action(async () => { await api('/auth/logout', json('POST', { refresh_token: useAuthStore.getState().refreshToken })); useAuthStore.getState().clearSession(); navigate('/') })}>{t('signOut')}</button><button className="intl-text-button danger" onClick={() => setDeleting(!deleting)}>{t('deleteAccount')}</button>{deleting && <form onSubmit={e => { e.preventDefault(); void action(async () => { await api('/account/delete', json('POST', { confirm })); useAuthStore.getState().clearSession(); navigate('/') }) }}><p>{t('deleteHint')}</p><input aria-label={t('email')} type="email" value={confirm} onChange={e => setConfirm(e.target.value)} /><button disabled={busy || confirm !== user?.email}>{t('confirmDelete')}</button></form>}</section>
  </div>
}
function CreateCharacter() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const editId = new URLSearchParams(location.search).get('edit')
  const [name, setName] = useState(''), [persona, setPersona] = useState(''), [tagline, setTagline] = useState(''), [opening, setOpening] = useState(''), [visibility, setVisibility] = useState('private')
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [draft, setDraft] = useState<Record<string, unknown>>({})
  useEffect(() => { if (!editId) return; let active = true; setBusy(true); void api<Record<string, any>>(`/characters/${encodeURIComponent(editId)}/draft`).then(result => { if (!active) return; const d = result; setDraft(d); setName(d.display_name?.en || d.display_name?.ja || d.display_name?.ko || ''); setPersona(d.persona || ''); setTagline(d.tagline || ''); setOpening(d.opening || ''); setVisibility(d.visibility || 'private') }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setBusy(false) }); return () => { active = false } }, [editId])
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const language = supportedLocale(i18n.language)
      const result = await api<{ id: string }>(editId ? `/characters/${encodeURIComponent(editId)}` : '/characters', json(editId ? 'PATCH' : 'POST', { ...draft, display_name: { [language]: name }, persona, intro: persona.slice(0, 500), tagline, opening: opening || null, visibility, locale: language, creation_mode: 'workshop' }))
      navigate(`/character/${encodeURIComponent(result.id || editId || '')}`)
    } catch (err) { setError((err as Error).message) } finally { setBusy(false) }
  }
  return <section className="intl-panel intl-create"><p className="intl-eyebrow">{t('create')}</p><h1>{t(editId ? 'editCharacter' : 'createTitle')}</h1><p>{t('createBody')}</p><Notice error>{error}</Notice><form onSubmit={submit}><label>{t('characterName')}<input required maxLength={20} value={name} onChange={e => setName(e.target.value)} /></label><label>{t('tagline')}<input required maxLength={60} value={tagline} onChange={e => setTagline(e.target.value)} /></label><label>{t('persona')}<textarea required minLength={20} maxLength={5000} rows={8} placeholder={t('personaHint')} value={persona} onChange={e => setPersona(e.target.value)} /></label><label>{t('opening')}<textarea rows={4} maxLength={2000} placeholder={t('openingHint')} value={opening} onChange={e => setOpening(e.target.value)} /></label><label>{t('visibility')}<select value={visibility} onChange={e => setVisibility(e.target.value)}>{['private', 'public', 'unlisted'].map(v => <option key={v} value={v}>{t(v)}</option>)}</select></label><button className="intl-button" disabled={busy}>{busy ? t('loading') : t(editId ? 'save' : 'createCharacter')}</button></form></section>
}
function ChatList() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Array<{ character_id: string; last_message_text: string }>>([])
  const [names, setNames] = useState<Record<string, string>>({})
  const [error, setError] = useState(''), [loading, setLoading] = useState(true)
  useEffect(() => { let active = true; void Promise.all([api<{ items: typeof items }>('/chat/inbox-summary'), api<{ characters: CharacterDTO[] }>('/characters')]).then(([history, catalog]) => { if (active) { setItems(history.items); setNames(Object.fromEntries(catalog.characters.map(c => [c.id, c.display_name]))) } }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [])
  return <section><h1>{t('chats')}</h1><Notice error>{error}</Notice>{loading ? <p>{t('loading')}</p> : !items.length ? <div className="intl-empty">{t('noChats')}</div> : items.map(item => <Link className="intl-chat-row" to={`/chat/${encodeURIComponent(item.character_id)}`} key={item.character_id}><strong>{names[item.character_id] || item.character_id}</strong><p>{item.last_message_text}</p></Link>)}</section>
}
function Legal() {
  const { type = 'terms' } = useParams()
  const { t } = useTranslation()
  const key = ['terms', 'privacy', 'contentPolicy', 'refunds', 'contact'].includes(type) ? type : 'terms'
  return <article className="intl-panel intl-legal"><h1>{t(key)}</h1><small>{t('legalIntro')}</small><p>{t(`${key}Body`)}</p><p><a href="mailto:support@yuoyuo.app">support@yuoyuo.app</a></p>{key === 'contact' && <p>{t('reportHint')}</p>}</article>
}
