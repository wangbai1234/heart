import { describe, expect, it } from 'vitest'
import { buildCharacterHeatMap } from './characterHeat'

describe('buildCharacterHeatMap', () => {
  it('uses real counts for every user-created character, including historical ones', () => {
    const heat = buildCharacterHeatMap(
      [
        { id: 'system-role', isBuiltin: true, chatUserCount: 2 },
        { id: 'old-user-role', isBuiltin: false, chatUserCount: 7 },
        { id: 'new-user-role', isBuiltin: false },
      ],
      new Map([['system-role', 6388]]),
    )

    expect(heat.get('system-role')).toBe(6388)
    expect(heat.get('old-user-role')).toBe(7)
    expect(heat.get('new-user-role')).toBe(0)
  })

  it('never exposes a negative real count', () => {
    const heat = buildCharacterHeatMap(
      [{ id: 'user-role', isBuiltin: false, chatUserCount: -5 }],
      new Map(),
    )
    expect(heat.get('user-role')).toBe(0)
  })
})
