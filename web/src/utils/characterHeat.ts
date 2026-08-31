export interface CharacterHeatInput {
  id: string
  displayHeat?: number
}

/**
 * Cover heat is server-authoritative for both first-party and UGC characters.
 */
export function buildCharacterHeatMap(
  rankedItems: CharacterHeatInput[],
): Map<string, number> {
  const map = new Map<string, number>()
  rankedItems.forEach((item) => {
    map.set(item.id, Math.max(0, item.displayHeat ?? 0))
  })

  return map
}
