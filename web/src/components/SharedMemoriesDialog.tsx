import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Dialog } from './ui/Dialog'
import { getSharedBond, correctSharedMemory, type SharedBondDTO, type SharedMemoryDTO } from '../services/api'

export function SharedMemoriesDialog({ characterId, open, onClose }: { characterId: string; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const [bond, setBond] = useState<SharedBondDTO | null>(null)
  const [editing, setEditing] = useState<SharedMemoryDTO | null>(null)
  const [content, setContent] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    let active = true
    setBond(null); setEditing(null); setError('')
    getSharedBond(characterId).then(value => { if (active) setBond(value) })
      .catch(() => { if (active) setError(t('error')) })
    return () => { active = false }
  }, [open, characterId, t])
  async function save() {
    if (!editing || saving) return
    setSaving(true); setError('')
    try {
      await correctSharedMemory(characterId, editing, content, confirmed)
      setBond(await getSharedBond(characterId)); setEditing(null)
    } catch { setError(t('memorySaveError')) }
    finally { setSaving(false) }
  }
  return <Dialog open={open} onClose={onClose} title={t('sharedMemories')} actions={<button className="w-full py-2" onClick={onClose}>{t('back')}</button>}>
    <div className="max-h-[60vh] overflow-y-auto text-left space-y-3">
      {error && <p role="alert">{error}</p>}
      {!bond && !error && <p>{t('loading')}</p>}
      {bond && <>
        <p>{t('sharedMessageCount', { count: bond.message_count })}</p>
        <p>{t('sharedEmotion')}: {t(`memoryEmotion_${bond.emotion}`)}</p>
        <p>{t('sharedIntimacy')}: {Math.round(bond.intimacy * 100)}%</p>
        <p className="text-xs">{t('sharedMemoryHint')}</p>
        {!bond.memories.length && <p>{t('empty')}</p>}
        {bond.memories.map(memory => <div key={`${memory.tier}-${memory.id}`} className="rounded-xl border border-[var(--color-border-glass)] p-3 space-y-2">
          <p className="text-xs">{t(memory.tier === 'L4' ? 'identityMemory' : 'everydayMemory')} · {new Date(memory.updated_at).toLocaleDateString()}</p>
          {editing?.id === memory.id && editing.tier === memory.tier ? <>
            <textarea aria-label={t('editMemory')} className="w-full min-h-24 bg-transparent text-[16px]" maxLength={2000} value={content} onChange={e => setContent(e.target.value)} />
            {memory.tier === 'L4' && <label className="flex gap-2"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />{t('confirmIdentityCorrection')}</label>}
            <div className="flex gap-4"><button disabled={saving || !content.trim() || (memory.tier === 'L4' && !confirmed)} onClick={() => void save()}>{saving ? t('loading') : t('save')}</button><button disabled={saving} onClick={() => setEditing(null)}>{t('cancel')}</button></div>
          </> : <><p className="whitespace-pre-wrap break-words">{memory.content}</p><button className="text-[var(--color-primary)]" onClick={() => { setEditing(memory); setContent(memory.content); setConfirmed(false) }}>{t('editMemory')}</button></>}
        </div>)}
      </>}
    </div>
  </Dialog>
}
