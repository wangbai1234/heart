import { create } from 'zustand'
import {
  getScenarios,
  getStoryGenres,
  getScenario,
  getActiveRun as apiGetActiveRun,
  unlockScenario as apiUnlockScenario,
  startRun as apiStartRun,
  getRun as apiGetRun,
  type ScenarioCardDTO,
  type ScenarioDetailDTO,
  type StoryBubbleDTO,
  type StoryRunDTO,
  type StoryKind,
  type StoryRole,
} from '../services/api'

/**
 * A single rendered story bubble in the player transcript.
 *
 * `id` is stable within a run (persisted seq-backed id, or a synthetic one for
 * opening/optimistic bubbles). The live streaming bubble uses the sentinel id
 * STREAM_ID and is dropped once the server's split `message_bubble` frames land.
 */
export interface StoryMessageVM {
  id: string
  turnId: string | null
  seq: number
  role: StoryRole
  kind: StoryKind
  npcName: string | null
  content: string
}

export const STREAM_ID = '__stream__'

let synthSeq = -1
function bubbleToVM(b: StoryBubbleDTO): StoryMessageVM {
  return {
    id: b.id ?? `synth-${synthSeq--}`,
    turnId: b.turn_id,
    seq: b.seq ?? synthSeq,
    role: b.role ?? (b.kind === 'dialogue' ? 'npc' : 'gm'),
    kind: b.kind,
    npcName: b.npc_name,
    content: b.content,
  }
}

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
  featuredScenarios: ScenarioCardDTO[]  // 独立的推荐区剧情（不受分类筛选影响）
  genres: Array<{ genre: string; count: number }>
  activeGenre: string | null
  loading: boolean
  loaded: boolean
  error: boolean

  detailById: Record<string, ScenarioDetailDTO>
  detailLoading: boolean
  detailError: boolean

  // Prior active run per scenario (resume vs restart CTA on the detail page).
  // undefined = not yet checked; null = checked, no active run.
  activeRunByScenario: Record<string, StoryRunDTO | null>

  // ── Run / player state (PR4) ──────────────────────────────────────
  runMetaById: Record<string, StoryRunDTO>
  messagesByRun: Record<string, StoryMessageVM[]>
  // Live delta accumulation for the in-flight GM turn; null = no live buffer.
  streamTextByRun: Record<string, string | null>
  generatingByRun: Record<string, boolean>
  // Set when the server reports 余额不足 for a run's per-minute billing: the
  // player page freezes input and shows a recharge prompt until top-up.
  pausedByRun: Record<string, boolean>
  runLoading: boolean
  runError: boolean

  loadCatalog: (force?: boolean) => Promise<void>
  setGenre: (genre: string | null) => Promise<void>
  loadScenario: (id: string, force?: boolean) => Promise<ScenarioDetailDTO | null>
  loadActiveRun: (scenarioId: string, force?: boolean) => Promise<StoryRunDTO | null>
  // Permanently unlock (pay for) a scenario; updates the detail cache on success.
  unlockScenario: (scenarioId: string) => Promise<{ ok: boolean; balance: number }>

  // Per-minute billing pause (set from useStoryWebSocket on insufficient_credits)
  setPaused: (runId: string, paused: boolean) => void

  // Run lifecycle
  startRun: (
    scenarioId: string,
    playerIdentity: Record<string, unknown>,
  ) => Promise<StoryRunDTO>
  loadRun: (runId: string, force?: boolean) => Promise<void>

  // WS-driven turn mutations (called from useStoryWebSocket)
  appendPlayerMessage: (runId: string, text: string, turnId: string) => void
  beginTurn: (runId: string) => void
  appendDelta: (runId: string, delta: string) => void
  commitBubble: (runId: string, bubble: StoryBubbleDTO) => void
  endTurn: (runId: string) => void
}

let catalogInflight: Promise<void> | null = null

async function fetchCatalog(
  set: (partial: Partial<StoryState>) => void,
  get: () => StoryState,
): Promise<void> {
  set({ loading: true, error: false })
  try {
    const genre = get().activeGenre
    // 推荐区独立查询 featured=true，不受分类筛选影响
    // 剧情网格查询当前分类（排除 featured，避免重复显示）
    const [{ scenarios: featured }, { scenarios }, { genres }] = await Promise.all([
      getScenarios({ featured: true, limit: 10 }),
      getScenarios(genre ? { genre, limit: 60 } : { limit: 60 }),
      getStoryGenres(),
    ])
    set({ featuredScenarios: featured, scenarios, genres, loaded: true, loading: false })
  } catch {
    set({ loading: false, error: true })
  }
}

