import { useEffect, useState, type ReactNode } from 'react'
import {
  ApiError,
  adminListPendingCharacters,
  adminApproveCharacter,
  adminRejectCharacter,
  type PendingCharacterDTO,
} from '../services/api'
import { useToastStore } from '../stores/toastStore'
import { Dialog } from '../components/ui/Dialog'

/**
 * 角色审核台 at /admin/review.
 *
 * Not a user route — it is gated by the admin key (backend ADMIN_SECRET_KEY),
 * entered once per visit and kept in component state only (never persisted).
 * Lists pending UGC characters and lets the admin approve or reject (with a
 * required reason) each one. Each card taps open to reveal the full authoring
 * payload — persona / 设定 / 简介 / 开场 / 说话风格 / 标签 — so review can be
 * thorough rather than working off a truncated preview.
 */
const ADMIN_KEY_STORAGE = 'heart_admin_key'

const GREETING_STYLE_TEXT: Record<string, string> = {
  warm: '温暖',
  cool: '疏离',
  playful: '俏皮',
  reserved: '克制',
  intense: '浓烈',
}

const GENDER_TEXT: Record<string, string> = { female: '女性', male: '男性' }

export function AdminReviewPage() {
  const showToast = useToastStore((s) => s.show)
  // Seed from sessionStorage so a refresh mid-review doesn't force re-entry,
  // but it never touches localStorage (won't outlive the tab).
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? '')
  const [authed, setAuthed] = useState(false)
  const [items, setItems] = useState<PendingCharacterDTO[]>([])
  const [loading, setLoading] = useState(false)
  const [rejectTarget, setRejectTarget] = useState<PendingCharacterDTO | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function loadPending(key: string) {
    setLoading(true)
    try {
      const res = await adminListPendingCharacters(key)
      setItems(res.pending)
      setAuthed(true)
      sessionStorage.setItem(ADMIN_KEY_STORAGE, key)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '加载失败，请稍后再试'
      showToast(msg, 'error')
      if (err instanceof ApiError && (err.status === 403 || err.status === 503)) {
        setAuthed(false)
        sessionStorage.removeItem(ADMIN_KEY_STORAGE)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const saved = sessionStorage.getItem(ADMIN_KEY_STORAGE)
    if (saved) void loadPending(saved)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AdminReviewView
      adminKey={adminKey}
      setAdminKey={setAdminKey}
      authed={authed}
      items={items}
      loading={loading}
      busyId={busyId}
      rejectTarget={rejectTarget}
      setRejectTarget={setRejectTarget}
      onLogin={() => loadPending(adminKey.trim())}
      onReload={() => loadPending(adminKey.trim())}
      onApprove={async (c) => {
        setBusyId(c.id)
        try {
          const r = await adminApproveCharacter(c.id, adminKey.trim())
          showToast(
            r.milestone_plus_granted
              ? `已通过，作者 +${r.coins_granted} 币并解锁进阶版`
              : `已通过，作者 +${r.coins_granted} 币`,
            'success',
          )
          setItems((prev) => prev.filter((x) => x.id !== c.id))
        } catch (err) {
          showToast(err instanceof ApiError ? err.message : '操作失败', 'error')
        } finally {
          setBusyId(null)
        }
      }}
      onReject={async (c, reason) => {
        setBusyId(c.id)
        try {
          await adminRejectCharacter(c.id, reason, adminKey.trim())
          showToast('已驳回', 'success')
          setItems((prev) => prev.filter((x) => x.id !== c.id))
          setRejectTarget(null)
        } catch (err) {
          showToast(err instanceof ApiError ? err.message : '操作失败', 'error')
        } finally {
          setBusyId(null)
        }
      }}
    />
  )
}

interface ViewProps {
  adminKey: string
  setAdminKey: (v: string) => void
  authed: boolean
  items: PendingCharacterDTO[]
  loading: boolean
  busyId: string | null
  rejectTarget: PendingCharacterDTO | null
  setRejectTarget: (c: PendingCharacterDTO | null) => void
  onLogin: () => void
  onReload: () => void
  onApprove: (c: PendingCharacterDTO) => void
  onReject: (c: PendingCharacterDTO, reason: string) => void
}

function AdminReviewView(p: ViewProps) {
  const [reason, setReason] = useState('')

  if (!p.authed) {
    return (
      <div className="w-full min-h-full flex flex-col items-center justify-center px-6 bg-[var(--color-bg-page)]">
        <div className="w-full max-w-[360px] rounded-[20px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-6">
          <h1 className="text-[20px] font-semibold text-[var(--color-ink)]">角色审核台</h1>
          <p className="mt-2 text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
            输入管理密钥进入。密钥仅保存在当前标签页，关闭即失效。
          </p>
          <input
            type="password"
            value={p.adminKey}
            onChange={(e) => p.setAdminKey(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && p.onLogin()}
            placeholder="管理密钥"
            className="mt-4 w-full h-[46px] rounded-[12px] px-4 bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[15px] text-[var(--color-ink)] outline-none focus:border-[var(--color-primary)]"
          />
          <button
            onClick={p.onLogin}
            disabled={!p.adminKey.trim() || p.loading}
            className="mt-4 w-full h-[46px] rounded-[12px] bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[15px] font-semibold disabled:opacity-50"
          >
            {p.loading ? '验证中…' : '进入'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full min-h-full flex flex-col bg-[var(--color-bg-page)]">
      <div style={{ height: 'var(--safe-top)' }} />
      <nav className="flex items-center justify-between px-5 h-[52px] shrink-0">
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">
          待审核 · {p.items.length}
        </span>
        <button
          onClick={p.onReload}
          disabled={p.loading}
          className="h-[34px] px-4 rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[13px] text-[var(--color-ink)] disabled:opacity-50"
        >
          {p.loading ? '刷新中…' : '刷新'}
        </button>
      </nav>

      <div className="flex-1 overflow-y-auto px-4 pb-10 pt-2">
        {p.items.length === 0 ? (
          <p className="text-center text-[14px] text-[var(--color-text-muted)] pt-20">
            {p.loading ? '加载中…' : '没有待审核的角色'}
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {p.items.map((c) => (
              <PendingCard
                key={c.id}
                c={c}
                busy={p.busyId === c.id}
                onApprove={() => p.onApprove(c)}
                onReject={() => { setReason(''); p.setRejectTarget(c) }}
              />
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={p.rejectTarget !== null}
        onClose={() => p.setRejectTarget(null)}
        title={`驳回「${p.rejectTarget?.display_name ?? ''}」`}
      >
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          maxLength={500}
          placeholder="填写驳回原因（用户可见）"
          className="w-full rounded-[12px] p-3 bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[14px] text-[var(--color-ink)] outline-none focus:border-[var(--color-primary)] resize-none"
        />
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => p.setRejectTarget(null)}
            className="flex-1 h-[44px] rounded-full bg-[var(--color-glass-75)] text-[var(--color-ink)] text-[15px] font-medium"
          >
            取消
          </button>
          <button
            onClick={() => p.rejectTarget && p.onReject(p.rejectTarget, reason.trim())}
            disabled={!reason.trim() || p.busyId !== null}
            className="flex-1 h-[44px] rounded-full bg-[var(--color-error)] text-white text-[15px] font-semibold disabled:opacity-50"
          >
            确认驳回
          </button>
        </div>
      </Dialog>
    </div>
  )
}

const VIS_TEXT: Record<string, string> = {
  public: '公开',
  unlisted: '仅链接可见',
  private: '私密',
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) return null
  return (
    <div className="mt-3">
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{label}</p>
      <div className="mt-1 text-[13px] text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap break-words">
        {value}
      </div>
    </div>
  )
}

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((t, i) => (
        <span key={`${t}-${i}`} className="h-[24px] px-2.5 inline-flex items-center rounded-full bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[12px] text-[var(--color-text-secondary)]">
          {t}
        </span>
      ))}
    </div>
  )
}

function PendingCard({
  c,
  busy,
  onApprove,
  onReject,
}: {
  c: PendingCharacterDTO
  busy: boolean
  onApprove: () => void
  onReject: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const meta = [
    c.gender ? GENDER_TEXT[c.gender] ?? c.gender : null,
    c.age_range ? `${c.age_range} 岁` : null,
    c.greeting_style ? `开场风格·${GREETING_STYLE_TEXT[c.greeting_style] ?? c.greeting_style}` : null,
  ].filter(Boolean).join(' · ')

  return (
    <div className="rounded-[18px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] overflow-hidden">
      {c.cover_url && (
        <div className="w-full h-[140px] overflow-hidden">
          <img src={c.cover_url} alt="" className="w-full h-full object-cover" />
        </div>
      )}
      <div className="p-4">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="w-full flex items-center gap-3 text-left"
        >
          <div className="w-[44px] h-[44px] rounded-full overflow-hidden bg-gradient-to-br from-[#FFB7C5] to-[#C8B6FF] shrink-0">
            {c.avatar_url && (
              <img
                src={c.avatar_url}
                alt=""
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[16px] font-semibold text-[var(--color-ink)] truncate">
              {c.display_name}
            </p>
            <p className="text-[12px] text-[var(--color-text-muted)] truncate">
              {VIS_TEXT[c.visibility] ?? c.visibility}
              {c.owner_email ? ` · ${c.owner_email}` : ''}
            </p>
          </div>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="var(--color-text-muted)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
            className={`shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
          >
            <polyline points="6,9 12,15 18,9" />
          </svg>
        </button>

        {!expanded && c.persona && (
          <p className="mt-3 text-[13px] text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap line-clamp-3">
            {c.persona}
          </p>
        )}

        {expanded && (
          <div className="mt-1">
            {meta && <p className="mt-3 text-[12px] text-[var(--color-text-muted)]">{meta}</p>}
            {c.tags.length > 0 && <div className="mt-3"><Chips items={c.tags} /></div>}
            <Field label="人设描述" value={c.persona} />
            <Field label="背景设定" value={c.backstory} />
            <Field label="角色简介" value={c.intro} />
            <Field label="一句话标语" value={c.tagline} />
            <Field label="初遇开场" value={c.opening} />
            {c.speech_samples.length > 0 && <Field label="说话示例" value={c.speech_samples.map((s, i) => <p key={i} className="mt-0.5">「{s}」</p>)} />}
            {c.catchphrases.length > 0 && <Field label="口头禅" value={<Chips items={c.catchphrases} />} />}
            {c.hard_never_user.length > 0 && <Field label="创作者禁则" value={c.hard_never_user.map((s, i) => <p key={i} className="mt-0.5">· {s}</p>)} />}
          </div>
        )}

        <div className="flex gap-3 mt-4">
          <button
            onClick={onReject}
            disabled={busy}
            className="flex-1 h-[42px] rounded-full bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] text-[var(--color-ink)] text-[14px] font-medium disabled:opacity-50"
          >
            驳回
          </button>
          <button
            onClick={onApprove}
            disabled={busy}
            className="flex-1 h-[42px] rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[14px] font-semibold disabled:opacity-50"
          >
            {busy ? '处理中…' : '通过'}
          </button>
        </div>
      </div>
    </div>
  )
}

