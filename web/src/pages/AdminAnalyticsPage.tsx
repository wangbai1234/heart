import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { ApiError, adminGetAnalytics, type AdminAnalyticsDTO } from '../services/api'

const ADMIN_KEY_STORAGE = 'heart_admin_key'
const DASHBOARD_THEME = {
  '--color-page-canvas': '#FFFFFF',
  '--color-page-surface': '#FFFFFF',
  '--color-ink': '#272733',
  '--color-text-primary': '#272733',
  '--color-text-secondary': '#626270',
  '--color-text-muted': '#858594',
  '--color-divider': '#E5E7EB',
} as CSSProperties

const CHART_COLORS = {
  dau: '#E85577',
  wau: '#2563EB',
  mau: '#059669',
  grid: '#E5E7EB',
  muted: '#737380',
}

function isoDay(date: Date): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(date)
}

function compact(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value)
}

function pct(value: number | null | undefined): string {
  return value == null ? '未成熟' : `${compact(value, 1)}%`
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="min-w-0 border-l-2 border-[var(--color-primary)] pl-3 py-1">
      <p className="text-[12px] text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-[24px] font-semibold text-[var(--color-ink)] tabular-nums break-words">{value}</p>
      {note && <p className="mt-1 text-[11px] text-[var(--color-text-secondary)]">{note}</p>}
    </div>
  )
}

function Section({ id, title, children, note }: { id: string; title: string; children: ReactNode; note?: string }) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-[var(--color-divider)] pt-7">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <h2 className="text-[17px] font-semibold text-[var(--color-ink)]">{title}</h2>
        {note && <p className="text-[11px] text-[var(--color-text-muted)]">{note}</p>}
      </div>
      {children}
    </section>
  )
}

function TrendChart({ data }: { data: AdminAnalyticsDTO['daily'] }) {
  const width = 900
  const height = 230
  const pad = { left: 38, right: 16, top: 16, bottom: 34 }
  const max = Math.max(1, ...data.flatMap((d) => [d.dau, d.wau, d.mau]))
  const x = (i: number) => pad.left + (i * (width - pad.left - pad.right)) / Math.max(1, data.length - 1)
  const y = (v: number) => pad.top + (height - pad.top - pad.bottom) * (1 - v / max)
  const points = (key: 'dau' | 'wau' | 'mau') => data.map((d, i) => `${x(i)},${y(d[key])}`).join(' ')
  return (
    <div className="w-full overflow-hidden bg-white">
      <div className="mb-2 flex flex-wrap gap-4 text-[12px] text-[var(--color-text-secondary)]">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#E85577]" />DAU</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#2563EB]" />WAU</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#059669]" />MAU</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="block w-full min-w-[560px]" role="img" aria-label="DAU WAU MAU 趋势图">
        <rect width={width} height={height} fill="#FFFFFF" />
        {[0, .25, .5, .75, 1].map((ratio) => {
          const yy = y(max * ratio)
          return <g key={ratio}><line x1={pad.left} x2={width - pad.right} y1={yy} y2={yy} stroke={CHART_COLORS.grid} /><text x={pad.left - 6} y={yy + 4} textAnchor="end" fill={CHART_COLORS.muted} fontSize="11">{Math.round(max * ratio)}</text></g>
        })}
        <polyline fill="none" stroke={CHART_COLORS.mau} strokeWidth="2" points={points('mau')} />
        <polyline fill="none" stroke={CHART_COLORS.wau} strokeWidth="3" points={points('wau')} />
        <polyline fill="none" stroke={CHART_COLORS.dau} strokeWidth="3" points={points('dau')} />
        {data.map((d, i) => (i === 0 || i === data.length - 1 || i % Math.max(1, Math.ceil(data.length / 6)) === 0) && (
          <text key={d.day} x={x(i)} y={height - 9} textAnchor={i === 0 ? 'start' : i === data.length - 1 ? 'end' : 'middle'} fill={CHART_COLORS.muted} fontSize="11">{d.day.slice(5)}</text>
        ))}
      </svg>
    </div>
  )
}

