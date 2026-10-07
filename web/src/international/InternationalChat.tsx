import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../stores/authStore'
import { type CharacterProfileDTO } from '../services/api'
import { api, json } from './api'

interface Message { id: string; role: string; content: string; kind?: string; turn_id?: string }
interface History { items: Message[]; next_cursor: string | null }
interface Frame { type: string; character_id?: string; turn_id?: string; delta?: string; content?: string; kind?: string; sequence_id?: number; code?: string }

export function InternationalChat() {
  const { characterId = '' } = useParams()
  const { t } = useTranslation()
  const token = useAuthStore(s => s.accessToken)
  const [messages, setMessages] = useState<Message[]>([]), [name, setName] = useState('')
  const [draft, setDraft] = useState(''), [error, setError] = useState('')
  const [connected, setConnected] = useState(false), [busy, setBusy] = useState(false), [loading, setLoading] = useState(true)
  const [cursor, setCursor] = useState<string | null>(null)
  const socket = useRef<WebSocket | null>(null), activeTurn = useRef<string | null>(null)
  const scroll = useRef<HTMLDivElement | null>(null), watchdog = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    let disposed = false
    let retry: ReturnType<typeof setTimeout> | undefined
    let retryCount = 0
    setMessages([]); setError(''); setLoading(true); setBusy(false)
    const finish = () => { activeTurn.current = null; setBusy(false); if (watchdog.current) clearTimeout(watchdog.current) }
    async function loadHistory(opening = false) {
      if (opening) await api(`/chat/opening?character_id=${encodeURIComponent(characterId)}`, json('POST', {}))
      const data = await api<History>(`/chat/history?character_id=${encodeURIComponent(characterId)}&limit=50`)
      if (disposed) return
      setMessages([...data.items].reverse()); setCursor(data.next_cursor)
    }
    function connect() {
      if (disposed || !useAuthStore.getState().accessToken) return
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${scheme}://${location.host}/api/chat/ws?token=${encodeURIComponent(useAuthStore.getState().accessToken!)}`)
      socket.current = ws
      ws.onopen = () => { if (disposed) { ws.close(); return }; setConnected(true); retryCount = 0 }
      ws.onmessage = event => {
        let frame: Frame
        try { frame = JSON.parse(event.data) as Frame } catch { setError(t('error')); return }
        if (frame.character_id && frame.character_id !== characterId) return
        if (frame.turn_id && activeTurn.current && frame.turn_id !== activeTurn.current) return
        const turnId = frame.turn_id ?? activeTurn.current ?? ''
        if (frame.type === 'turn_start') {
          activeTurn.current = turnId
          setMessages(current => [...current, { id: turnId, turn_id: turnId, role: 'assistant', content: '' }])
        } else if (frame.type === 'text_delta') {
          setMessages(current => current.map(message => message.id === turnId ? { ...message, content: message.content + (frame.delta ?? '') } : message))
        } else if (frame.type === 'message_bubble') {
          const id = frame.sequence_id === 0 ? turnId : `${turnId}-${frame.sequence_id}`
          const bubble = { id, turn_id: turnId, role: 'assistant', content: frame.content ?? '', kind: frame.kind }
          setMessages(current => current.some(message => message.id === id) ? current.map(message => message.id === id ? bubble : message) : [...current, bubble])
        } else if (['turn_end', 'interrupted'].includes(frame.type)) {
          void loadHistory().catch(() => { if (!disposed) setError(t('error')) }).finally(() => { if (!disposed) finish() })
        } else if (frame.type === 'error' || frame.type === 'insufficient_credits' || frame.type === 'model_forbidden') {
          finish(); setError(t(frame.type === 'insufficient_credits' || frame.code === 'INSUFFICIENT_CREDITS' ? 'insufficient' : 'error'))
          void loadHistory().catch(() => {})
        }
      }
      ws.onclose = () => {
        if (disposed) return
        setConnected(false); finish()
        if (retryCount++ >= 5) { setError(t('offline')); return }
        retry = setTimeout(() => { void api('/auth/me').then(() => { if (!disposed) { void loadHistory().catch(() => {}); connect() } }).catch(() => { if (!disposed) setError(t('sessionExpired')) }) }, Math.min(1000 * 2 ** retryCount, 15000))
      }
      ws.onerror = () => { if (!disposed) setConnected(false) }
    }
    void (async () => {
      try {
        const profile = await api<CharacterProfileDTO>(`/characters/${encodeURIComponent(characterId)}/profile`)
        if (disposed) return
        setName(profile.display_name)
        await loadHistory(true)
        if (!disposed) connect()
      } catch (e) { if (!disposed) setError((e as Error).message) }
      finally { if (!disposed) setLoading(false) }
    })()
    return () => { disposed = true; if (retry) clearTimeout(retry); if (watchdog.current) clearTimeout(watchdog.current); socket.current?.close(); socket.current = null }
  }, [characterId, token, t])
  useEffect(() => { scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: 'smooth' }) }, [messages])
  function send(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim() || busy || socket.current?.readyState !== WebSocket.OPEN) return
    const turn = crypto.randomUUID(), text = draft.trim()
    activeTurn.current = turn; setBusy(true); setError(''); setDraft('')
    setMessages(current => [...current, { id: `user-${turn}`, role: 'user', content: text, turn_id: turn }])
    socket.current.send(JSON.stringify({ type: 'chat', text, character_id: characterId, turn_id: turn, voice_enabled: false, model: 'gemini-3.1', channel: 'chat' }))
    watchdog.current = setTimeout(() => { if (activeTurn.current === turn) { socket.current?.send(JSON.stringify({ type: 'interrupt', turn_id: turn })); activeTurn.current = null; setBusy(false); setError(t('error')) } }, 90000)
  }
  return <section className="intl-chat"><div className="intl-chat-title"><div><Link to="/chats">← {t('chats')}</Link><h1>{name || t('conversation')}</h1><small>{t(connected ? 'connected' : loading ? 'loading' : 'offline')}</small></div><Link to="/account">{t('preferences')}</Link></div>{error && <p className="intl-notice intl-error" role="alert">{error}</p>}
    {cursor && <button disabled={loading} onClick={async () => { setLoading(true); try { const history = await api<History>(`/chat/history?character_id=${encodeURIComponent(characterId)}&cursor=${encodeURIComponent(cursor)}&limit=50`); setMessages(current => [...history.items].reverse().concat(current)); setCursor(history.next_cursor) } catch (e) { setError((e as Error).message) } finally { setLoading(false) } }}>{t('history')}</button>}
    <div className="intl-messages" ref={scroll} role="log" aria-live="polite">{messages.filter(message => message.content).map(message => <div key={message.id} className={`intl-message ${message.role === 'user' ? 'user' : ''} ${message.kind === 'action' ? 'action' : ''}`}>{message.content}</div>)}{busy && <small>{t('thinking')}</small>}</div>
    <form onSubmit={send}><textarea aria-label={t('message')} placeholder={t('message')} value={draft} onChange={e => setDraft(e.target.value)} maxLength={8000} rows={2} /><button className="intl-button" disabled={!connected || busy || !draft.trim()}>{t('send')}</button>{busy && <button type="button" onClick={() => socket.current?.send(JSON.stringify({ type: 'interrupt', turn_id: activeTurn.current }))}>{t('stop')}</button>}</form><small>{t('aiNotice')}</small>
  </section>
}
