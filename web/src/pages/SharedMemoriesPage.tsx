import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSafeBack } from '../hooks/useSafeBack'
import { useAuthStore } from '../stores/authStore'
import { getCharacterProfile, getSharedBond, correctSharedMemory, addSharedMemory, type SharedBondDTO, type SharedMemoryDTO } from '../services/api'
import { stageLabel } from '../utils/relationship'
import { MemoryBookIcon } from '../components/MemoryBookIcon'
import { Button } from '../components/ui/Button'
import { Dialog } from '../components/ui/Dialog'

export function SharedMemoriesPage({ demo = false }: { demo?: boolean }) {
  const { id = '' } = useParams<{ id: string }>()
  const { t, i18n } = useTranslation()
  const back = useSafeBack(`/chat/${encodeURIComponent(id)}`)
  const accountId = useAuthStore(s => s.user?.id)
  const [bond, setBond] = useState<SharedBondDTO | null>(null)
  const [name, setName] = useState('')
  const [avatar, setAvatar] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState<'all' | 'L3' | 'L4'>('all')
  const [editor, setEditor] = useState<{id: string; tier: 'L3' | 'L4'; memory?: SharedMemoryDTO} | null>(null)
  const [content, setContent] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setError(''); setEditor(null); setBond(null); setName(''); setAvatar(null)
    if (demo) {
      setBond(demoBond(i18n.language)); setName('Haru'); return
    }
    Promise.all([getSharedBond(id), getCharacterProfile(id)]).then(([value, profile]) => {
      if (active) { setBond(value); setName(profile.display_name); setAvatar(profile.avatar_url ?? null) }
    }).catch(() => { if (active) setError(t('error')) })
    return () => { active = false }
  }, [id, accountId, demo, i18n.language, reload, t])
  function openEditor(memory?: SharedMemoryDTO) {
    setEditor({id: memory?.id ?? crypto.randomUUID(), tier: memory?.tier ?? 'L3', memory})
    setContent(memory?.content ?? ''); setConfirmed(false); setError(''); setSaved(false)
  }
  async function save() {
    if (!editor || saving || !content.trim() || (editor.tier === 'L4' && !confirmed)) return
    setSaving(true); setError('')
    try {
      if (demo) {
        const note: SharedMemoryDTO = {id: editor.id, tier: editor.tier, content: content.trim(), category:'user_note', updated_at: new Date().toISOString()}
        setBond(value => value && ({...value, memories: editor.memory ? value.memories.map(m => m.id === note.id && m.tier === note.tier ? note : m) : [note, ...value.memories]}))
      } else {
        if (editor.memory) await correctSharedMemory(id, editor.memory, content, confirmed)
        else await addSharedMemory(id, editor.id, editor.tier, content, confirmed)
        setBond(await getSharedBond(id))
      }
      setEditor(null); setSaved(true)
    } catch { setError(t('memorySaveError')) }
    finally { setSaving(false) }
  }
  const date = (value: string) => new Date(value).toLocaleDateString(i18n.language, {month:'short', day:'numeric', year:'numeric'})
  const memories = bond?.memories.filter(m => filter === 'all' || m.tier === filter) ?? []
  const emotionChanges = bond?.emotion_history.filter((e, i, all) => i === all.length - 1 || e.emotion !== all[i+1].emotion).slice(0, 6) ?? []
  return <div className="h-full flex flex-col bg-[var(--color-page-canvas)] text-[var(--color-ink)]">
    <header className="flex items-center gap-3 px-4 pb-3 border-b border-[var(--color-border-glass)] bg-[var(--color-glass-75)] backdrop-blur-xl" style={{paddingTop:'calc(var(--safe-top) + 12px)'}}>
      <button aria-label={t('back')} onClick={back} className="w-11 h-11 flex items-center justify-center text-[24px]">‹</button>
      <MemoryBookIcon /><h1 className="text-[17px] font-medium flex-1">{t('sharedMemories')}</h1>
    </header>
    <main className="flex-1 overflow-y-auto px-5 pb-8">
      {demo && <p className="text-xs text-[var(--color-text-muted)] py-3 border-b border-[var(--color-divider)]">{t('memoryDemo')}</p>}
      {error && !editor && <div role="alert" className="py-5"><p>{error}</p><Button variant="secondary" onClick={() => setReload(n => n+1)}>{t('retry')}</Button></div>}
      {!bond && !error && <p className="py-8" role="status">{t('loading')}</p>}
      {bond && <>
        <section className="relative mt-5 rounded-[24px] p-5 bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)] overflow-hidden">
          <div className="absolute top-0 right-6 w-5 h-9 bg-[var(--color-primary)] opacity-35" style={{clipPath:'polygon(0 0,100% 0,100% 100%,50% 75%,0 100%)'}} />
          <div className="flex items-center gap-3 mb-4">
            {avatar ? <img src={avatar} alt="" className="w-12 h-12 rounded-full object-cover" /> : <span className="w-12 h-12 rounded-full bg-[var(--color-page-canvas)] flex items-center justify-center"><MemoryBookIcon /></span>}
            <div><p className="text-[11px] tracking-widest text-[var(--color-text-muted)]">{t('memoryPrivate')}</p><p className="text-sm mt-1">{name}</p></div>
          </div>
          <h2 className="text-[23px] leading-snug font-semibold pr-4">{t('memoryRemembers', {name})}</h2>
          <p className="text-sm leading-relaxed text-[var(--color-text-secondary)] mt-2">{t(bond.memories.length ? 'memoryGrowing' : 'memoryNewStory')}</p>
          {bond.memories[0] && <blockquote className="mt-5 pl-4 border-l-2 border-[var(--color-primary)] text-sm leading-relaxed whitespace-pre-wrap break-words">{bond.memories[0].content}</blockquote>}
          <div className="grid grid-cols-3 gap-3 mt-6 pt-4 border-t border-[var(--color-divider)]">
            {[[bond.active_days, 'memoryDays'], [bond.user_message_count, 'memoryYourMessages'], [bond.memories.length, 'memoryKept']].map(([value, key]) => <div key={key}><p className="text-[24px] font-medium tabular-nums">{value}</p><p className="text-[11px] leading-snug text-[var(--color-text-muted)]">{t(String(key))}</p></div>)}
          </div>
          <p className="mt-3 text-xs text-[var(--color-text-muted)]">{t('sharedMessageCount',{count:bond.message_count})}{bond.first_message_at ? ` · ${t('memorySince',{date:date(bond.first_message_at)})}` : ''}</p>
        </section>
        <section className="py-6 border-b border-[var(--color-divider)]">
          <h2 className="font-medium">{t('memoryHowChanged')}</h2>
          <div className="flex justify-between gap-4 mt-4 text-sm"><span>{stageLabel(bond.stage)}</span><span>{t('sharedIntimacy')} <strong className="text-[var(--color-primary)]">{Math.round(bond.intimacy*100)}%</strong></span></div>
          <div className="h-1.5 rounded-full bg-[var(--color-divider)] mt-2 overflow-hidden"><div className="h-full bg-[var(--color-primary)] rounded-full" style={{width:`${Math.max(0,Math.min(100,bond.intimacy*100))}%`}} /></div>
          <p className="text-sm mt-4">{t('memoryNow')} · {t(`memoryEmotion_${bond.emotion}`)}</p>
          <p className="text-xs leading-relaxed text-[var(--color-text-muted)] mt-2">{t('memoryFeelingHint')}</p>
          <ol className="mt-5 space-y-3">
            {bond.relationship_history.slice(0, 6).map(e => <li key={e.id} className="flex items-start gap-3 text-sm"><span className="text-[var(--color-primary)]">○</span><div><p>{e.from_stage ? `${stageLabel(e.from_stage)} → ` : ''}{e.to_stage && stageLabel(e.to_stage)}</p><time className="text-xs text-[var(--color-text-muted)]">{date(e.at)}</time></div></li>)}
          </ol>
          <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4">{emotionChanges.map(e => <div key={e.id} className="text-xs"><span>{t(`memoryEmotion_${e.emotion}`)}</span><p className="text-[var(--color-text-muted)] mt-1">{date(e.at)}</p></div>)}</div>
          {!bond.relationship_history.length && !emotionChanges.length && <p className="text-xs text-[var(--color-text-muted)] mt-4">{t('memoryNoHistory')}</p>}
        </section>
        <section className="pt-6">
          <div className="flex justify-between items-center gap-3"><h2 className="font-medium">{t('memoryDetails')}</h2><Button size="sm" variant="secondary" onClick={() => openEditor()}>{t('memoryAdd')}</Button></div>
          <p className="text-xs leading-relaxed text-[var(--color-text-muted)] mt-3">{t('sharedMemoryHint')}</p>
          <div className="flex gap-2 mt-4 mb-4" role="group" aria-label={t('memoryDetails')}>
            {(['all','L4','L3'] as const).map(value => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)} className={`min-h-11 px-3 rounded-full text-xs border ${filter === value ? 'border-[var(--color-primary)] text-[var(--color-primary)] bg-[var(--color-glass-75)]' : 'border-transparent text-[var(--color-text-muted)]'}`}>{t(value === 'all' ? 'memoryAll' : value === 'L4' ? 'identityMemory' : 'everydayMemory')}</button>)}
          </div>
          <p role="status" className="text-xs text-[var(--color-primary)]">{saved ? t(demo ? 'memoryDemoSaved' : 'memorySaved') : ''}</p>
          {!memories.length && <div className="py-8 text-center text-sm text-[var(--color-text-muted)]"><MemoryBookIcon /><p className="mt-3">{t('memoryEmpty')}</p></div>}
          <div className="space-y-3">{memories.map((m,index) => <article key={`${m.tier}-${m.id}`} className="relative p-4 pl-5 bg-[var(--color-glass-75)] rounded-2xl border border-[var(--color-border-glass)]">
            <div className="absolute left-0 inset-y-4 w-0.5 bg-[var(--color-primary)] opacity-30" />
            <div className="flex gap-2 justify-between items-center text-[11px] text-[var(--color-text-muted)]"><span>{String(index+1).padStart(2,'0')} / {t(m.tier === 'L4' ? 'identityMemory' : 'everydayMemory')}</span><time>{date(m.updated_at)}</time></div>
            <p className="text-sm leading-7 mt-3 whitespace-pre-wrap break-words">{m.content}</p>
            <button className="min-h-11 text-xs text-[var(--color-primary)] mt-1" onClick={() => openEditor(m)}>{t('editMemory')}</button>
          </article>)}</div>
        </section>
      </>}
    </main>
    <Dialog open={!!editor} onClose={() => { if (!saving) {setEditor(null); setError('')} }} title={t(editor?.memory ? 'editMemory' : 'memoryAdd')} actions={<div className="flex gap-3"><Button variant="ghost" disabled={saving} onClick={() => {setEditor(null); setError('')}}>{t('cancel')}</Button><Button disabled={!content.trim() || (editor?.tier === 'L4' && !confirmed)} loading={saving} onClick={() => void save()}>{t('save')}</Button></div>}>
      <div className="text-left space-y-4">
        {!editor?.memory && <label className="block text-sm">{t('memoryKind')}<select aria-label={t('memoryKind')} value={editor?.tier ?? 'L3'} disabled={saving} onChange={e => {setEditor(value => value && ({...value, tier: e.target.value as 'L3' | 'L4'})); setConfirmed(false)}} className="block w-full mt-2 p-3 rounded-xl bg-[var(--color-page-canvas)] text-[16px]"><option value="L3">{t('everydayMemory')} (L3)</option><option value="L4">{t('identityMemory')} (L4)</option></select></label>}
        <label className="block text-sm">{t('memoryWrite')}<textarea aria-label={t('memoryWrite')} value={content} disabled={saving} maxLength={2000} onChange={e => setContent(e.target.value)} className="w-full mt-2 min-h-36 p-3 rounded-xl bg-[var(--color-page-canvas)] text-[16px]" /></label>
        <p className="text-xs text-[var(--color-text-muted)]">{t(editor?.tier === 'L4' ? 'memoryPinnedHint' : 'memoryEverydayHint')}</p>
        {editor?.tier === 'L4' && <label className="flex items-start gap-2 text-xs"><input type="checkbox" checked={confirmed} disabled={saving} onChange={e => setConfirmed(e.target.checked)} />{t('confirmIdentityCorrection')}</label>}
        {error && <p role="alert" className="text-sm">{error}</p>}
      </div>
    </Dialog>
  </div>
}

