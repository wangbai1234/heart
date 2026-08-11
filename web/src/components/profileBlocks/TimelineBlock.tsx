import { blockColors, type BlockProps } from './types'

/** 纵向时间线：竖轴 + 节点，label 作时间/阶段，value 作事件。 */
export function TimelineBlock({ block, chrome }: BlockProps<{ type: 'timeline'; title: string; events: { label: string; value: string }[] }>) {
  const c = blockColors(chrome)
  return (
    <section>
      <h3
        className="mb-4 text-[13px] font-medium uppercase tracking-[0.18em]"
        style={{ color: c.accent, fontFamily: 'var(--font-serif, Georgia, serif)' }}
      >
        {block.title}
      </h3>
      <ol className="relative ml-1 space-y-5">
        <span className="absolute left-[3px] top-1.5 bottom-1.5 w-px" style={{ background: c.hairline }} aria-hidden />
        {block.events.map((ev, i) => (
          <li key={i} className="relative pl-6">
            <span
              className="absolute left-0 top-[6px] h-[7px] w-[7px] rounded-full ring-2"
              style={{ background: c.accent, boxShadow: `0 0 0 3px ${chrome.bg}` }}
              aria-hidden
            />
            <div className="text-[12px] uppercase tracking-widest" style={{ color: c.accent }}>
              {ev.label}
            </div>
            <div className="mt-1 text-[15px] leading-relaxed" style={{ color: c.primary }}>
              {ev.value}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
