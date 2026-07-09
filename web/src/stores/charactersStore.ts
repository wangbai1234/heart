import { create } from 'zustand'
import {
  getCharacters,
  createCharacter as apiCreateCharacter,
  updateCharacter as apiUpdateCharacter,
  setCharacterVisibility as apiSetVisibility,
  disableCharacter as apiDisableCharacter,
  type CharacterDTO,
  type CharacterDraftDTO,
} from '../services/api'
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
 *
 * C5b extension: UGC CRUD actions (createCharacter, updateCharacter,
 * setVisibility, disableCharacter) mutate the catalog and re-fetch in one step.
 */
interface CharactersState {
  characters: CharacterDTO[]
  loaded: boolean
  loading: boolean
  load: (force?: boolean) => Promise<void>

  // UGC actions — each calls the API and then force-reloads the catalog.
  createCharacter: (draft: CharacterDraftDTO) => Promise<{ id: string; display_name: string }>
  updateCharacter: (id: string, draft: CharacterDraftDTO) => Promise<void>
  setVisibility: (id: string, visibility: 'public' | 'unlisted' | 'private') => Promise<void>
  disableCharacter: (id: string) => Promise<void>
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

  createCharacter: async (draft) => {
    const result = await apiCreateCharacter(draft)
    await get().load(true)
    return { id: result.id, display_name: result.display_name }
  },

  updateCharacter: async (id, draft) => {
    await apiUpdateCharacter(id, draft)
    await get().load(true)
  },

  setVisibility: async (id, visibility) => {
    await apiSetVisibility(id, visibility)
    await get().load(true)
  },

  disableCharacter: async (id) => {
    await apiDisableCharacter(id)
    await get().load(true)
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