function demoBond(language: string): SharedBondDTO {
  const notes = language.startsWith('ja') ? ['疲れた日は、アドバイスよりも静かに話を聞いてほしい。','大切な面接が10月15日にある。終わったら、ふたりで話したい。','雨の夜に読書をするのが好き。お気に入りは小さな古書店。'] : language.startsWith('ko') ? ['힘든 날에는 조언보다 조용히 이야기를 들어주면 좋겠다.','10월 15일에 중요한 면접이 있다. 끝나면 함께 이야기하고 싶다.','비 오는 저녁에 책 읽는 것을 좋아한다. 작은 헌책방이 가장 편안한 곳이다.'] : ['On difficult days, I prefer quiet listening to advice.','My important interview is on October 15. I want us to talk afterwards.','I love reading on rainy evenings. My favourite place is the little secondhand bookshop.']
  return {message_count:428, user_message_count:196, active_days:24, first_message_at:'2026-09-12T10:00:00Z', stage:'CLOSE_FRIEND', intimacy:0.64, emotion:'warm', memories:notes.map((content,i) => ({id:`demo-${i}`,tier:i===0?'L4':'L3',content,category:'user_note',updated_at:`2026-10-0${8-i}T10:00:00Z`})),relationship_history:[{id:'r2',from_stage:'FRIEND',to_stage:'CLOSE_FRIEND',at:'2026-10-06T10:00:00Z'},{id:'r1',from_stage:'ACQUAINTANCE',to_stage:'FRIEND',at:'2026-09-20T10:00:00Z'}],emotion_history:[{id:'e2',emotion:'warm',at:'2026-10-08T10:00:00Z'},{id:'e1',emotion:'calm',at:'2026-09-12T10:00:00Z'}]}
}
