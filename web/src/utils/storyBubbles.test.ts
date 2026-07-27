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

// These vectors MUST match backend/tests/unit/test_story_prompt.py
// (_split_npc_rest section). An inline （动作） on a **角色名** line splits into
// its own action bubble instead of being embedded in the dialogue bubble.
describe('splitGmText **角色名** inline action', () => {
  it('speaker + inline action + dialogue → action then dialogue', () => {
    const out = splitGmText('**贺听澜**（他缓缓走近你）“你来了。”')
    expect(out).toHaveLength(2)
    expect(out[0]).toEqual({ kind: 'action', npcName: null, content: '他缓缓走近你' })
    expect(out[1]).toEqual({ kind: 'dialogue', npcName: '贺听澜', content: '你来了。' })
  })

  it('speaker + action + bare 台词', () => {
    const out = splitGmText('**贺听澜** （目光扫过你）今晚别走。')
    expect(out.map((b) => b.kind)).toEqual(['action', 'dialogue'])
    expect(out[0].content).toBe('目光扫过你')
    expect(out[1].npcName).toBe('贺听澜')
    expect(out[1].content).toBe('今晚别走。')
  })

  it('dialogue → action → dialogue order preserved, name carried on 台词', () => {
    const out = splitGmText('**林**你来了。（转身离开）还是算了。')
    expect(out.map((b) => b.kind)).toEqual(['dialogue', 'action', 'dialogue'])
    expect(out[0]).toEqual({ kind: 'dialogue', npcName: '林', content: '你来了。' })
    expect(out[1].content).toBe('转身离开')
    expect(out[2]).toEqual({ kind: 'dialogue', npcName: '林', content: '还是算了。' })
  })
})
