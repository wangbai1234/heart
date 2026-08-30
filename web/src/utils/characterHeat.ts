export interface CharacterHeatInput {
  id: string
  isBuiltin: boolean
  chatUserCount?: number
}

/**
 * System-authored roles may use editorial heat; user-authored roles always use
 * the real distinct-chat-user count supplied by the backend.
 */
export function buildCharacterHeatMap(
  rankedItems: CharacterHeatInput[],
  editorialOverrides: ReadonlyMap<string, number>,
): Map<string, number> {
  const map = new Map<string, number>()
  const systemItems = rankedItems.filter((item) => item.isBuiltin)
  const systemRank = new Map(systemItems.map((item, index) => [item.id, index]))
  const systemCount = systemItems.length

  rankedItems.forEach((item) => {
    if (!item.isBuiltin) {
      map.set(item.id, Math.max(0, item.chatUserCount ?? 0))
      return
    }

    const override = editorialOverrides.get(item.id)
    if (override !== undefined) {
      map.set(item.id, override)
      return
    }

    const rank = systemRank.get(item.id) ?? 0
    const virtual =
      systemCount <= 1 ? 2750 : Math.round(5000 - (rank / (systemCount - 1)) * 4500)
    map.set(item.id, virtual)
  })

  return map
}
