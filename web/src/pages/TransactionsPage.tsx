import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreditsStore } from '../stores/creditsStore'
import { getTransactions } from '../services/api'
import { Skeleton } from '../components/ui/Skeleton'
import { useScrollRestore } from '../hooks/useScrollRestore'

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
  refund: '退款',
  adjust: '手动调整',
}

export function TransactionsPage() {
  const navigate = useNavigate()
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
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center px-5 pt-4 pb-3" style={{ paddingTop: 'var(--safe-top)' }}>
        <button onClick={() => navigate(-1 as any)} className="text-[var(--color-ink)] text-[14px] active:opacity-60">
          ← 返回
        </button>
        <h2 className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] pr-10">积分明细</h2>
      </div>

      {/* Balance card */}
      <div className="mx-5 mb-4 p-4 rounded-[16px] bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-accent)]">
        <p className="text-[13px] text-white/70">当前积分</p>
        <p className="text-[32px] font-bold text-white mt-1">{balance}</p>
      </div>

      {/* Transaction list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5">
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
            <p className="text-[var(--color-text-muted)] text-[14px]">暂无积分记录</p>
          </div>
        ) : (
          <div className="space-y-0">
            {items.map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-3 border-b border-[var(--color-divider-inset)]"
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
