import { useEffect, useState } from 'react'
import {
  bindMask,
  createMask,
  deleteMask,
  getMasks,
  unbindMask,
  updateMask,
  type UserMask,
} from '../services/api'
import { useToastStore } from '../stores/toastStore'
import { BottomSheet } from './ui/BottomSheet'

interface MaskSheetProps {
  open: boolean
  onClose: () => void
  characterId: string
  characterName: string
}

type EditorState = {
  id: string | null
  name: string
  gender: UserMask['gender']
  bio: string
  bind: boolean
}

const EMPTY_EDITOR: EditorState = { id: null, name: '', gender: 'unspecified', bio: '', bind: true }

function MaskIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3.5 7.5c2.7-1.6 5.5-2.2 8.5-2.2s5.8.6 8.5 2.2c-.2 5.9-3.3 10.2-8.5 11.2C6.8 17.7 3.7 13.4 3.5 7.5Z" />
      <path d="M7 10.7c1.1-.7 2.2-.7 3.3 0M13.7 10.7c1.1-.7 2.2-.7 3.3 0M9.7 15c1.5.7 3.1.7 4.6 0" />
    </svg>
  )
}

export function MaskDeleteDialog({
  mask,
  busy,
  onCancel,
  onConfirm,
}: {
  mask: Pick<UserMask, 'id' | 'name'>
  busy: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-5" role="dialog" aria-modal="true" aria-labelledby="delete-mask-title">
      <button type="button" aria-label="取消删除" onClick={onCancel} className="absolute inset-0 bg-black/58 backdrop-blur-[2px]" />
      <div className="relative w-full max-w-[340px] rounded-[8px] border border-white/12 bg-[#2B2024] p-5 text-center text-white shadow-[0_24px_80px_rgba(20,9,13,0.56)]">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-[8px] bg-[#FF6E8A]/12 text-[#FF9DB0]">
          <MaskIcon size={27} />
        </span>
        <h3 id="delete-mask-title" className="mt-4 text-[17px] font-semibold">删除这个面具？</h3>
        <p className="mt-2 break-words text-[14px] font-medium text-[#FFF0F3]">“{mask.name}”</p>
        <p className="mt-2 text-[12px] leading-5 text-[#CDBFC0]">
          删除后会从所有已绑定角色中解绑，面具设定将无法恢复。
        </p>
        <div className="mt-5 grid grid-cols-2 gap-2.5">
          <button type="button" disabled={busy} onClick={onCancel} className="h-11 rounded-[8px] border border-white/10 bg-white/7 text-[14px] font-medium text-[#E6D7D5] disabled:opacity-40">
            取消
          </button>
          <button type="button" disabled={busy} onClick={onConfirm} className="h-11 rounded-[8px] bg-[#E95772] text-[14px] font-semibold text-white shadow-[0_8px_22px_rgba(233,87,114,0.28)] active:scale-[0.98] disabled:opacity-40">
            {busy ? '删除中…' : '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function MaskSheet({ open, onClose, characterId, characterName }: MaskSheetProps) {
  const [items, setItems] = useState<UserMask[]>([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<UserMask | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setItems((await getMasks()).items)
    } catch {
      useToastStore.getState().show('面具加载失败，请稍后重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    setEditor(null)
    setDeleteTarget(null)
    void load()
  }, [open])

  const save = async () => {
    if (!editor || !editor.name.trim() || !editor.bio.trim()) return
    setBusyId(editor.id ?? 'new')
    const payload = {
      name: editor.name.trim(),
      gender: editor.gender,
      bio: editor.bio.trim(),
    }
    try {
      const saved = editor.id
        ? (await updateMask(editor.id, payload)).item
        : (await createMask(payload)).item
      const wasBoundHere = items
        .find((item) => item.id === editor.id)
        ?.bound_character_ids.includes(characterId) ?? false
      if (editor.bind && !wasBoundHere) await bindMask(saved.id, characterId)
      if (!editor.bind && wasBoundHere) await unbindMask(saved.id, characterId)
      useToastStore.getState().show(editor.id ? '面具已更新' : '面具已创建', 'success')
      setEditor(null)
      await load()
    } catch {
      useToastStore.getState().show('保存失败，请稍后重试', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const toggleBinding = async (mask: UserMask) => {
    setBusyId(mask.id)
    try {
      if (mask.bound_character_ids.includes(characterId)) await unbindMask(mask.id, characterId)
      else await bindMask(mask.id, characterId)
      await load()
    } catch {
      useToastStore.getState().show('绑定状态更新失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const remove = async () => {
    if (!deleteTarget) return
    const mask = deleteTarget
    setBusyId(mask.id)
    try {
      await deleteMask(mask.id)
      setItems((current) => current.filter((item) => item.id !== mask.id))
      setDeleteTarget(null)
      useToastStore.getState().show('面具已删除', 'success')
    } catch {
      useToastStore.getState().show('删除失败，请稍后重试', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <BottomSheet
        open={open}
        onClose={onClose}
        sheetClassName="overflow-hidden bg-[linear-gradient(180deg,#6A4652_0%,#33262B_30%,#211A1D_100%)] shadow-[0_-18px_60px_rgba(31,18,22,0.42)]"
        handleClassName="bg-white/28"
        contentClassName="px-4 pb-4 sm:px-5"
      >
      <div className="mx-auto flex h-[min(86dvh,760px)] w-full max-w-[520px] flex-col text-white">
        <header className="flex shrink-0 items-center gap-3 pb-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[8px] bg-[#FFB7C5]/18 text-[#FFD2DC] shadow-[0_6px_20px_rgba(31,18,22,0.2)]">
            <MaskIcon />
          </span>
          <span className="min-w-0 flex-1">
            <h2 className="text-[20px] font-semibold tracking-[0]">我的面具</h2>
            <p className="mt-0.5 text-[12px] text-[#E6D7D5]">让{characterName}以你选择的身份认识你</p>
          </span>
          {!editor && (
            <button type="button" onClick={() => setEditor({ ...EMPTY_EDITOR })} className="h-9 shrink-0 rounded-[8px] bg-[#FFB7C5]/18 px-3 text-[13px] font-semibold text-[#FFE7EC] active:scale-[0.98]">
              新建面具
            </button>
          )}
        </header>

        {editor ? (
          <div className="min-h-0 flex-1 overflow-y-auto pb-3">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-[17px] font-semibold">{editor.id ? '编辑面具' : '新建面具'}</h3>
              <button type="button" onClick={() => setEditor(null)} className="text-[13px] text-[#E6D7D5]">返回列表</button>
            </div>
            <label className="mb-2 block text-[13px] font-medium text-[#FFF0F3]">昵称</label>
            <input value={editor.name} maxLength={80} onChange={(e) => setEditor({ ...editor, name: e.target.value })} placeholder="角色对你的称呼" className="mb-4 h-12 w-full rounded-[8px] border border-white/10 bg-white/8 px-3.5 text-[16px] text-white outline-none placeholder:text-[#AFA1A2] focus:border-[#FF94AC]" />

            <span className="mb-2 block text-[13px] font-medium text-[#FFF0F3]">性别</span>
            <div className="mb-4 grid grid-cols-3 gap-2">
              {([['male', '男'], ['female', '女'], ['unspecified', '不设定']] as const).map(([value, label]) => (
                <button key={value} type="button" onClick={() => setEditor({ ...editor, gender: value })} className={`h-11 rounded-[8px] border text-[14px] ${editor.gender === value ? 'border-[#FF94AC] bg-[#FF94AC]/16 text-white shadow-[inset_0_0_0_1px_rgba(255,148,172,.45)]' : 'border-white/10 bg-white/7 text-[#D2C3C1]'}`}>{label}</button>
              ))}
            </div>

            <div className="mb-2 flex items-center justify-between">
              <label className="text-[13px] font-medium text-[#FFF0F3]">身份简介</label>
              <span className="text-[11px] tabular-nums text-[#AFA1A2]">{editor.bio.length}/2000</span>
            </div>
            <textarea value={editor.bio} maxLength={2000} onChange={(e) => setEditor({ ...editor, bio: e.target.value })} placeholder="你的性格、经历、喜好，以及希望角色如何认识你" className="h-40 w-full resize-none rounded-[8px] border border-white/10 bg-white/8 p-3.5 text-[16px] leading-6 text-white outline-none placeholder:text-[#AFA1A2] focus:border-[#FF94AC]" />

            <button type="button" role="switch" aria-checked={editor.bind} onClick={() => setEditor({ ...editor, bind: !editor.bind })} className="mt-4 flex w-full items-center gap-3 rounded-[8px] border border-white/8 bg-white/7 px-3.5 py-3 text-left">
              <span className="min-w-0 flex-1">
                <span className="block text-[14px] font-medium">绑定给{characterName}</span>
                <span className="mt-1 block text-[11px] text-[#CDBFC0]">开启后，角色会把你当作这个身份</span>
              </span>
              <span className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${editor.bind ? 'bg-[#FF94AC]' : 'bg-white/14'}`}><span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-transform ${editor.bind ? 'translate-x-6' : 'translate-x-1'}`} /></span>
            </button>
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto pb-3">
            {loading && items.length === 0 && <p className="py-16 text-center text-[13px] text-[#D2C3C1]">正在加载面具…</p>}
            {!loading && items.length === 0 && (
              <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center">
                <span className="mb-4 text-[#D8B7BE]"><MaskIcon size={54} /></span>
                <p className="text-[15px] font-medium">还没有面具</p>
                <p className="mt-1 text-[12px] text-[#CDBFC0]">创建一个身份，开始不同的相遇</p>
              </div>
            )}
            <div className="space-y-2.5">
              {items.map((mask) => {
                const boundHere = mask.bound_character_ids.includes(characterId)
                return (
                  <article key={mask.id} className={`rounded-[8px] border p-3.5 ${boundHere ? 'border-[#FF94AC] bg-[#FF94AC]/12 shadow-[inset_0_0_0_1px_rgba(255,148,172,.35)]' : 'border-white/9 bg-white/7'}`}>
                    <div className="flex items-start gap-3">
                      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[8px] ${boundHere ? 'bg-[#FF94AC]/22 text-[#FFD2DC]' : 'bg-white/9 text-[#D2C3C1]'}`}><MaskIcon size={22} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <strong className="truncate text-[15px] font-semibold">{mask.name}</strong>
                          <span className="text-[11px] text-[#D2C3C1]">{mask.gender === 'male' ? '男' : mask.gender === 'female' ? '女' : '未设定'}</span>
                          {boundHere && <span className="rounded-[5px] bg-[#FF94AC]/22 px-2 py-1 text-[10px] font-semibold text-[#FFE7EC]">当前绑定</span>}
                        </span>
                        <p className="mt-1 line-clamp-2 text-[12px] leading-5 text-[#D2C3C1]">{mask.bio}</p>
                      </span>
                    </div>
                    <div className="mt-3 flex items-center justify-end gap-2 border-t border-white/8 pt-2.5">
                      <button type="button" disabled={busyId === mask.id} onClick={() => void toggleBinding(mask)} className={`h-8 rounded-[7px] px-3 text-[12px] font-medium ${boundHere ? 'bg-white/9 text-[#E6D7D5]' : 'bg-[#FFB7C5]/18 text-[#FFE7EC]'}`}>{boundHere ? '解绑' : `绑定给${characterName}`}</button>
                      <button type="button" aria-label="编辑面具" onClick={() => setEditor({ id: mask.id, name: mask.name, gender: mask.gender, bio: mask.bio, bind: boundHere })} className="flex h-8 w-8 items-center justify-center rounded-[7px] bg-white/9 text-[#E6D7D5]"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></svg></button>
                      <button type="button" aria-label="删除面具" onClick={() => setDeleteTarget(mask)} className="flex h-8 w-8 items-center justify-center rounded-[7px] bg-[#FF6E8A]/10 text-[#FF9DB0]"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5"/></svg></button>
                    </div>
                  </article>
                )
              })}
            </div>
          </div>
        )}

        {editor && (
          <div className="shrink-0 border-t border-white/10 bg-[#211A1D]/92 pt-3">
            <button type="button" disabled={!editor.name.trim() || !editor.bio.trim() || busyId !== null} onClick={() => void save()} className="h-12 w-full rounded-[8px] bg-[linear-gradient(100deg,#F1D8C9_0%,#FFB7C5_34%,#FF94AC_67%,#FF6E8A_100%)] text-[15px] font-semibold text-white shadow-[0_8px_26px_rgba(232,85,119,0.3)] active:scale-[0.99] disabled:opacity-40">{busyId ? '保存中…' : '保存'}</button>
          </div>
        )}
      </div>

      </BottomSheet>

      {open && deleteTarget && (
        <MaskDeleteDialog
          mask={deleteTarget}
          busy={busyId === deleteTarget.id}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void remove()}
        />
      )}
    </>
  )
}
