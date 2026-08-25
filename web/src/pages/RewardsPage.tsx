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

  const copyInvite = async () => {
    if (!store.invite) return
    try {
      await navigator.clipboard.writeText(store.invite.invite_url)
      showToast('邀请链接已复制', 'success')
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
            <InvitePanel store={store} onCopy={() => void copyInvite()} />
          ) : view === 'lottery' ? (
            <LotteryPanel
              store={store}
              spinning={spinning}
              rotation={rotation}
              result={result}
              onDraw={() => void runDraw()}
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

function InvitePanel({ store, onCopy }: { store: RewardsState; onCopy: () => void }) {
  return (
    <section className="space-y-4">
      <div className="relative min-h-[180px] overflow-hidden rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-5 pr-[116px]">
        <p className="text-[12px] font-medium text-[var(--color-primary-600)]">我的邀请码</p>
        <p className="mt-2 font-[var(--font-latin)] text-[26px] font-bold tracking-[0.14em] text-[var(--color-ink)]">{store.invite?.invite_code}</p>
        <button onClick={onCopy} className="mt-5 h-[40px] rounded-[8px] bg-[var(--color-primary-500)] px-4 text-[13px] font-medium text-white">复制链接</button>
        <img src="/assets/settings/invite-mascot.webp" alt="" className="absolute bottom-2 right-1 h-[118px] w-[118px] object-contain" />
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

function LotteryPanel({ store, spinning, rotation, result, onDraw, onToast }: {
  store: RewardsState
  spinning: boolean
  rotation: number
  result: LotteryDrawResult | null
  onDraw: () => void
  onToast: (message: string, variant?: 'info' | 'error' | 'success') => void
}) {
  const prizes = orderLotteryPrizes(store.lottery?.pool_prizes ?? []).slice(0, WHEEL_PRIZE_CODES.length)

  return (
    <section>
      <div className="mx-auto flex max-w-[420px] flex-col items-center">
        <div className="relative aspect-square w-full max-w-[310px]">
          <div className="absolute left-1/2 top-[-5px] z-10 h-0 w-0 -translate-x-1/2 border-x-[10px] border-t-[20px] border-x-transparent border-t-[var(--color-ink)]" />
          <div
            className="absolute inset-0 transition-transform duration-[900ms] ease-out"
            style={{ transform: `rotate(${rotation}deg)` }}
          >
            <img
              src="/assets/rewards/lottery-wheel-10.png"
              alt=""
              draggable={false}
              className="absolute inset-0 h-full w-full select-none object-contain"
            />
            <div className="absolute inset-0" aria-hidden="true">
              {prizes.map((prize, index) => {
                const angle = index * WHEEL_SECTOR_ANGLE
                return (
                  <div
                    key={prize.code}
                    className="absolute inset-0"
                    style={{ transform: `rotate(${angle}deg)` }}
                  >
                    <span
                      className="absolute left-1/2 top-[17%] block w-[58px] -translate-x-1/2 -translate-y-1/2 text-center text-[10px] font-semibold leading-[1.15] text-[#5a4852] [text-shadow:0_1px_1px_rgba(255,255,255,0.7)]"
                    >
                      <span className="inline-block" style={{ transform: `rotate(${-angle}deg)` }}>
                        {PRIZE_LABELS[prize.code] ?? prize.code}
                      </span>
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
          <button
            onClick={onDraw}
            disabled={spinning || !store.lottery?.available_chances}
            className="absolute left-1/2 top-1/2 z-20 flex h-[88px] w-[88px] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-[6px] border-white bg-[var(--color-primary-500)] text-[15px] font-semibold text-white shadow-[var(--shadow-btn)] disabled:opacity-50"
          >
            {spinning ? '抽取中' : '抽奖'}
          </button>
        </div>
        <p className="mt-4 min-h-[28px] text-[18px] font-semibold text-[var(--color-ink)]">
          {result ? `获得 ${PRIZE_LABELS[result.prize_code] ?? result.prize_code}` : `${store.lottery?.available_chances ?? 0} 次机会`}
        </p>
        <p className="text-[12px] text-[var(--color-text-muted)]">最近到期 {formatDate(store.lottery?.next_expiry_at ?? null)}</p>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-divider)] sm:grid-cols-5">
        {prizes.map((prize) => (
          <div key={prize.code} className="bg-[var(--color-page-surface)] px-3 py-3 text-center text-[12px] text-[var(--color-text-secondary)]">{PRIZE_LABELS[prize.code] ?? prize.code}</div>
        ))}
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

function StatusLabel({ status }: { status: string }) {
  const labels: Record<string, string> = { pending: '互动中', qualified: '已生效', review: '审核中', rejected: '未通过' }
  return <span className="text-[12px] font-medium text-[var(--color-text-secondary)]">{labels[status] ?? status}</span>
}

function EmptyRow({ text }: { text: string }) { return <p className="py-8 text-center text-[13px] text-[var(--color-text-muted)]">{text}</p> }
function LoadError({ onRetry }: { onRetry: () => void }) { return <div className="py-16 text-center"><p className="text-[14px] text-[var(--color-text-muted)]">加载失败</p><button onClick={onRetry} className="mt-3 text-[13px] font-medium text-[var(--color-primary-600)]">重试</button></div> }
function RewardsSkeleton() { return <div className="space-y-4"><Skeleton height={180} className="rounded-[8px]" /><Skeleton height={52} className="rounded-[8px]" /><Skeleton height={180} className="rounded-[8px]" /></div> }
