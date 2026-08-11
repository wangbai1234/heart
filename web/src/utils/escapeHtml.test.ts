import { describe, expect, it } from 'vitest'

import { escapeHtml, escapeHtmlAllowBr } from './escapeHtml'

// escapeHtml 存在的唯一理由是 PremiseCardBase 把角色数据拼进 iframe srcDoc。
// UGC 角色创作会让用户编辑那些字段，所以注入向量必须被锁住。
// 见 docs/UGC_PRESENTATION_GAPS.md 第 3 节。

describe('escapeHtml', () => {
  it('中和 script 标签', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt;',
    )
  })

  it('转义引号，阻断属性逃逸', () => {
    expect(escapeHtml('" onerror="alert(1)')).toBe(
      '&quot; onerror=&quot;alert(1)',
    )
    expect(escapeHtml("' onload='x")).toBe('&#39; onload=&#39;x')
  })

  it('先转义 & 以免二次转义出错', () => {
    expect(escapeHtml('&lt;')).toBe('&amp;lt;')
  })

  it('普通中文文本原样通过', () => {
    expect(escapeHtml('江南雨夜，烛火摇曳。')).toBe('江南雨夜，烛火摇曳。')
  })

  it('空字符串安全', () => {
    expect(escapeHtml('')).toBe('')
  })
})

describe('escapeHtmlAllowBr', () => {
  // 全部 46 个内置 premise card 共 86 处 <br>，全在 note 字段，无其他标签。
  it('保留 <br> 的三种写法', () => {
    expect(escapeHtmlAllowBr('a<br>b')).toBe('a<br>b')
    expect(escapeHtmlAllowBr('a<br/>b')).toBe('a<br>b')
    expect(escapeHtmlAllowBr('a<br />b')).toBe('a<br>b')
  })

  it('大小写不限', () => {
    expect(escapeHtmlAllowBr('a<BR>b')).toBe('a<br>b')
  })

  it('放回 br 的同时仍拦住 script', () => {
    expect(escapeHtmlAllowBr('第一行<br><script>alert(1)</script>')).toBe(
      '第一行<br>&lt;script&gt;alert(1)&lt;/script&gt;',
    )
  })

  it('不放行其他标签', () => {
    expect(escapeHtmlAllowBr('<img src=x onerror=alert(1)>')).toBe(
      '&lt;img src=x onerror=alert(1)&gt;',
    )
    expect(escapeHtmlAllowBr('<b>粗</b>')).toBe('&lt;b&gt;粗&lt;/b&gt;')
  })

  it('不被 <brx> 之类近似标签骗过', () => {
    expect(escapeHtmlAllowBr('<brx>')).toBe('&lt;brx&gt;')
  })

  it('真实 note 内容（内置卡片格式）保持渲染', () => {
    const note = '人间烟火千万种，我独爱你眼里那一盏灯。<br>只此一盏。'
    expect(escapeHtmlAllowBr(note)).toBe(note)
  })
})
