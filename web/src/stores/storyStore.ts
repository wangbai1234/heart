import { create } from 'zustand'
import {
  getScenarios,
  getStoryGenres,
  getScenario,
  type ScenarioCardDTO,
  type ScenarioDetailDTO,
} from '../services/api'

/**
 * Read-only catalog state for Story/剧情 mode (SS09), PR2 scope.
 *
 * Mirrors the charactersStore pattern: a cached list + genres for the Explore
 * page, plus a per-id detail cache for the detail page. Run lifecycle
 * (start/resume) and streaming state are added alongside the player UI (PR4).
 *
 * `genre` is the active filter chip (null = 全部). Changing it re-fetches the
 * grid. All fetches are best-effort: on failure we keep whatever we have and
 * surface `error` so the page can render an ErrorState with retry.
 */
interface StoryState {
  scenarios: ScenarioCardDTO[]
  genres: Array<{ genre: string; count: number }>
  activeGenre: string | null
  loading: boolean
  loaded: boolean
  error: boolean

  detailById: Record<string, ScenarioDetailDTO>
  detailLoading: boolean
  detailError: boolean

  loadCatalog: (force?: boolean) => Promise<void>
  setGenre: (genre: string | null) => Promise<void>
  loadScenario: (id: string, force?: boolean) => Promise<ScenarioDetailDTO | null>
}

let catalogInflight: Promise<void> | null = null

async function fetchCatalog(
  set: (partial: Partial<StoryState>) => void,
  get: () => StoryState,
): Promise<void> {
  set({ loading: true, error: false })
  try {
    const genre = get().activeGenre
    const [{ scenarios }, { genres }] = await Promise.all([
      getScenarios(genre ? { genre, limit: 60 } : { limit: 60 }),
      getStoryGenres(),
    ])
    set({ scenarios, genres, loaded: true, loading: false })
  } catch {
    set({ loading: false, error: true })
  }
}

export const useStoryStore = create<StoryState>((set, get) => ({
  scenarios: [],
  genres: [],
  activeGenre: null,
  loading: false,
  loaded: false,
  error: false,

  detailById: {},
  detailLoading: false,
  detailError: false,

  loadCatalog: async (force = false) => {
    if (!force && (get().loaded || get().loading)) return
    if (catalogInflight) return catalogInflight
    catalogInflight = fetchCatalog(set, get).finally(() => {
      catalogInflight = null
    })
    return catalogInflight
  },

  setGenre: async (genre) => {
    if (get().activeGenre === genre) return
    set({ activeGenre: genre })
    // Only the grid depends on the filter; refetch scenarios (genres are stable).
    set({ loading: true, error: false })
    try {
      const { scenarios } = await getScenarios(genre ? { genre, limit: 60 } : { limit: 60 })
      set({ scenarios, loading: false })
    } catch {
      set({ loading: false, error: true })
    }
  },

  loadScenario: async (id, force = false) => {
    const cached = get().detailById[id]
    if (cached && !force) return cached
    set({ detailLoading: true, detailError: false })
    try {
      const detail = await getScenario(id)
      set((s) => ({
        detailById: { ...s.detailById, [id]: detail },
        detailLoading: false,
      }))
      return detail
    } catch {
      set({ detailLoading: false, detailError: true })
      return null
    }
  },
}))
