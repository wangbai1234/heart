import { useEffect, useState } from 'react'
import {
  ApiError,
  adminApprovePromotion,
  adminGetPromotionImage,
  adminListPendingPromotions,
  adminNeedsInfoPromotion,
  adminRejectPromotion,
  type PromotionMembershipReward,
  type PromotionSubmission,
} from '../services/api'
import { useToastStore } from '../stores/toastStore'

const ADMIN_KEY_STORAGE = 'heart_admin_key'
const platformLabel = { douyin: '抖音', xiaohongshu: '小红书' } as const
const taskLabel = { ambassador: '每日安利', creator: '原创作品', likes: '点赞核验' } as const

type MembershipPreview = {
  threshold: 300 | 1000
  label: string
  days: number
  state: 'not_reached' | 'grant_now' | 'granted'
}

function membershipPreview(item: PromotionSubmission): MembershipPreview[] {
  const likes = item.likes_count ?? 0
  const granted300 = item.source_milestone_300_granted ?? item.milestone_300_granted
  const granted1000 = item.source_milestone_1000_granted ?? item.milestone_1000_granted
  return [
    { threshold: 300, label: '29 元档 VIP', days: 30, state: granted300 ? 'granted' : likes >= 300 ? 'grant_now' : 'not_reached' },
    { threshold: 1000, label: '69 元档 VIP', days: 30, state: granted1000 ? 'granted' : likes >= 1000 ? 'grant_now' : 'not_reached' },
  ]
}

function approvalLabel(item: PromotionSubmission): string {
  if (item.task_type !== 'likes') return '通过并发放奖励'
  const rewards = membershipPreview(item).filter((reward) => reward.state === 'grant_now')
  if (rewards.length === 2) return '通过并累计发放 29 + 69 元档 VIP'
  if (rewards[0]) return `通过并发放 ${rewards[0].label}`
  return `通过（${(item.likes_count ?? 0) < 300 ? '未达 VIP 门槛' : '本次无新增权益'}）`
}

function approvalToast(rewardCoins: number, memberships: PromotionMembershipReward[]): string {
  const rewards = [
    rewardCoins ? `${rewardCoins} 币` : '',
    ...memberships.map((reward) => `${reward.label} ${reward.days} 天`),
  ].filter(Boolean)
  return rewards.length ? `已通过，已发放 ${rewards.join('、')}` : '已通过，本次没有新增权益'
}

