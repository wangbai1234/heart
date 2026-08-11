import { blockColors, type BlockProps } from './types'

/** 物件隐喻：卡片网格，label 作物件名，value 作它承载的意义。 */
export function ObjectsBlock({ block, chrome }: BlockProps<{ type: 'objects'; title: string; items: { label: string; value: string }[] }>) {
  const c = blockColors(chrome)
  return (
    <section>
      <h3
        className="mb-4 text-[13px] font-medium uppercase tracking-[0.18em]"
        style={{ color: c.accent, fontFamily: 'var(--font-serif, Georgia, serif)' }}
      >
        {block.title}
      </h3>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {block.items.map((it, i) => (
          <div
            key={i}
            className="rounded-xl border p-3.5"
            style={{ background: c.panel, borderColor: c.hairline }}
          >
            <div
              className="mb-1 text-[15px]"
              style={{ color: c.primary, fontFamily: 'var(--font-serif, Georgia, serif)' }}
            >
              {it.label}
            </div>
            <div className="text-[13.5px] leading-relaxed" style={{ color: c.muted }}>
              {it.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
