import { create } from 'zustand'
import {
  getCharacters,
  getCharacterProfile,
  createCharacter as apiCreateCharacter,
  updateCharacter as apiUpdateCharacter,
  setCharacterVisibility as apiSetVisibility,
  disableCharacter as apiDisableCharacter,
  type CharacterDTO,
  type CharacterDraftDTO,
  type CharacterProfileDTO,
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

  // Per-id profile cache for /character/:id. Mirrors storyStore.detailById so a
  // re-entry is instant (no ~1s spinner). System characters never change their
  // cover/copy; a user editing their own character re-fetches via force=true
  // (createCharacter / updateCharacter clear the affected entry below).
  profileById: Record<string, CharacterProfileDTO>
  loadProfile: (id: string, force?: boolean) => Promise<CharacterProfileDTO | null>

  // UGC actions — each calls the API and then force-reloads the catalog.
  createCharacter: (draft: CharacterDraftDTO) => Promise<{ id: string; display_name: string }>
  updateCharacter: (id: string, draft: CharacterDraftDTO) => Promise<void>
  setVisibility: (id: string, visibility: 'public' | 'unlisted' | 'private') => Promise<void>
  disableCharacter: (id: string) => Promise<void>
}

// Deduplicate concurrent / repeated loads across the app.
let inflight: Promise<void> | null = null
// Per-id inflight dedup for profile fetches (two components mounting the same
// /character/:id at once share one request).
const profileInflight: Record<string, Promise<CharacterProfileDTO | null>> = {}

export const useCharactersStore = create<CharactersState>((set, get) => ({
  characters: [],
  loaded: false,
  loading: false,
  profileById: {},

  loadProfile: async (id, force = false) => {
    const cached = get().profileById[id]
    if (cached && !force) return cached
    const pending = profileInflight[id]
    if (pending) return pending
    const req = getCharacterProfile(id)
      .then((profile) => {
        set((s) => ({ profileById: { ...s.profileById, [id]: profile } }))
        return profile
      })
      .catch(() => null)
      .finally(() => {
        delete profileInflight[id]
      })
    profileInflight[id] = req
    return req
  },

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
    // Drop the stale profile so /character/:id re-fetches the edited cover/copy.
    set((s) => {
      const next = { ...s.profileById }
      delete next[id]
      return { profileById: next }
    })
    await get().load(true)
  },

  setVisibility: async (id, visibility) => {
    await apiSetVisibility(id, visibility)
    // Drop the cached profile so a re-open reflects the new visibility/review
    // state instead of a stale snapshot.
    set((s) => {
      const next = { ...s.profileById }
      delete next[id]
      return { profileById: next }
    })
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
