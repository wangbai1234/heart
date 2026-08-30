import { create } from 'zustand'
import { getCompanions, type CompanionDTO } from '../services/api'

/**
 * Runtime source of truth for the bond-center companion list (GET /api/companions).
 *
 * Kept separate from charactersStore: charactersStore owns the raw character
 * catalog (UGC CRUD, visibility), this store owns the aggregated
 * relationship/inbox/proactive view used by the bond center UI. The backend
 * already sorts by unread/proactive → recency → intimacy; consumers should
 * not re-sort.
 */
interface CompanionsState {
  companions: CompanionDTO[]
  loaded: boolean
  loading: boolean
  load: (force?: boolean) => Promise<void>
  reset: () => void
}

let inflight: Promise<void> | null = null
// A forced refresh requested while an older request is in flight must run
// once more after that request settles; otherwise quick creation can reuse a
// pre-create companion snapshot and hide the initial intimacy state.
let forcedRefresh: Promise<void> | null = null
let catalogGeneration = 0

export const useCompanionsStore = create<CompanionsState>((set, get) => ({
  companions: [],
  loaded: false,
  loading: false,

  reset: () => {
    catalogGeneration += 1
    set({ companions: [], loaded: false, loading: false })
  },

  load: async (force = false) => {
    if (!force && (get().loaded || get().loading)) return
    if (force && forcedRefresh) return forcedRefresh
    if (force && inflight) {
      const current = inflight
      let refresh: Promise<void>
      refresh = current.then(
        () => {
          if (forcedRefresh === refresh) forcedRefresh = null
          return get().load(true)
        },
        () => {
          if (forcedRefresh === refresh) forcedRefresh = null
          return get().load(true)
        },
      )
      forcedRefresh = refresh
      return refresh
    }
    if (inflight) return inflight

    const requestGeneration = catalogGeneration
    set({ loading: true })
    inflight = getCompanions()
      .then(({ companions }) => {
        if (requestGeneration !== catalogGeneration) return
        set({ companions, loaded: true, loading: false })
      })
      .catch(() => {
        if (requestGeneration !== catalogGeneration) return
        set({ loading: false })
      })
      .finally(() => {
        inflight = null
      })
    return inflight
  },
}))
