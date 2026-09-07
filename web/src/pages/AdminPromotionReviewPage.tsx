import { useEffect, useState } from 'react'
import { ApiError, adminApprovePromotion, adminListPendingPromotions, adminNeedsInfoPromotion, adminRejectPromotion, type PromotionSubmission } from '../services/api'
import { useToastStore } from '../stores/toastStore'

const ADMIN_KEY_STORAGE = 'heart_admin_key'
const platformLabel = { douyin: '抖音', xiaohongshu: '小红书' } as const
const taskLabel = { ambassador: '每日安利', creator: '原创作品', likes: '点赞核验' } as const

export function AdminPromotionReviewPage() {
  const showToast = useToastStore((s) => s.show)
  const [key, setKey] = useState(() => sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? '')
  const [authed, setAuthed] = useState(false)
  const [items, setItems] = useState<PromotionSubmission[]>([])
  const [loading, setLoading] = useState(false)
  const [reasonId, setReasonId] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  const load = async (adminKey: string) => {
    setLoading(true)
    try { const res = await adminListPendingPromotions(adminKey); setItems(res.pending); setAuthed(true); sessionStorage.setItem(ADMIN_KEY_STORAGE, adminKey) }
    catch (err) { showToast(err instanceof ApiError ? err.message : '加载失败', 'error'); setAuthed(false) }
    finally { setLoading(false) }
  }
  useEffect(() => { const saved = sessionStorage.getItem(ADMIN_KEY_STORAGE); if (saved) void load(saved) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const action = async (item: PromotionSubmission, kind: 'approve' | 'reject' | 'needs') => {
    try {
      if (kind === 'approve') { const res = await adminApprovePromotion(item.id, key); showToast(`已通过，发放 ${res.reward_coins} 币`, 'success') }
      if (kind === 'reject') { await adminRejectPromotion(item.id, reason.trim(), key); showToast('已驳回', 'success') }
      if (kind === 'needs') { await adminNeedsInfoPromotion(item.id, reason.trim(), key); showToast('已要求补充材料', 'success') }
      setItems((prev) => prev.filter((x) => x.id !== item.id)); setReasonId(null); setReason('')
    } catch (err) { showToast(err instanceof ApiError ? err.message : '操作失败', 'error') }
  }

  if (!authed) return <div className="flex min-h-full items-center justify-center px-6"><div className="w-full max-w-[360px] rounded-[18px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-6"><h1 className="text-[20px] font-semibold text-[var(--color-ink)]">推广审核台</h1><input type="password" value={key} onChange={(e) => setKey(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && void load(key.trim())} placeholder="管理密钥" className="mt-4 h-[46px] w-full rounded-[10px] border border-[var(--color-divider)] bg-transparent px-3" /><button disabled={!key.trim() || loading} onClick={() => void load(key.trim())} className="mt-4 h-[46px] w-full rounded-[10px] bg-[var(--color-primary-500)] text-white">{loading ? '验证中…' : '进入审核台'}</button></div></div>

  return <div className="min-h-full bg-[var(--color-bg-page)]"><div style={{ height: 'var(--safe-top)' }} /><div className="flex h-[58px] items-center justify-between px-5"><h1 className="text-[18px] font-semibold text-[var(--color-ink)]">推广待审核 · {items.length}</h1><button onClick={() => void load(key)} className="text-[13px] text-[var(--color-primary-600)]">刷新</button></div><div className="space-y-3 px-4 pb-10">{items.length === 0 && <p className="pt-20 text-center text-[14px] text-[var(--color-text-muted)]">暂无待审核内容</p>}{items.map((item) => <article key={item.id} className="rounded-[16px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-[15px] font-semibold text-[var(--color-ink)]">{taskLabel[item.task_type]} · {platformLabel[item.platform]}</p><p className="mt-1 text-[12px] text-[var(--color-text-muted)]">{item.owner_email || item.user_id} · {new Date(item.submitted_at).toLocaleString('zh-CN')}</p></div><span className="text-[12px] text-[var(--color-text-secondary)]">{item.likes_count != null ? `${item.likes_count} 赞` : ''}</span></div>{item.screenshot_url && <img src={item.screenshot_url} alt="提交截图" className="mt-3 max-h-[360px] w-full rounded-[10px] object-contain" />}{item.post_url && <p className="mt-3 break-all text-[12px] text-[var(--color-primary-700)]">{item.post_url}</p>}{item.title && <p className="mt-2 text-[13px] text-[var(--color-text-secondary)]">{item.title}</p>}<div className="mt-4 grid grid-cols-3 gap-2"><button onClick={() => void action(item, 'approve')} className="h-[40px] rounded-[9px] bg-[var(--color-primary-500)] text-[13px] font-semibold text-white">通过</button><button onClick={() => { setReasonId(item.id); setReason('') }} className="h-[40px] rounded-[9px] bg-[var(--color-page-soft)] text-[13px] text-[var(--color-ink)]">驳回/补充</button><button onClick={() => navigator.clipboard.writeText(item.post_url || '')} className="h-[40px] rounded-[9px] bg-[var(--color-page-soft)] text-[13px] text-[var(--color-ink)]">复制链接</button></div>{reasonId === item.id && <div className="mt-3"><textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="填写驳回或补充说明" rows={3} className="w-full rounded-[9px] border border-[var(--color-divider)] bg-transparent p-2 text-[13px]" /><div className="mt-2 flex gap-2"><button disabled={!reason.trim()} onClick={() => void action(item, 'needs')} className="h-[38px] flex-1 rounded-[9px] bg-[var(--color-page-soft)] text-[12px]">要求补充</button><button disabled={!reason.trim()} onClick={() => void action(item, 'reject')} className="h-[38px] flex-1 rounded-[9px] bg-[var(--color-error)] text-[12px] text-white">确认驳回</button></div></div>}</article>)}</div></div>
}
