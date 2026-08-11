import { blockColors, type BlockProps } from './types'

/** 对照：表里反差。两列对齐，中缝一条 accent 分隔，每行一组对照。 */
export function ContrastBlock({ block, chrome }: BlockProps<{ type: 'contrast'; leftLabel: string; rightLabel: string; pairs: { label: string; value: string }[] }>) {
  const c = blockColors(chrome)
  return (
    <section className="rounded-2xl border p-4" style={{ background: c.panel, borderColor: c.hairline }}>
      <div className="mb-3 grid grid-cols-2 gap-4 text-[12px] uppercase tracking-[0.16em]">
        <div style={{ color: c.muted }}>{block.leftLabel}</div>
        <div className="text-right" style={{ color: c.accent }}>{block.rightLabel}</div>
      </div>
      <div className="relative space-y-3">
        <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2" style={{ background: c.hairline }} aria-hidden />
        {block.pairs.map((p, i) => (
          <div key={i} className="grid grid-cols-2 gap-4 text-[14.5px] leading-relaxed">
            <div style={{ color: c.muted }}>{p.label}</div>
            <div className="text-right" style={{ color: c.primary }}>{p.value}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