export const useStoryStore = create<StoryState>((set, get) => ({
  scenarios: [],
  featuredScenarios: [],
  genres: [],
  activeGenre: null,
  loading: false,
  loaded: false,
  error: false,

  detailById: {},
  detailLoading: false,
  detailError: false,

  activeRunByScenario: {},

  runMetaById: {},
  messagesByRun: {},
  streamTextByRun: {},
  generatingByRun: {},
  pausedByRun: {},
  runLoading: false,
  runError: false,

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
    // 推荐区（featuredScenarios）保持不变，只重新查询分类网格
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

  loadActiveRun: async (scenarioId, force = false) => {
    const cached = get().activeRunByScenario[scenarioId]
    if (cached !== undefined && !force) return cached
    try {
      const { run } = await apiGetActiveRun(scenarioId)
      set((s) => ({ activeRunByScenario: { ...s.activeRunByScenario, [scenarioId]: run } }))
      return run
    } catch {
      // Best-effort: on failure leave it unchecked so the CTA falls back to
      // "开始剧情" (a first-time-play affordance is the safe default).
      return null
    }
  },

  unlockScenario: async (scenarioId) => {
    const res = await apiUnlockScenario(scenarioId)
    // Reflect the unlock in the detail cache so the CTA flips to 开始剧情
    // without a refetch. Leaves other detail fields untouched.
    set((s) => {
      const cached = s.detailById[scenarioId]
      if (!cached) return {}
      return { detailById: { ...s.detailById, [scenarioId]: { ...cached, unlocked: true } } }
    })
    return { ok: res.ok, balance: res.balance }
  },

  setPaused: (runId, paused) => {
    set((s) => ({ pausedByRun: { ...s.pausedByRun, [runId]: paused } }))
  },

  // ── Run lifecycle ─────────────────────────────────────────────────

  startRun: async (scenarioId, playerIdentity) => {
    const { run, opening_bubbles } = await apiStartRun(scenarioId, playerIdentity)
    // Seed the transcript with the opening GM bubbles so the player page has
    // content immediately (no extra round-trip before the first turn). The
    // fresh run is now this scenario's active run (the server retired any prior
    // one), so update the resume cache to point at it.
    set((s) => ({
      runMetaById: { ...s.runMetaById, [run.run_id]: run },
      messagesByRun: { ...s.messagesByRun, [run.run_id]: opening_bubbles.map(bubbleToVM) },
      streamTextByRun: { ...s.streamTextByRun, [run.run_id]: null },
      generatingByRun: { ...s.generatingByRun, [run.run_id]: false },
      activeRunByScenario: { ...s.activeRunByScenario, [scenarioId]: run },
    }))
    return run
  },

  loadRun: async (runId, force = false) => {
    // Already hydrated (e.g. just started) — don't clobber live state.
    if (!force && get().messagesByRun[runId]) return
    set({ runLoading: true, runError: false })
    try {
      const { run, messages } = await apiGetRun(runId)
      set((s) => ({
        runMetaById: { ...s.runMetaById, [runId]: run },
        messagesByRun: { ...s.messagesByRun, [runId]: messages.map(bubbleToVM) },
        streamTextByRun: { ...s.streamTextByRun, [runId]: null },
        runLoading: false,
      }))
    } catch {
      set({ runLoading: false, runError: true })
    }
  },

  // ── WS-driven turn mutations ──────────────────────────────────────

  appendPlayerMessage: (runId, text, turnId) => {
    set((s) => ({
      messagesByRun: {
        ...s.messagesByRun,
        [runId]: [
          ...(s.messagesByRun[runId] ?? []),
          {
            id: `player-${turnId}`,
            turnId,
            seq: Number.MAX_SAFE_INTEGER,
            role: 'player',
            kind: 'narration',
            npcName: null,
            content: text,
          },
        ],
      },
    }))
  },

  beginTurn: (runId) => {
    set((s) => ({
      generatingByRun: { ...s.generatingByRun, [runId]: true },
      streamTextByRun: { ...s.streamTextByRun, [runId]: '' },
    }))
  },

  appendDelta: (runId, delta) => {
    set((s) => ({
      streamTextByRun: {
        ...s.streamTextByRun,
        [runId]: (s.streamTextByRun[runId] ?? '') + delta,
      },
    }))
  },

  commitBubble: (runId, bubble) => {
    // First committed bubble of the turn retires the live streaming buffer:
    // the server has now sent the properly-split bubbles for the same text.
    set((s) => ({
      streamTextByRun: { ...s.streamTextByRun, [runId]: null },
      generatingByRun: { ...s.generatingByRun, [runId]: false },
      messagesByRun: {
        ...s.messagesByRun,
        [runId]: [...(s.messagesByRun[runId] ?? []), bubbleToVM(bubble)],
      },
    }))
  },

  endTurn: (runId) => {
    set((s) => {
      const meta = s.runMetaById[runId]
      return {
        generatingByRun: { ...s.generatingByRun, [runId]: false },
        streamTextByRun: { ...s.streamTextByRun, [runId]: null },
        runMetaById: meta
          ? { ...s.runMetaById, [runId]: { ...meta, turn_count: meta.turn_count + 1 } }
          : s.runMetaById,
      }
    })
  },
}))
