import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Markdown from 'react-markdown'

export function LegalPage() {
  const { type } = useParams<{ type: string }>()
  const navigate = useNavigate()
  const [content, setContent] = useState('')

  useEffect(() => {
    const file = type === 'privacy' ? 'privacy.md' : 'terms.md'
    fetch(`/legal/${file}`)
      .then((r) => r.text())
      .then((text) => {
        // Strip HTML comments (internal notes that shouldn't be rendered)
        setContent(text.replace(/<!--[\s\S]*?-->/g, ''))
      })
      .catch(() => setContent('加载失败'))
  }, [type])

  const title = type === 'privacy' ? '隐私政策' : '用户协议'

  return (
    <div className="w-full h-full flex flex-col" style={{ background: 'var(--color-bg)' }}>
      <div className="flex items-center px-5 pt-4 pb-3" style={{ paddingTop: 'var(--safe-top)' }}>
        <button onClick={() => navigate(-1 as any)} className="text-[var(--color-ink)] text-[14px] active:opacity-60">← 返回</button>
        <h2 className="flex-1 text-center text-[17px] font-semibold text-[var(--color-ink)] pr-10">{title}</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-5 pb-8">
        <div className="prose prose-sm max-w-none legal-content">
          <Markdown
            components={{
              h1: ({ children }) => <h1 className="text-[22px] font-bold mt-6 mb-3 text-[var(--color-ink)]">{children}</h1>,
              h2: ({ children }) => <h2 className="text-[17px] font-semibold mt-5 mb-2 text-[var(--color-ink)]">{children}</h2>,
              p: ({ children }) => <p className="text-[13px] leading-[1.8] text-[var(--color-text-secondary)] my-1">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold text-[var(--color-ink)]">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              ul: ({ children }) => <ul className="list-disc pl-5 my-2 text-[13px] leading-[1.8] text-[var(--color-text-secondary)]">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 my-2 text-[13px] leading-[1.8] text-[var(--color-text-secondary)]">{children}</ol>,
              li: ({ children }) => <li className="my-1">{children}</li>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-[var(--color-primary)] pl-4 my-2 text-[13px] text-[var(--color-text-secondary)] italic">
                  {children}
                </blockquote>
              ),
              hr: () => <hr className="my-4 border-[var(--color-divider-inset)]" />,
              a: ({ href, children }) => (
                <a href={href} className="text-[var(--color-primary)] underline">{children}</a>
              ),
            }}
          >
            {content}
          </Markdown>
        </div>
      </div>
      <div style={{ height: 'var(--safe-bottom)' }} />
    </div>
  )
}
