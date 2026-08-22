import { useEffect, useState } from 'react'
import { useCreditsStore } from '../stores/creditsStore'
import { getTransactions } from '../services/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useScrollRestore } from '../hooks/useScrollRestore'
import { useSafeBack } from '../hooks/useSafeBack'

interface Transaction {
  delta: number
  type: string
  ref_type: string
  balance_after: number
  created_at: string
}

const TYPE_LABELS: Record<string, string> = {
  grant: '注册赠送',
  redeem: '兑换码充值',
  consume_text: '文本对话',
  consume_voice: '语音对话',
  consume_llm: '模型对话',
  consume_tts: '语音合成',
  consume_clone: '声音克隆',
  membership_grant: '会员赠币',
  invite: '邀请奖励',
  refund: '退款',
  adjust: '手动调整',
}

export function TransactionsPage() {
  const goBack = useSafeBack('/wallet')
  const { balance, refresh: refreshCredits } = useCreditsStore()
  const scrollRef = useScrollRestore()
  const [items, setItems] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [loadMoreError, setLoadMoreError] = useState(false)

  useEffect(() => {
    refreshCredits()
    loadInitial()
  }, [])

  const loadInitial = async () => {
    setLoading(true)
    setLoadError(false)
    try {
      const data = await getTransactions(undefined, 20)
      setItems(data.items)
      setNextCursor(data.next_cursor)
    } catch {
      setLoadError(true)
    }
    setLoading(false)
  }

  const loadMore = async () => {
    if (!nextCursor || loadingMore) return
    setLoadingMore(true)
    setLoadMoreError(false)
    try {
      const data = await getTransactions(nextCursor, 20)
      setItems((prev) => [...prev, ...data.items])
      setNextCursor(data.next_cursor)
    } catch {
      setLoadMoreError(true)
    }
    setLoadingMore(false)
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  return (
    <div className="app-atmosphere relative flex h-full w-full flex-col overflow-hidden">
      <div style={{ height: 'var(--safe-top)' }} />
      {/* Header */}
      <nav className="relative z-20 flex h-[52px] shrink-0 items-center justify-between border-b border-white/40 px-5">
        <button onClick={goBack} className="w-[44px] h-[44px] flex items-center justify-center">
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        <span className="text-[17px] font-semibold text-[var(--color-ink)]">yuoyuo币明细</span>
        <div className="w-[44px]" />
      </nav>

      {/* Balance card */}
      <div className="relative z-10 mx-4 mb-4 mt-4 overflow-hidden rounded-[20px] border border-white/35 bg-[linear-gradient(135deg,#FF9FB3_0%,#FF7898_56%,#A7C7E7_100%)] p-5 shadow-[0_12px_30px_rgba(232,85,119,0.18)]">
        <div className="pointer-events-none absolute inset-y-0 right-0 w-[42%] bg-[linear-gradient(110deg,transparent,rgba(255,255,255,0.18))]" />
        <div className="relative flex items-start justify-between">
          <div>
            <p className="text-[13px] text-white/75">当前 yuoyuo币</p>
            <p className="mt-1 text-[34px] font-bold leading-none text-white">{balance}</p>
          </div>
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.84)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="8.5" />
            <path d="M12 7v10M15 9.5c-.7-1-1.7-1.5-3-1.5-1.7 0-3 1-3 2.4 0 3.1 6 1.5 6 4.4 0 1.5-1.3 2.7-3.2 2.7-1.5 0-2.6-.5-3.4-1.6" />
          </svg>
        </div>
        <p className="relative mt-3 text-[12px] text-white/70">签到币与购买币均永久有效</p>
      </div>

      {/* Transaction list */}
      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 pb-2">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between py-3">
                <div>
                  <Skeleton width={80} height={14} />
                  <Skeleton width={50} height={10} className="mt-1" />
                </div>
                <Skeleton width={60} height={14} />
              </div>
            ))}
          </div>
        ) : loadError ? (
          <div className="text-center py-12">
            <p className="text-[var(--color-text-muted)] text-[14px]">加载失败</p>
            <button onClick={loadInitial} className="mt-3 text-[13px] text-[var(--color-primary)] active:opacity-60">重试</button>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-[var(--color-text-muted)] text-[14px]">暂无 yuoyuo币记录</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-[18px] border border-[var(--color-border-glass)] bg-[var(--color-glass-card)] shadow-[var(--shadow-card)]">
            {items.map((item, i) => (
              <div
                key={i}
                className={`flex items-center justify-between px-4 py-3.5 ${i < items.length - 1 ? 'border-b border-[var(--color-divider-inset)]' : ''}`}
              >
                <div>
                  <p className="text-[14px] text-[var(--color-ink)]">
                    {TYPE_LABELS[item.type] || item.type}
                  </p>
                  <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
                    {formatDate(item.created_at)}
                  </p>
                </div>
                <span
                  className={`text-[15px] font-medium ${
                    item.delta > 0 ? 'text-[var(--color-primary)]' : 'text-[var(--color-ink)]'
                  }`}
                >
                  {item.delta > 0 ? '+' : ''}{item.delta}
                </span>
              </div>
            ))}

            {nextCursor && (
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className={`w-full py-3 text-center text-[13px] active:opacity-60 ${
                  loadMoreError
                    ? 'text-[var(--color-error)]'
                    : 'text-[var(--color-primary)]'
                }`}
              >
                {loadingMore
                  ? '加载中...'
                  : loadMoreError
                  ? '加载失败，点击重试'
                  : '加载更多'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Bottom safe area */}
      <div style={{ height: 'var(--safe-bottom)' }} />
    </div>
  )
}
