import { useEffect, useMemo, useState } from 'react'
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'
import { Skeleton } from '../components/ui/Skeleton'
import { TabBar } from '../components/ui/TabBar'
import type { LotteryDrawResult } from '../services/api'
import { useCreditsStore } from '../stores/creditsStore'
import { useRewardsStore } from '../stores/rewardsStore'
import { useToastStore } from '../stores/toastStore'

type RewardsView = 'invite' | 'lottery' | 'commission'
type RewardsState = ReturnType<typeof useRewardsStore.getState>

const WHEEL_PRIZE_CODES = [
  'coin_20', 'coin_40', 'coin_60', 'coin_80', 'coin_100',
  'coin_200', 'vip_plus_3d', 'vip_immersive_3d', 'vip_plus_30d',
  'vip_immersive_30d',
] as const
const WHEEL_SECTOR_ANGLE = 360 / WHEEL_PRIZE_CODES.length
const WHEEL_SPIN_DURATION_MS = 900

const PRIZE_LABELS: Record<string, string> = {
  coin_20: '20 币', coin_40: '40 币', coin_60: '60 币', coin_80: '80 币',
  coin_100: '100 币', coin_200: '200 币', vip_plus_3d: '进阶 3 天',
  vip_immersive_3d: '沉浸 3 天', vip_plus_30d: '进阶月卡',
  vip_immersive_30d: '沉浸月卡',
}

type LotteryPrize = NonNullable<RewardsState['lottery']>['pool_prizes'][number]

function orderLotteryPrizes(prizes: LotteryPrize[]): LotteryPrize[] {
  const byCode = new Map(prizes.map((prize) => [prize.code, prize]))
  const ordered = WHEEL_PRIZE_CODES
    .map((code) => byCode.get(code))
    .filter((prize): prize is LotteryPrize => Boolean(prize))
  const extras = prizes.filter((prize) => !WHEEL_PRIZE_CODES.includes(prize.code as typeof WHEEL_PRIZE_CODES[number]))
  return [...ordered, ...extras]
}

function getPrizeIndex(prizeCode: string, prizes: LotteryPrize[]): number {
  const index = orderLotteryPrizes(prizes).findIndex((prize) => prize.code === prizeCode)
  return index >= 0 ? index : 0
}

function formatDate(value: string | null): string {
  if (!value) return '--'
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' })
    .format(new Date(value))
}

