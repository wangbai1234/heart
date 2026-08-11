import { blockColors, type BlockProps } from './types'

/** 档案表：身份档案 / 病历卡质感。左侧 accent 竖条 + label/value 对。 */
export function DossierBlock({ block, chrome }: BlockProps<{ type: 'dossier'; title: string; rows: { label: string; value: string }[] }>) {
  const c = blockColors(chrome)
  return (
    <section className="relative pl-4">
      <span
        className="absolute left-0 top-1 bottom-1 w-[2px] rounded-full"
        style={{ background: c.accent, opacity: 0.55 }}
        aria-hidden
      />
      <h3
        className="mb-3 text-[13px] font-medium uppercase tracking-[0.18em]"
        style={{ color: c.accent, fontFamily: 'var(--font-serif, Georgia, serif)' }}
      >
        {block.title}
      </h3>
      <dl className="space-y-2.5">
        {block.rows.map((row, i) => (
          <div key={i} className="flex gap-4 text-[15px] leading-relaxed">
            <dt className="w-[5.5rem] shrink-0 text-[13px]" style={{ color: c.muted }}>
              {row.label}
            </dt>
            <dd className="flex-1" style={{ color: c.primary }}>
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