export function AdminPromotionReviewPage() {
  const showToast = useToastStore((state) => state.show)
  const [key, setKey] = useState(() => sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? '')
  const [authed, setAuthed] = useState(false)
  const [items, setItems] = useState<PromotionSubmission[]>([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [reasonId, setReasonId] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [approveTarget, setApproveTarget] = useState<PromotionSubmission | null>(null)

  const load = async (adminKey: string) => {
    setLoading(true)
    try {
      const result = await adminListPendingPromotions(adminKey)
      setItems(result.pending)
      setAuthed(true)
      sessionStorage.setItem(ADMIN_KEY_STORAGE, adminKey)
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : '加载失败', 'error')
      setAuthed(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const saved = sessionStorage.getItem(ADMIN_KEY_STORAGE)
    if (saved) void load(saved)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const action = async (item: PromotionSubmission, kind: 'approve' | 'reject' | 'needs') => {
    setBusyId(item.id)
    try {
      if (kind === 'approve') {
        const result = await adminApprovePromotion(item.id, key)
        showToast(approvalToast(result.reward_coins, result.granted_memberships ?? []), 'success')
      }
      if (kind === 'reject') {
        await adminRejectPromotion(item.id, reason.trim(), key)
        showToast('已驳回', 'success')
      }
      if (kind === 'needs') {
        await adminNeedsInfoPromotion(item.id, reason.trim(), key)
        showToast('已要求补充材料', 'success')
      }
      setItems((current) => current.filter((entry) => entry.id !== item.id))
      setReasonId(null)
      setApproveTarget(null)
      setReason('')
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : '操作失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const copyLink = async (postUrl: string | null) => {
    if (!postUrl) return
    try {
      await navigator.clipboard.writeText(postUrl)
      showToast('作品链接已复制', 'success')
    } catch {
      showToast('复制失败，请手动复制链接', 'error')
    }
  }

  if (!authed) {
    return (
      <div className="flex min-h-full items-center justify-center bg-[var(--color-bg-page)] px-6">
        <div className="w-full max-w-[360px] rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-6 shadow-[var(--shadow-soft)]">
          <p className="text-[11px] font-semibold text-[var(--color-primary-600)]">YUOYUO · INTERNAL</p>
          <h1 className="mt-1 text-[20px] font-semibold text-[var(--color-ink)]">推广审核台</h1>
          <input type="password" value={key} onChange={(event) => setKey(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && void load(key.trim())} placeholder="管理密钥" className="mt-5 h-[46px] w-full rounded-[8px] border border-[var(--color-divider)] bg-transparent px-3 text-[var(--color-ink)] outline-none focus:border-[var(--color-primary-400)]" />
          <button disabled={!key.trim() || loading} onClick={() => void load(key.trim())} className="mt-4 h-[46px] w-full rounded-[8px] bg-[var(--color-primary-500)] text-white disabled:opacity-50">
            {loading ? '验证中…' : '进入审核台'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[var(--color-bg-page)]">
      <div style={{ height: 'var(--safe-top)' }} />
      <header className="sticky top-0 z-20 border-b border-[var(--color-divider)] bg-[var(--color-bg-page)]/95 backdrop-blur-xl">
        <div className="mx-auto flex h-[58px] max-w-[920px] items-center justify-between px-4 sm:px-6">
          <div>
            <p className="text-[10px] font-semibold text-[var(--color-primary-600)]">安利与创作福利</p>
            <h1 className="text-[18px] font-semibold text-[var(--color-ink)]">推广待审核 · {items.length}</h1>
          </div>
          <button onClick={() => void load(key)} disabled={loading} className="h-[36px] rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-4 text-[13px] text-[var(--color-ink)] disabled:opacity-50">
            {loading ? '刷新中…' : '刷新'}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-[920px] space-y-4 px-4 py-5 pb-10 sm:px-6">
        {items.length === 0 && <p className="pt-20 text-center text-[14px] text-[var(--color-text-muted)]">暂无待审核内容</p>}
        {items.map((item) => (
          <PromotionReviewCard
            key={item.id}
            item={item}
            adminKey={key}
            busy={busyId === item.id}
            reasonOpen={reasonId === item.id}
            reason={reason}
            onReasonChange={setReason}
            onOpenReason={() => { setReasonId(item.id); setReason('') }}
            onApprove={() => item.task_type === 'likes' ? setApproveTarget(item) : void action(item, 'approve')}
            onReject={() => void action(item, 'reject')}
            onNeedsInfo={() => void action(item, 'needs')}
            onCopyLink={() => void copyLink(item.post_url)}
          />
        ))}
      </main>

      <PromotionApprovalDialog
        item={approveTarget}
        busy={busyId !== null}
        onClose={() => { if (!busyId) setApproveTarget(null) }}
        onConfirm={() => { if (approveTarget) void action(approveTarget, 'approve') }}
      />
    </div>
  )
}

function PromotionApprovalDialog({ item, busy, onClose, onConfirm }: {
  item: PromotionSubmission | null
  busy: boolean
  onClose: () => void
  onConfirm: () => void
}) {
  if (!item) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-5" role="dialog" aria-modal="true" aria-labelledby="promotion-approval-title">
      <button type="button" aria-label="关闭确认框" onClick={onClose} className="absolute inset-0 bg-[var(--color-overlay)]" />
      <div className="relative z-10 w-full max-w-[360px] rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-5 shadow-[var(--shadow-modal)]">
        <h2 id="promotion-approval-title" className="text-center text-[17px] font-semibold text-[var(--color-ink)]">确认点赞权益发放</h2>
        <p className="mt-4 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">已核验该作品为 <strong className="text-[var(--color-ink)]">{item.likes_count ?? 0} 赞</strong>。</p>
        <p className="mt-2 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">{approvalLabel(item)}。权益按里程碑累计，已发放的档位不会重复发放。</p>
        <div className="mt-5 flex gap-2">
          <button type="button" onClick={onClose} disabled={busy} className="h-[44px] flex-1 rounded-[8px] bg-[var(--color-page-soft)] text-[14px] text-[var(--color-ink)] disabled:opacity-50">取消</button>
          <button type="button" onClick={onConfirm} disabled={busy} className="h-[44px] flex-1 rounded-[8px] bg-[var(--color-primary-500)] text-[14px] font-semibold text-white disabled:opacity-50">{busy ? '发放中…' : '确认通过'}</button>
        </div>
      </div>
    </div>
  )
}

function PromotionReviewCard({ item, adminKey, busy, reasonOpen, reason, onReasonChange, onOpenReason, onApprove, onReject, onNeedsInfo, onCopyLink }: {
  item: PromotionSubmission
  adminKey: string
  busy: boolean
  reasonOpen: boolean
  reason: string
  onReasonChange: (value: string) => void
  onOpenReason: () => void
  onApprove: () => void
  onReject: () => void
  onNeedsInfo: () => void
  onCopyLink: () => void
}) {
  return (
    <article className="rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4 shadow-[var(--shadow-soft)] sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[15px] font-semibold text-[var(--color-ink)]">{taskLabel[item.task_type]} · {platformLabel[item.platform]}</p>
          <p className="mt-1 break-all text-[12px] text-[var(--color-text-muted)]">{item.owner_email || item.user_id} · {new Date(item.submitted_at).toLocaleString('zh-CN')}</p>
        </div>
        {item.likes_count != null && (
          <div className="shrink-0 border-l-2 border-[var(--color-primary-400)] pl-3 text-right">
            <strong className="block text-[22px] leading-none text-[var(--color-ink)]">{item.likes_count}</strong>
            <span className="mt-1 block text-[10px] text-[var(--color-text-muted)]">当前点赞</span>
          </div>
        )}
      </div>

      {item.screenshot_url && <AdminEvidenceImage submissionId={item.id} adminKey={adminKey} />}
      {item.post_url && (
        <div className="mt-3 flex items-start justify-between gap-3 border-y border-[var(--color-divider)] py-3">
          <a href={item.post_url} target="_blank" rel="noreferrer" className="min-w-0 break-all text-[12px] leading-relaxed text-[var(--color-primary-700)]">{item.post_url}</a>
          <button type="button" onClick={onCopyLink} className="shrink-0 text-[12px] font-semibold text-[var(--color-primary-600)]">复制链接</button>
        </div>
      )}
      {item.title && <p className="mt-3 text-[13px] text-[var(--color-text-secondary)]">{item.title}</p>}

      {item.task_type === 'likes' && <MembershipEntitlementPreview item={item} />}

      <button type="button" onClick={onApprove} disabled={busy} className="mt-4 min-h-[46px] w-full rounded-[8px] bg-[var(--color-primary-500)] px-4 py-2 text-[13px] font-semibold leading-snug text-white shadow-[var(--shadow-btn)] disabled:opacity-50">
        {busy ? '处理中…' : approvalLabel(item)}
      </button>
      <button type="button" onClick={onOpenReason} disabled={busy} className="mt-2 h-[40px] w-full rounded-[8px] bg-[var(--color-page-soft)] text-[13px] text-[var(--color-ink)] disabled:opacity-50">驳回或要求补充材料</button>

      {reasonOpen && (
        <div className="mt-3 border-t border-[var(--color-divider)] pt-3">
          <textarea value={reason} onChange={(event) => onReasonChange(event.target.value)} placeholder="填写驳回或补充说明" rows={3} maxLength={500} className="w-full resize-none rounded-[8px] border border-[var(--color-divider)] bg-transparent p-3 text-[13px] text-[var(--color-ink)] outline-none focus:border-[var(--color-primary-400)]" />
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button type="button" disabled={!reason.trim() || busy} onClick={onNeedsInfo} className="h-[40px] rounded-[8px] bg-[var(--color-page-soft)] text-[12px] text-[var(--color-ink)] disabled:opacity-50">要求补充</button>
            <button type="button" disabled={!reason.trim() || busy} onClick={onReject} className="h-[40px] rounded-[8px] bg-[var(--color-error)] text-[12px] text-white disabled:opacity-50">确认驳回</button>
          </div>
        </div>
      )}
    </article>
  )
}

function MembershipEntitlementPreview({ item }: { item: PromotionSubmission }) {
  const rewards = membershipPreview(item)
  const currentRewards = rewards.filter((reward) => reward.state === 'grant_now')
  return (
    <section className="mt-4 border-l-4 border-[var(--color-primary-500)] bg-[var(--color-page-soft)] px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[12px] font-semibold text-[var(--color-ink)]">本次审核权益</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-[var(--color-text-secondary)]">{currentRewards.length ? '审核通过后立即进入用户账户，两档奖励累计发放。' : '当前没有待发放的 VIP 权益。'}</p>
        </div>
        {currentRewards.length > 0 && <span className="shrink-0 text-[11px] font-semibold text-[var(--color-primary-700)]">待发 {currentRewards.length} 档</span>}
      </div>
      <div className="mt-3 divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
        {rewards.map((reward) => (
          <div key={reward.threshold} className="flex items-center justify-between gap-3 py-2.5">
            <div>
              <p className="text-[13px] font-semibold text-[var(--color-ink)]">{reward.threshold} 赞 · {reward.label}</p>
              <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">有效期 {reward.days} 天</p>
            </div>
            <RewardState state={reward.state} />
          </div>
        ))}
      </div>
    </section>
  )
}

function RewardState({ state }: { state: MembershipPreview['state'] }) {
  const content = {
    not_reached: { label: '未达标', className: 'text-[var(--color-text-muted)]' },
    grant_now: { label: '本次发放', className: 'text-[var(--color-primary-700)]' },
    granted: { label: '已发放', className: 'text-[var(--color-success)]' },
  }[state]
  return <span className={`shrink-0 text-[11px] font-semibold ${content.className}`}>{content.label}</span>
}

function AdminEvidenceImage({ submissionId, adminKey }: { submissionId: string; adminKey: string }) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null
    setFailed(false)
    void adminGetPromotionImage(submissionId, adminKey)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      })
      .catch(() => { if (active) setFailed(true) })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [adminKey, submissionId])

  if (failed) return <div className="mt-3 flex min-h-[120px] items-center justify-center rounded-[8px] border border-dashed border-[var(--color-divider)] text-[12px] text-[var(--color-error)]">截图加载失败，请刷新重试</div>
  if (!imageUrl) return <div className="mt-3 flex min-h-[120px] items-center justify-center rounded-[8px] bg-[var(--color-page-soft)] text-[12px] text-[var(--color-text-muted)]">截图加载中…</div>
  return <img src={imageUrl} alt="提交截图" className="mt-3 max-h-[460px] w-full rounded-[8px] bg-[var(--color-page-soft)] object-contain" />
}
