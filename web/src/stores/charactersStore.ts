import { create } from 'zustand'
import { getCharacters, type CharacterDTO } from '../services/api'
import { CHARACTER_PROFILES } from '../data/uiContent'

/**
 * Runtime source of truth for *which characters exist* (UGC refactor C4).
 *
 * Replaces the hardcoded `CharacterId = 'rin' | 'dorothy'` union: the list now
 * comes from `GET /api/characters`, so a new server-side character shows up in
 * the UI without a frontend change. Visual assets (avatar / colors) are still
 * resolved locally via resolveCharacterProfile — only the *catalog* is dynamic.
 *
 * Fallback: until the catalog loads (or if the request fails), consumers fall
 * back to the built-in profiles so cold-start / offline never yields an empty
 * character list.
 */
interface CharactersState {
  characters: CharacterDTO[]
  loaded: boolean
  loading: boolean
  load: (force?: boolean) => Promise<void>
}

// Deduplicate concurrent / repeated loads across the app.
let inflight: Promise<void> | null = null

export const useCharactersStore = create<CharactersState>((set, get) => ({
  characters: [],
  loaded: false,
  loading: false,

  load: async (force = false) => {
    if (!force && (get().loaded || get().loading)) return
    if (inflight) return inflight

    set({ loading: true })
    inflight = getCharacters()
      .then(({ characters }) => {
        set({ characters, loaded: true, loading: false })
      })
      .catch(() => {
        // Keep whatever we have; consumers fall back to CHARACTER_PROFILES.
        set({ loading: false })
      })
      .finally(() => {
        inflight = null
      })
    return inflight
  },
}))

/**
 * The character ids currently known to the UI: the loaded server catalog, or
 * the built-in profiles as a fallback. Used for route-boundary validation so an
 * unknown `/chat/:id` can be rejected before it reaches the backend.
 */
export function knownCharacterIds(): Set<string> {
  const { characters } = useCharactersStore.getState()
  if (characters.length > 0) return new Set(characters.map((c) => c.id))
  return new Set(Object.keys(CHARACTER_PROFILES))
}

export function isKnownCharacterId(id: string): boolean {
  return knownCharacterIds().has(id)
}

/** Server-authoritative display name for an id, if the catalog is loaded. */
export function serverDisplayName(id: string): string | undefined {
  return useCharactersStore.getState().characters.find((c) => c.id === id)?.display_name
}
