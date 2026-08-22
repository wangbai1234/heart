import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { MaskDeleteDialog } from './MaskSheet'

describe('MaskDeleteDialog', () => {
  it('shows the mask name, deletion impact, and explicit actions', () => {
    const html = renderToStaticMarkup(
      <MaskDeleteDialog
        mask={{ id: 'mask-1', name: '雨夜旅人' }}
        busy={false}
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    expect(html).toContain('role="dialog"')
    expect(html).toContain('删除这个面具？')
    expect(html).toContain('雨夜旅人')
    expect(html).toContain('删除后会从所有已绑定角色中解绑，面具设定将无法恢复。')
    expect(html).toContain('取消')
    expect(html).toContain('确认删除')
  })

  it('shows progress while deletion is running', () => {
    const html = renderToStaticMarkup(
      <MaskDeleteDialog
        mask={{ id: 'mask-1', name: '雨夜旅人' }}
        busy
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    expect(html).toContain('删除中…')
    expect(html).toContain('disabled=""')
  })
})
