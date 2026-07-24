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
}

let inflight: Promise<void> | null = null

export const useCompanionsStore = create<CompanionsState>((set, get) => ({
  companions: [],
  loaded: false,
  loading: false,

  load: async (force = false) => {
    if (!force && (get().loaded || get().loading)) return
    if (inflight) return inflight

    set({ loading: true })
    inflight = getCompanions()
      .then(({ companions }) => {
        set({ companions, loaded: true, loading: false })
      })
      .catch(() => {
        set({ loading: false })
      })
      .finally(() => {
        inflight = null
      })
    return inflight
  },
}))
