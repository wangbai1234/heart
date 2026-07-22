import { useMemo, useState } from 'react'
import type { PlayerTemplate, PlayerTemplateField } from '../../services/api'
import { useStoryStore } from '../../stores/storyStore'
import { useToastStore } from '../../stores/toastStore'
import { ApiError } from '../../services/api'

/**
 * The 主控 (player character) card form, shown as a bottom sheet before a run
 * starts. Fields are driven by the scenario's `player_template` (falls back to
 * the global default template the server sends). On submit it creates the run
 * (POST /story/runs, which also generates the opening GM turn) and hands the
 * new run_id back so the detail page can navigate into the player.
 */
interface StartRunSheetProps {
  scenarioId: string
  scenarioTitle: string
  template: PlayerTemplate
  onClose: () => void
  onStarted: (runId: string) => void
}

export function StartRunSheet({
  scenarioId,
  scenarioTitle,
  template,
  onClose,
  onStarted,
}: StartRunSheetProps) {
  const startRun = useStoryStore((s) => s.startRun)
  const showToast = useToastStore((s) => s.show)
  const [values, setValues] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const fields = useMemo(() => template.fields ?? [], [template])

  const setField = (key: string, value: string) =>
    setValues((v) => ({ ...v, [key]: value }))

  const handleSubmit = async () => {
    // Required-field validation before hitting the network.
    const missing = fields.filter((f) => f.required && !values[f.key]?.trim())
    if (missing.length > 0) {
      showToast(`请填写：${missing.map((f) => f.label).join('、')}`, 'error')
      return
    }
    // Drop empty optional values so the GM card stays clean.
    const identity: Record<string, string> = {}
    for (const f of fields) {
      const val = values[f.key]?.trim()
      if (val) identity[f.key] = val
    }

    setSubmitting(true)
    try {
      const run = await startRun(scenarioId, identity)
      onStarted(run.run_id)
    } catch (e) {
      const msg =
        e instanceof ApiError && e.status === 403
          ? '这是成人向剧情，需要先完成年龄验证'
          : '开局失败，请稍后重试'
      showToast(msg, 'error')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex flex-col justify-end">
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
        onClick={submitting ? undefined : onClose}
      />

      {/* Sheet */}
      <div
        className="relative z-10 max-h-[86vh] flex flex-col rounded-t-[24px] bg-[var(--color-surface)] border-t border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]"
        style={{ paddingBottom: 'var(--safe-bottom)' }}
      >
        <div className="flex-shrink-0 pt-3 pb-1 flex justify-center">
          <span className="h-1 w-10 rounded-full bg-[var(--color-border)]" />
        </div>

        <div className="px-5 pt-2 pb-3">
          <h2 className="text-[19px] font-bold text-[var(--color-ink)]">创建你的主控</h2>
          <p className="mt-1 text-[13px] text-[var(--color-text-muted)]">
            进入《{scenarioTitle}》前，先告诉 GM 你在故事里是谁
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-4">
          {fields.map((f) => (
            <FieldInput
              key={f.key}
              field={f}
              value={values[f.key] ?? ''}
              onChange={(v) => setField(f.key, v)}
            />
          ))}
        </div>

        <div className="flex-shrink-0 px-5 pt-3 pb-4 border-t border-[var(--color-border-glass)]">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full h-[52px] rounded-[26px] bg-[var(--color-primary)] text-white text-[16px] font-semibold shadow-[var(--shadow-btn)] active:scale-[0.98] transition-transform disabled:opacity-60"
          >
            {submitting ? '正在生成开场…' : '进入剧情'}
          </button>
        </div>
      </div>
    </div>
  )
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: PlayerTemplateField
  value: string
  onChange: (v: string) => void
}) {
  const label = (
    <label className="block text-[13px] font-semibold text-[var(--color-text-secondary)] mb-1.5">
      {field.label}
      {field.required && <span className="text-[var(--color-primary)]"> *</span>}
    </label>
  )

  const baseInput =
    'w-full rounded-[14px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] px-3.5 text-[15px] text-[var(--color-ink)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)]'

  if (field.type === 'select') {
    return (
      <div>
        {label}
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${baseInput} h-[46px] appearance-none`}
        >
          <option value="">请选择</option>
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    )
  }

  if (field.type === 'textarea') {
    return (
      <div>
        {label}
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          placeholder={`描述你的${field.label}…`}
          className={`${baseInput} py-2.5 resize-none min-h-[76px]`}
        />
      </div>
    )
  }

  return (
    <div>
      {label}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`填写${field.label}`}
        className={`${baseInput} h-[46px]`}
      />
    </div>
  )
}
