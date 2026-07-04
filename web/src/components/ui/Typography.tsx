import type { ReactNode } from 'react'

interface TypographyProps {
  variant: 'display' | 'title' | 'headline' | 'body' | 'caption' | 'overline' | 'brand' | 'tagline'
  children: ReactNode
  className?: string
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span'
}

const styles = {
  display: 'text-[36px] font-bold leading-tight tracking-tight',
  title: 'text-[18px] font-medium leading-normal',
  headline: 'text-[16px] font-semibold leading-normal',
  body: 'text-[15px] font-normal leading-relaxed',
  caption: 'text-[13px] font-normal leading-normal',
  overline: 'text-[12px] font-normal leading-normal tracking-wider',
  brand: 'text-[36px] font-bold leading-none tracking-tight font-[var(--font-latin)]',
  tagline: 'text-[14px] font-normal leading-normal tracking-[0.12em]',
}

const tags = {
  display: 'h1',
  title: 'h2',
  headline: 'h3',
  body: 'p',
  caption: 'span',
  overline: 'span',
  brand: 'span',
  tagline: 'p',
} as const

export function Typography({ variant, children, className = '', as }: TypographyProps) {
  const Tag = as || tags[variant]
  return (
    <Tag className={`${styles[variant]} text-[var(--color-ink)] ${className}`}>
      {children}
    </Tag>
  )
}
