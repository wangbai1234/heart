import { blockColors, type BlockProps } from './types'

/** 大字引文：serif 独白，左侧超大引号作装饰。newline 用 pre-wrap 保留。 */
export function QuoteBlock({ block, chrome }: BlockProps<{ type: 'quote'; text: string; attribution?: string }>) {
  const c = blockColors(chrome)
  return (
    <figure className="relative py-1">
      <span
        className="pointer-events-none absolute -left-1 -top-6 select-none text-[64px] leading-none"
        style={{ color: c.accent, opacity: 0.18, fontFamily: 'Georgia, serif' }}
        aria-hidden
      >
        &ldquo;
      </span>
      <blockquote
        className="relative whitespace-pre-wrap pl-6 text-[19px] font-light italic leading-[1.7]"
        style={{ color: c.primary, fontFamily: 'var(--font-serif, Georgia, serif)' }}
      >
        {block.text}
      </blockquote>
      {block.attribution && (
        <figcaption className="mt-3 pl-6 text-[13px] tracking-wide" style={{ color: c.muted }}>
          — {block.attribution}
        </figcaption>
      )}
    </figure>
  )
}
