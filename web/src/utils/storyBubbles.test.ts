import { describe, expect, it } from 'vitest'

import { splitGmText } from './storyBubbles'

// These vectors MUST match backend/tests/unit/test_story_prompt.py
// (split_gm_text pending-speaker section). storyBubbles.ts is a behavioural
// port of the Python split_gm_text; vitest locks the two implementations to the
// same output so a future frontend edit can't silently drift.

describe('splitGmText pending-speaker (empty-oval regression)', () => {
  it('(a) bare speaker attaches the next prose line as 台词', () => {
    const out = splitGmText('**贺听澜**\n贺家不缺摆件，缺的是能扛事的人。')
    expect(out).toHaveLength(1)
    expect(out[0].kind).toBe('dialogue')
    expect(out[0].npcName).toBe('贺听澜')
    expect(out[0].content).toBe('贺家不缺摆件，缺的是能扛事的人。')
    // No empty-content bubble slipped through.
    expect(out.every((b) => b.content.trim() !== '')).toBe(true)
  })

  it('(b) bare speaker at end-of-text drops silently', () => {
    expect(splitGmText('**贺听澜**')).toEqual([])
  })

  it('(c) bare speaker dropped when followed by 【旁白】', () => {
    const out = splitGmText('**贺听澜**\n【旁白】夜色渐深。')
    expect(out).toHaveLength(1)
    expect(out[0].kind).toBe('narration')
    expect(out[0].npcName).toBeNull()
    expect(out[0].content).toContain('夜色渐深')
  })

  it('(d) same-line `**name** 台词` still works', () => {
    const out = splitGmText('**贺听澜** 你来了。')
    expect(out).toHaveLength(1)
    expect(out[0].kind).toBe('dialogue')
    expect(out[0].npcName).toBe('贺听澜')
    expect(out[0].content).toBe('你来了。')
  })

  it('(e) blank line between speaker and 台词 survives', () => {
    const out = splitGmText('**贺听澜**\n\n贺家不缺摆件。')
    expect(out).toHaveLength(1)
    expect(out[0].kind).toBe('dialogue')
    expect(out[0].npcName).toBe('贺听澜')
    expect(out[0].content).toBe('贺家不缺摆件。')
  })

  it('(f) consecutive bare speakers → first dropped', () => {
    const out = splitGmText('**甲**\n**乙** 台词')
    expect(out).toHaveLength(1)
    expect(out[0].kind).toBe('dialogue')
    expect(out[0].npcName).toBe('乙')
    expect(out[0].content).toBe('台词')
  })

  // Live-stream transient: while only the bare `**name**` has arrived, the
  // splitter returns [] so the caller shows TypingDots (no empty oval).
  it('(live) bare speaker mid-stream returns []', () => {
    expect(splitGmText('**贺听澜**')).toEqual([])
    expect(splitGmText('**贺听澜**\n')).toEqual([])
  })
})