export function AdminAnalyticsPage() {
  const today = useMemo(() => isoDay(new Date()), [])
  const initialStart = useMemo(() => {
    const d = new Date(); d.setDate(d.getDate() - 29); return isoDay(d)
  }, [])
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? '')
  const [start, setStart] = useState(initialStart)
  const [end, setEnd] = useState(today)
  const [data, setData] = useState<AdminAnalyticsDTO | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load(key = adminKey.trim()) {
    if (!key) return
    setLoading(true); setError('')
    try {
      const result = await adminGetAnalytics(start, end, key)
      setData(result); sessionStorage.setItem(ADMIN_KEY_STORAGE, key)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '加载失败，请稍后重试')
      if (err instanceof ApiError && (err.status === 403 || err.status === 503)) setData(null)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    const saved = sessionStorage.getItem(ADMIN_KEY_STORAGE)
    if (saved) void load(saved)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!data) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-white px-5" style={DASHBOARD_THEME}>
        <div className="w-full max-w-[380px] border-t-2 border-[var(--color-primary)] pt-5">
          <p className="text-[12px] text-[var(--color-primary)]">YUOYUO · INTERNAL</p>
          <h1 className="mt-2 text-[22px] font-semibold text-[var(--color-ink)]">产品健康看板</h1>
          <p className="mt-2 text-[13px] text-[var(--color-text-secondary)]">输入管理密钥读取实时聚合数据。密钥只保存在当前标签页。</p>
          <input type="password" value={adminKey} onChange={(e) => setAdminKey(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && void load()} placeholder="管理密钥" className="mt-5 h-[46px] w-full border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-3 text-[15px] text-[var(--color-ink)] outline-none focus:border-[var(--color-primary)]" />
          {error && <p className="mt-3 text-[13px] text-[var(--color-error)]" role="alert">{error}</p>}
          <button type="button" onClick={() => void load()} disabled={!adminKey.trim() || loading} className="mt-4 h-[44px] w-full bg-[var(--color-primary)] text-[14px] font-medium text-white disabled:opacity-50">{loading ? '读取中…' : '进入看板'}</button>
        </div>
      </div>
    )
  }

  const last = data.daily.at(-1)
  const revenue = Number(data.scope.revenue_cny || 0)
  const arppu = data.scope.paid_users ? revenue / data.scope.paid_users : 0
  const maturedD1 = data.retention.filter((r) => r.d1_pct != null)
  const weightedD1 = maturedD1.reduce((s, r) => s + r.d1_users, 0) / Math.max(1, maturedD1.reduce((s, r) => s + r.cohort_users, 0)) * 100

  return (
    <div className="h-full w-full overflow-y-auto bg-white text-[var(--color-ink)]" style={DASHBOARD_THEME}>
      <header className="sticky top-0 z-20 border-b border-[var(--color-divider)] bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div><p className="text-[11px] text-[var(--color-primary)]">YUOYUO · PRODUCT HEALTH</p><h1 className="text-[18px] font-semibold">产品健康看板</h1></div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-[11px] text-[var(--color-text-muted)]">开始<input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} className="ml-2 h-[36px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-2 text-[13px] text-[var(--color-ink)]" /></label>
            <label className="text-[11px] text-[var(--color-text-muted)]">结束<input type="date" value={end} min={start} max={today} onChange={(e) => setEnd(e.target.value)} className="ml-2 h-[36px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] px-2 text-[13px] text-[var(--color-ink)]" /></label>
            <button type="button" onClick={() => void load()} disabled={loading} className="h-[36px] bg-[var(--color-primary)] px-4 text-[13px] font-medium text-white disabled:opacity-50">{loading ? '刷新中…' : '刷新'}</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] space-y-9 px-4 py-7 pb-20 sm:px-6">
        {error && <p className="border-l-2 border-[var(--color-error)] pl-3 text-[13px] text-[var(--color-error)]" role="alert">{error}</p>}
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12px] text-[var(--color-text-secondary)]">
          <span>{data.window.start} 至 {data.window.end} · 上海时区</span>
          {data.data_quality.current_day_partial && <span className="text-[var(--color-warning)]">今天数据尚未完整</span>}
          <span>仅展示聚合数据，不含用户隐私与聊天内容</span>
        </div>

        <Section id="scale" title="一、整体用户规模分析">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
            <Stat label="累计注册" value={compact(data.scope.total_users)} note={`其中有效账号 ${compact(data.scope.active_users)}`} />
            <Stat label="区间新增" value={compact(data.scope.new_users)} />
            <Stat label="区间核心活跃" value={compact(data.scope.active_users_in_range)} note={`聊天/剧情输入 · ${compact(data.scope.sessions_in_range)} 个会话`} />
            <Stat label="核心激活率" value={pct(data.scope.new_users ? data.retention.reduce((s, r) => s + r.d0_users, 0) / data.scope.new_users * 100 : 0)} note="新增用户 D0 核心活跃" />
          </div>
        </Section>

        <Section id="active" title="二、DAU / WAU / MAU 活跃分析" note="DAU 只计聊天或剧情输入">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-4 mb-5">
            <Stat label="最新 DAU" value={compact(last?.dau)} />
            <Stat label="最新 WAU" value={compact(last?.wau)} />
            <Stat label="最新 MAU" value={compact(last?.mau)} />
            <Stat label="DAU / MAU" value={pct(last?.dau_mau_pct)} note="陪伴习惯形成度" />
          </div>
          <div className="overflow-x-auto"><TrendChart data={data.daily} /></div>
        </Section>

        <Section id="retention" title="三、用户留存分析（重点）" note={`成熟 cohort 加权 D1 ${pct(weightedD1)}`}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-[12px]">
              <thead className="text-[var(--color-text-muted)]"><tr className="border-b border-[var(--color-divider)]"><th className="py-2 font-medium">注册日</th><th>新增</th><th>D0</th><th>D1</th><th>D3</th><th>D7</th></tr></thead>
              <tbody>{data.retention.map((r) => <tr key={r.reg_day} className="border-b border-[var(--color-divider)]"><td className="py-3">{r.reg_day}</td><td>{r.cohort_users}</td><td>{pct(r.d0_pct)} <span className="text-[var(--color-text-muted)]">({r.d0_users})</span></td><td>{pct(r.d1_pct)}</td><td>{pct(r.d3_pct)}</td><td>{pct(r.d7_pct)}</td></tr>)}</tbody>
            </table>
          </div>
        </Section>

        <Section id="depth" title="四、用户活跃深度分析">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
            <Stat label="聊天用户" value={compact(data.depth.active_chat_users)} />
            <Stat label="用户对话轮次" value={compact(data.depth.user_turns)} />
            <Stat label="人均 / 中位轮次" value={`${compact(data.depth.avg_turns_per_user, 1)} / ${compact(data.depth.median_turns, 1)}`} />
            <Stat label="10轮 / 30轮用户" value={`${compact(data.depth.ten_turn_users)} / ${compact(data.depth.thirty_turn_users)}`} />
          </div>
        </Section>

        <Section id="characters" title="五、角色数据分析（非常重要）" note="按开聊人数、用户轮次排序">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-[12px]">
              <thead className="text-[var(--color-text-muted)]"><tr className="border-b border-[var(--color-divider)]"><th className="py-2 font-medium">角色</th><th>进入</th><th>开聊</th><th>进入→开聊</th><th>用户轮次</th><th>人均轮次</th><th>回访率</th></tr></thead>
              <tbody>{data.characters.map((c) => <tr key={c.character_name} className="border-b border-[var(--color-divider)]"><td className="py-3 font-medium">{c.character_name}</td><td>{c.entered_users}</td><td>{c.chat_users}</td><td>{pct(c.entry_to_chat_pct)}</td><td>{compact(c.user_turns)}</td><td>{compact(c.avg_turns, 1)}</td><td>{pct(c.return_rate_pct)}</td></tr>)}</tbody>
            </table>
          </div>
        </Section>

        <Section id="churn" title="六、用户流失分析" note={`以 ${data.window.end} 为观察日`}>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <Stat label="近 7 日仍活跃" value={compact(data.churn.active_last_7d)} />
            <Stat label="流失预警（7–13日）" value={compact(data.churn.lapsed_7_to_13d)} note="上周活跃、本周未活跃" />
            <Stat label="已流失（14日+）" value={compact(data.churn.lapsed_14d_plus)} note="曾有核心行为，连续14日无行为" />
          </div>
        </Section>

        <Section id="payment" title="七、付费分析">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
            <Stat label="收入" value={`¥${compact(revenue, 2)}`} />
            <Stat label="付费用户" value={compact(data.scope.paid_users)} />
            <Stat label="ARPPU" value={`¥${compact(arppu, 2)}`} />
            <Stat label="付费率" value={pct(data.scope.active_users_in_range ? data.scope.paid_users / data.scope.active_users_in_range * 100 : 0)} note="付费用户 / 区间核心活跃" />
          </div>
          {data.payments.length > 0 && <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[520px] text-left text-[12px]"><thead className="text-[var(--color-text-muted)]"><tr className="border-b border-[var(--color-divider)]"><th className="py-2 font-medium">日期</th><th>订单</th><th>付费用户</th><th>收入</th></tr></thead><tbody>{data.payments.map((p) => <tr key={p.day} className="border-b border-[var(--color-divider)]"><td className="py-3">{p.day}</td><td>{p.orders}</td><td>{p.paid_users}</td><td>¥{compact(Number(p.revenue_cny), 2)}</td></tr>)}</tbody></table></div>}
        </Section>

        <Section id="cost" title="八、AI 成本分析">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <Stat label="LLM 账本扣费次数" value={compact(data.ai_cost.llm_transactions)} />
            <Stat label="LLM 消耗用户" value={compact(data.ai_cost.llm_users)} />
            <Stat label="真实积分消耗" value={`${compact(data.ai_cost.llm_credits_spent, 2)} 悠悠币`} />
          </div>
          <div className="mt-5 border-l-2 border-[var(--color-warning)] pl-3 text-[12px] leading-relaxed text-[var(--color-text-secondary)]">
            <p className="font-medium text-[var(--color-ink)]">人民币成本暂不可计算</p>
            <p className="mt-1">{data.ai_cost.note} 当前不展示估算值，避免把用户积分价格误当供应商成本。</p>
          </div>
        </Section>
      </main>
    </div>
  )
}
