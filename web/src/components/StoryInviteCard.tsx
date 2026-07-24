import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getActiveRun, type StoryHookDTO } from '../services/api'

// ── Client-side dismissal cooldown (Wave 3) ──────────────────────────────
// The hook's eligibility is backend-authoritative; the "don't nag me again for
// N hours" cooldown is purely client-side in V1 (no server write). A dismissal
// stores a timestamp; the card stays hidden until cooldown_hours elapse. Worst
// case (localStorage cleared / another device) the card simply reappears —
// harmless, since entering the story is idempotent.

const dismissKey = (characterId: string, scenarioId: string) =>
  `dismissedHook:${characterId}:${scenarioId}`

/** True if this hook was dismissed within its cooldown window on this device. */
export function isHookOnCooldown(characterId: string, hook: StoryHookDTO): boolean {
  try {
    const raw = localStorage.getItem(dismissKey(characterId, hook.scenario_id))
    if (!raw) return false
    const dismissedAt = Number(raw)
    if (!Number.isFinite(dismissedAt)) return false
    const elapsedHours = (Date.now() - dismissedAt) / 3_600_000
    return elapsedHours < hook.cooldown_hours
  } catch {
    return false
  }
}

function markDismissed(characterId: string, scenarioId: string): void {
  try {
    localStorage.setItem(dismissKey(characterId, scenarioId), String(Date.now()))
  } catch {
    /* localStorage unavailable — card reappears next mount, acceptable */
  }
}

interface StoryInviteCardProps {
  characterId: string
  hook: StoryHookDTO
  /** Called after the user dismisses the card so the parent can hide it. */
  onDismiss?: () => void
}

/**
 * 剧情邀约卡 — a character invites the user into a linked scenario. Entering
 * resumes the user's active run for that scenario if one exists, else opens the
 * scenario detail page to start fresh. Config-driven, not AI-generated.
 */
export function StoryInviteCard({ characterId, hook, onDismiss }: StoryInviteCardProps) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  const handleEnter = async () => {
    if (busy) return
    setBusy(true)
    markDismissed(characterId, hook.scenario_id)
    try {
      const { run } = await getActiveRun(hook.scenario_id)
      if (run) {
        navigate(`/story/${run.run_id}`)
        return
      }
    } catch {
      /* fall through to scenario detail entry */
    }
    navigate(`/explore/${hook.scenario_id}`)
  }

  const handleDismiss = () => {
    markDismissed(characterId, hook.scenario_id)
    onDismiss?.()
  }

  return (
    <div className="rounded-[20px] px-4 py-3 bg-[var(--color-glass-75)] backdrop-blur-[16px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-semibold text-[var(--color-ink)]">
          {hook.invite_title || '她想邀你走进一段剧情'}
        </p>
        <button
          onClick={handleDismiss}
          className="shrink-0 -mt-1 -mr-1 w-[28px] h-[28px] flex items-center justify-center text-[var(--color-text-secondary)] active:scale-90 transition-transform"
          aria-label="暂时不看这个邀约"
        >
          ×
        </button>
      </div>
      {hook.invite_copy && (
        <p className="text-[12px] text-[var(--color-text-secondary)] mt-1 leading-relaxed">
          {hook.invite_copy}
        </p>
      )}
      <button
        onClick={handleEnter}
        disabled={busy}
        className="mt-3 h-[34px] px-4 rounded-full bg-[var(--color-primary)] text-white text-[12px] font-medium active:scale-[0.96] transition-transform disabled:opacity-60"
      >
        {busy ? '进入中…' : hook.cta_label || '进入剧情'}
      </button>
    </div>
  )
}
