import { describe, expect, it } from 'vitest'
import { buildCharacterHeatMap } from './characterHeat'

describe('buildCharacterHeatMap', () => {
  it('uses persisted server heat for every character', () => {
    const heat = buildCharacterHeatMap(
      [
        { id: 'system-role', displayHeat: 6388 },
        { id: 'user-role', displayHeat: 307 },
      ],
    )

    expect(heat.get('system-role')).toBe(6388)
    expect(heat.get('user-role')).toBe(307)
  })

  it('never exposes a negative heat value', () => {
    const heat = buildCharacterHeatMap(
      [{ id: 'user-role', displayHeat: -5 }],
    )
    expect(heat.get('user-role')).toBe(0)
  })
})