export function RewardsPage() {
  const [view, setView] = useState<RewardsView>('lottery')
  const [spinning, setSpinning] = useState(false)
  const [rotation, setRotation] = useState(0)
  const [result, setResult] = useState<LotteryDrawResult | null>(null)
  const store = useRewardsStore()
  const showToast = useToastStore((state) => state.show)

  useEffect(() => { void store.refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const copyInvite = async (value: string, label: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      showToast(`${label}已复制`, 'success')
    } catch {
      showToast('复制失败，请稍后重试', 'error')
    }
  }

  const runDraw = async () => {
    if (spinning || !store.lottery?.available_chances) return
    setSpinning(true)
    setResult(null)
    try {
      const next = await store.draw()
      const prizeIndex = getPrizeIndex(next.prize_code, store.lottery?.pool_prizes ?? [])
      const targetOffset = ((WHEEL_PRIZE_CODES.length - prizeIndex) % WHEEL_PRIZE_CODES.length) * WHEEL_SECTOR_ANGLE
      const currentOffset = ((rotation % 360) + 360) % 360
      const clockwiseOffset = (targetOffset - currentOffset + 360) % 360
      setRotation(rotation + 1440 + clockwiseOffset)
      window.setTimeout(() => {
        setResult(next)
        setSpinning(false)
        if (next.balance !== null) useCreditsStore.getState().setBalance(next.balance)
      }, WHEEL_SPIN_DURATION_MS)
    } catch {
      setSpinning(false)
      showToast('抽奖失败，请稍后重试', 'error')
    }
  }

  const pendingCommission = useMemo(
    () => store.commission?.entries.filter((entry) => entry.status === 'pending')
      .reduce((sum, entry) => sum + entry.commission_fen, 0) ?? 0,
    [store.commission],
  )

  return (
    <AppPageShell className="app-atmosphere">
      <div className="relative z-10 flex h-full flex-col bg-transparent">
        <div style={{ height: 'var(--safe-top)' }} />
        <AppPageContent className="flex h-[58px] shrink-0 items-center justify-between px-4 sm:px-5">
          <h1 className="text-[23px] font-bold text-[var(--color-ink)]">福利</h1>
          <span className="text-[12px] text-[var(--color-text-muted)]">
            {store.lottery?.available_chances ?? 0} 次可用
          </span>
        </AppPageContent>

        <AppPageContent className="px-4 sm:px-5">
          <div className="grid h-[38px] grid-cols-3 rounded-[8px] bg-[var(--color-page-soft)] p-1" role="tablist">
            {([['invite', '邀请'], ['lottery', '抽奖'], ['commission', '佣金']] as const)
              .map(([id, label]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={view === id}
                  onClick={() => setView(id)}
                  className={`rounded-[6px] text-[13px] font-medium transition-colors ${view === id ? 'bg-[var(--color-page-surface)] text-[var(--color-ink)] shadow-[var(--shadow-soft)]' : 'text-[var(--color-text-muted)]'}`}
                >
                  {label}
                </button>
              ))}
          </div>
        </AppPageContent>

        <AppPageContent className="min-h-0 flex-1 overflow-y-auto px-4 pb-[116px] pt-4 sm:px-5">
          {store.loading && !store.invite ? <RewardsSkeleton /> : store.error && !store.invite ? (
            <LoadError onRetry={() => void store.refresh()} />
          ) : view === 'invite' ? (
            <InvitePanel
              store={store}
              onCopyCode={() => void copyInvite(store.invite?.invite_code ?? '', '邀请码')}
              onCopyLink={() => void copyInvite(store.invite?.invite_url ?? '', '邀请链接')}
            />
          ) : view === 'lottery' ? (
            <LotteryPanel
              store={store}
              spinning={spinning}
              rotation={rotation}
              result={result}
              onDraw={() => void runDraw()}
              onInvite={() => setView('invite')}
              onToast={showToast}
            />
          ) : (
            <CommissionPanel store={store} pendingFen={pendingCommission} onToast={showToast} />
          )}
        </AppPageContent>
        <TabBar />
      </div>
    </AppPageShell>
  )
}

function InvitePanel({ store, onCopyCode, onCopyLink }: {
  store: RewardsState
  onCopyCode: () => void
  onCopyLink: () => void
}) {
  return (
    <section className="space-y-5">
      <div className="relative overflow-hidden rounded-[8px] border border-[#f1b3c0]/35 bg-[var(--color-page-surface)] p-5 shadow-[0_12px_32px_rgba(117,58,76,0.10)]">
        <div className="relative min-h-[122px] pr-[104px] sm:pr-[150px]">
          <p className="text-[11px] font-bold text-[var(--color-primary-600)]">邀请好友 · 双重奖励</p>
          <h2 className="mt-2 text-[21px] font-bold leading-[1.3] text-[var(--color-ink)]">
            好友聊满 3 条<br />送你 1 次抽奖
          </h2>
          <p className="mt-2 text-[12px] leading-[1.55] text-[var(--color-text-secondary)]">
            好友付费，再享实付金额 10% 佣金
          </p>
          <img src="/assets/settings/invite-mascot.webp" alt="" className="absolute -right-3 -top-1 h-[116px] w-[116px] object-contain sm:right-3 sm:h-[136px] sm:w-[136px]" />
        </div>
        <div className="mt-3 border-t border-[var(--color-divider)] pt-4">
          <p className="text-[11px] text-[var(--color-text-muted)]">我的邀请码</p>
          <p className="mt-1 font-[var(--font-latin)] text-[25px] font-bold tracking-[0.14em] text-[var(--color-ink)]">{store.invite?.invite_code ?? '--'}</p>
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <button onClick={onCopyCode} className="flex h-[42px] items-center justify-center gap-1.5 rounded-[8px] border border-[var(--color-primary-400)] text-[13px] font-semibold text-[var(--color-primary-600)] active:scale-[0.98]">
              <CopyIcon />
              复制邀请码
            </button>
            <button onClick={onCopyLink} className="flex h-[42px] items-center justify-center gap-1.5 rounded-[8px] bg-[var(--color-primary-500)] text-[13px] font-semibold text-white shadow-[0_7px_18px_rgba(255,110,138,0.24)] active:scale-[0.98]">
              <LinkIcon />
              复制邀请链接
            </button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center border-y border-[var(--color-divider)] py-4">
        <InviteStep index="1" label="分享邀请" />
        <span className="h-px w-4 bg-[var(--color-divider)] sm:w-8" />
        <InviteStep index="2" label="好友互动" />
        <span className="h-px w-4 bg-[var(--color-divider)] sm:w-8" />
        <InviteStep index="3" label="机会到账" />
      </div>
      <div className="grid grid-cols-3 border-y border-[var(--color-divider)] py-4">
        <Metric value={store.invite?.invited_count ?? 0} label="有效邀请" />
        <Metric value={store.invite?.pending_count ?? 0} label="互动中" />
        <Metric value={store.invite?.today_remaining ?? 0} label="今日剩余" />
      </div>
      <div>
        <h2 className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">邀请进度</h2>
        <div className="divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
          {(store.invite?.invitees ?? []).map((invitee, index) => (
            <div key={invitee.id} className="flex min-h-[58px] items-center justify-between py-2">
              <div>
                <p className="text-[14px] text-[var(--color-ink)]">好友 {index + 1}</p>
                <p className="text-[11px] text-[var(--color-text-muted)]">{invitee.msg_count}/3 条互动</p>
              </div>
              <StatusLabel status={invitee.status} />
            </div>
          ))}
          {!store.invite?.invitees.length && <EmptyRow text="暂无邀请记录" />}
        </div>
      </div>
    </section>
  )
}

function LotteryPanel({ store, spinning, rotation, result, onDraw, onInvite, onToast }: {
  store: RewardsState
  spinning: boolean
  rotation: number
  result: LotteryDrawResult | null
  onDraw: () => void
  onInvite: () => void
  onToast: (message: string, variant?: 'info' | 'error' | 'success') => void
}) {
  const prizes = orderLotteryPrizes(store.lottery?.pool_prizes ?? []).slice(0, WHEEL_PRIZE_CODES.length)

  return (
    <section className="space-y-5">
      <div className="flex items-start justify-between gap-4 border-b border-[var(--color-divider)] pb-4">
        <div>
          <p className="text-[11px] font-bold text-[var(--color-primary-600)]">幸运转盘 · 次次有奖</p>
          <h2 className="mt-1 text-[20px] font-bold leading-[1.35] text-[var(--color-ink)]">最高赢沉浸版月卡</h2>
          <p className="mt-1 text-[12px] text-[var(--color-text-secondary)]">邀请好友完成有效互动，机会自动到账</p>
        </div>
        <button onClick={onInvite} className="shrink-0 rounded-[8px] border border-[var(--color-primary-300)] px-3 py-2 text-[12px] font-semibold text-[var(--color-primary-600)] active:scale-[0.98]">
          赚机会
        </button>
      </div>

      <div className="overflow-hidden rounded-[8px] border border-[#efb2bf]/30 bg-[var(--color-page-surface)] px-3 pb-5 pt-4 shadow-[0_14px_34px_rgba(104,51,67,0.10)] sm:px-6">
        <div className="mx-auto mb-3 grid max-w-[390px] grid-cols-3 divide-x divide-[var(--color-divider)] border-y border-[var(--color-divider)] py-3">
          <RewardPromise value={`${store.lottery?.available_chances ?? 0} 次`} label="当前可抽" accent />
          <RewardPromise value="100%" label="次次有奖" />
          <RewardPromise value="¥69" label="最高价值" />
        </div>

        <div className="mx-auto flex max-w-[420px] flex-col items-center">
          <div className="relative aspect-square w-full max-w-[342px]">
            <div className="absolute left-1/2 top-[1.5%] z-30 h-0 w-0 -translate-x-1/2 border-x-[10px] border-t-[19px] border-x-transparent border-t-[#7f4d58] drop-shadow-[0_2px_2px_rgba(0,0,0,0.2)]" />
            <div
              className="absolute inset-0 transition-transform duration-[900ms] ease-out motion-reduce:transition-none"
              style={{ transform: `rotate(${rotation}deg)`, willChange: 'transform' }}
            >
              <img
                src="/assets/rewards/lottery-wheel-10.png"
                alt=""
                aria-hidden="true"
                draggable={false}
                className="absolute inset-0 h-full w-full select-none object-contain drop-shadow-[0_12px_18px_rgba(41,22,27,0.2)]"
              />
              {prizes.map((prize, index) => {
                const angle = index * WHEEL_SECTOR_ANGLE
                const radians = angle * Math.PI / 180
                return (
                  <span
                    key={prize.code}
                    className="absolute z-10 -translate-x-1/2 -translate-y-1/2"
                    style={{
                      left: `${50 + 31 * Math.sin(radians)}%`,
                      top: `${50 - 31 * Math.cos(radians)}%`,
                    }}
                  >
                    <span
                      className="flex items-center justify-center whitespace-nowrap rounded-full bg-[#4b2c35]/78 px-1.5 py-1 font-bold leading-none text-white shadow-[0_2px_6px_rgba(49,24,30,0.25)] transition-transform duration-[900ms] ease-out motion-reduce:transition-none"
                      style={{
                        fontSize: 'clamp(8px, 2.5vw, 10px)',
                        minWidth: 'clamp(44px, 14vw, 58px)',
                        transform: `rotate(${-rotation}deg)`,
                      }}
                    >
                      {PRIZE_LABELS[prize.code] ?? prize.code}
                    </span>
                  </span>
                )
              })}
            </div>
            <button
              onClick={onDraw}
              disabled={spinning || !store.lottery?.available_chances}
              className="absolute left-1/2 top-1/2 z-20 flex h-[25%] w-[25%] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-transparent text-[15px] font-bold text-[#8d5361] outline-none transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:ring-2 focus-visible:ring-white/90 focus-visible:ring-offset-2 focus-visible:ring-offset-[#dfa987]"
            >
              {spinning ? '抽取中' : '抽奖'}
            </button>
          </div>
          <div className="mt-2 min-h-[54px] text-center" aria-live="polite">
            <p className={`text-[18px] font-bold ${result ? 'text-[var(--color-primary-600)]' : 'text-[var(--color-ink)]'}`}>
              {result ? `恭喜获得 ${PRIZE_LABELS[result.prize_code] ?? result.prize_code}` : '点击中心，抽取今日好运'}
            </p>
            <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">
              {result ? '奖励已自动发放到账户' : '悠悠币立即到账，会员奖进入体验卡'}
            </p>
            <p className="mt-1 text-[10px] text-[var(--color-text-muted)]">机会有效期至 {formatDate(store.lottery?.next_expiry_at ?? null)}</p>
          </div>
        </div>
      </div>

      <button onClick={onInvite} className="flex h-[48px] w-full items-center justify-center gap-2 rounded-[8px] bg-[var(--color-primary-500)] text-[14px] font-semibold text-white shadow-[0_8px_20px_rgba(255,110,138,0.22)] active:scale-[0.99]">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6M22 11h-6" />
        </svg>
        邀请好友，赚更多抽奖机会
      </button>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-[var(--color-primary-600)]">REWARD VAULT</p>
            <h2 className="mt-0.5 text-[17px] font-bold text-[var(--color-ink)]">奖励宝库</h2>
          </div>
          <span className="text-[11px] text-[var(--color-text-muted)]">每次必得其一</span>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {prizes.map((prize) => (
            <RewardCard key={prize.code} code={prize.code} label={PRIZE_LABELS[prize.code] ?? prize.code} />
          ))}
        </div>
      </div>
      {!!store.coupons.length && (
        <div className="mt-6">
          <h2 className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">体验卡</h2>
          <div className="divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
            {store.coupons.map((coupon) => (
              <div key={coupon.id} className="flex min-h-[62px] items-center justify-between py-2">
                <div>
                  <p className="text-[14px] text-[var(--color-ink)]">{coupon.tier === 'plus' ? '进阶版' : '沉浸版'} {coupon.days} 天</p>
                  <p className="text-[11px] text-[var(--color-text-muted)]">{coupon.status === 'active' ? `${formatDate(coupon.activate_by)} 前激活` : coupon.status === 'activated' ? '已激活' : '已过期'}</p>
                </div>
                {coupon.status === 'active' && (
                  <button onClick={() => void store.activateCoupon(coupon.id).then(() => onToast('体验卡已激活', 'success')).catch(() => onToast('激活失败', 'error'))} className="h-[34px] rounded-[8px] border border-[var(--color-primary-500)] px-3 text-[12px] font-medium text-[var(--color-primary-600)]">激活</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function CommissionPanel({ store, pendingFen, onToast }: {
  store: RewardsState
  pendingFen: number
  onToast: (message: string, variant?: 'info' | 'error' | 'success') => void
}) {
  return (
    <section className="space-y-5">
      <div className="border-b border-[var(--color-divider)] pb-5">
        <p className="text-[12px] text-[var(--color-text-muted)]">可用佣金</p>
        <p className="mt-1 text-[36px] font-bold text-[var(--color-ink)]">¥{(store.commission?.balance_yuan ?? 0).toFixed(2)}</p>
        <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">待结算 ¥{(pendingFen / 100).toFixed(2)}</p>
      </div>
      <div>
        <h2 className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">兑换权益</h2>
        <div className="divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
          {Object.entries(store.commission?.products ?? {}).map(([sku, product]) => (
            <div key={sku} className="flex min-h-[62px] items-center justify-between py-2">
              <div>
                <p className="text-[14px] text-[var(--color-ink)]">{product.target === 'membership' ? (product.tier === 'plus' ? '进阶版会员' : '沉浸版会员') : `${product.coins} 悠悠币`}</p>
                <p className="text-[11px] text-[var(--color-text-muted)]">¥{(product.price_fen / 100).toFixed(2)}</p>
              </div>
              <button
                disabled={(store.commission?.balance_fen ?? 0) < product.price_fen}
                onClick={() => void store.spend(product.target, sku).then(() => onToast('兑换成功', 'success')).catch(() => onToast('兑换失败', 'error'))}
                className="h-[34px] rounded-[8px] bg-[var(--color-primary-500)] px-3 text-[12px] font-medium text-white disabled:opacity-40"
              >兑换</button>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h2 className="mb-2 text-[15px] font-semibold text-[var(--color-ink)]">佣金明细</h2>
        <div className="divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
          {(store.commission?.entries ?? []).map((entry) => (
            <div key={entry.order_id} className="flex min-h-[54px] items-center justify-between py-2">
              <div><p className="text-[13px] text-[var(--color-ink)]">邀请返佣</p><p className="text-[11px] text-[var(--color-text-muted)]">{formatDate(entry.created_at)}</p></div>
              <div className="text-right"><p className="text-[13px] font-medium text-[var(--color-ink)]">+¥{(entry.commission_fen / 100).toFixed(2)}</p><p className="text-[11px] text-[var(--color-text-muted)]">{entry.status === 'pending' ? '待结算' : entry.status === 'settled' ? '已入账' : '已冲正'}</p></div>
            </div>
          ))}
          {!store.commission?.entries.length && <EmptyRow text="暂无佣金记录" />}
        </div>
      </div>
    </section>
  )
}

function Metric({ value, label }: { value: number; label: string }) {
  return <div className="text-center"><p className="text-[21px] font-bold text-[var(--color-ink)]">{value}</p><p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{label}</p></div>
}

function RewardPromise({ value, label, accent = false }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="text-center">
      <p className={`text-[17px] font-bold ${accent ? 'text-[var(--color-primary-600)]' : 'text-[var(--color-ink)]'}`}>{value}</p>
      <p className="mt-1 text-[10px] text-[var(--color-text-muted)]">{label}</p>
    </div>
  )
}

function RewardCard({ code, label }: { code: string; label: string }) {
  const isVip = code.startsWith('vip_')
  const isMonth = code.endsWith('_30d')
  const isGrand = code === 'coin_200' || isMonth
  const detail = isVip
    ? `${code.includes('immersive') ? '沉浸版' : '进阶版'}会员`
    : '悠悠币'

  return (
    <div className={`relative min-h-[88px] overflow-hidden rounded-[8px] border p-3 ${isGrand ? 'border-[#e8ba68]/65 bg-[#e8ba68]/[0.08] shadow-[0_7px_18px_rgba(174,118,37,0.10)]' : 'border-[var(--color-divider)] bg-[var(--color-page-surface)]'}`}>
      {isGrand && <span className="absolute inset-x-0 top-0 h-[3px] bg-[#e8ba68]" />}
      <div className="flex items-start justify-between gap-2">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${isVip ? 'bg-[#9b84d7]/18 text-[#9b84d7]' : 'bg-[#ff8faa]/16 text-[var(--color-primary-600)]'}`}>
          {isVip ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="m3 8 4.5 4L12 5l4.5 7L21 8l-2 10H5L3 8Z" /><path d="M5 21h14" />
            </svg>
          ) : (
            <span className="text-[12px] font-black">Y</span>
          )}
        </span>
        {isGrand && <span className="rounded-full bg-[#e8ba68]/18 px-1.5 py-1 text-[9px] font-bold text-[#bd7e25]">大奖</span>}
      </div>
      <p className="mt-2 text-[13px] font-bold text-[var(--color-ink)]">{label}</p>
      <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">{detail}</p>
    </div>
  )
}

function CopyIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

function LinkIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  )
}

function InviteStep({ index, label }: { index: string; label: string }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5 text-center">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-primary-100)] text-[11px] font-bold text-[var(--color-primary-600)]">{index}</span>
      <span className="text-[11px] font-medium text-[var(--color-text-secondary)]">{label}</span>
    </div>
  )
}

function StatusLabel({ status }: { status: string }) {
  const labels: Record<string, string> = { pending: '互动中', qualified: '已生效', review: '审核中', rejected: '未通过' }
  return <span className="text-[12px] font-medium text-[var(--color-text-secondary)]">{labels[status] ?? status}</span>
}

function EmptyRow({ text }: { text: string }) { return <p className="py-8 text-center text-[13px] text-[var(--color-text-muted)]">{text}</p> }
function LoadError({ onRetry }: { onRetry: () => void }) { return <div className="py-16 text-center"><p className="text-[14px] text-[var(--color-text-muted)]">加载失败</p><button onClick={onRetry} className="mt-3 text-[13px] font-medium text-[var(--color-primary-600)]">重试</button></div> }
function RewardsSkeleton() { return <div className="space-y-4"><Skeleton height={180} className="rounded-[8px]" /><Skeleton height={52} className="rounded-[8px]" /><Skeleton height={180} className="rounded-[8px]" /></div> }
