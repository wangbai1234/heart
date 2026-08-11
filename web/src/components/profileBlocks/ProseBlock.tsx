import { blockColors, type BlockProps } from './types'

/** 纯文本段落：可选标题 + 正文。newline 用 pre-wrap 保留。 */
export function ProseBlock({ block, chrome }: BlockProps<{ type: 'prose'; title?: string; text: string }>) {
  const c = blockColors(chrome)
  return (
    <section>
      {block.title && (
        <h3
          className="mb-3 text-[13px] font-medium uppercase tracking-[0.18em]"
          style={{ color: c.accent, fontFamily: 'var(--font-serif, Georgia, serif)' }}
        >
          {block.title}
        </h3>
      )}
      <p
        className="whitespace-pre-wrap text-[15px] leading-[1.85]"
        style={{ color: c.primary }}
      >
        {block.text}
      </p>
    </section>
  )
}
