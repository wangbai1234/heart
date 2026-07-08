import { create } from 'zustand'
import type { ProactiveMessageDTO } from '../services/api'

interface ProactiveState {
  /** IDs already ingested this session, to avoid duplicates on repeated polls. */
  seenIds: Set<string>
  /** Pending proactive messages per character — drives the inbox unread badge. */
  pendingByChar: Record<string, ProactiveMessageDTO[]>
  /** Add newly-polled messages (deduped by id). Returns the ones actually added. */
  ingest: (messages: ProactiveMessageDTO[]) => ProactiveMessageDTO[]
  /** Remove and return the pending messages for a character (called on open). */
  drain: (characterId: string) => ProactiveMessageDTO[]
  reset: () => void
}

/**
 * Holds proactive messages surfaced by the SS06 Inner Loop until the user opens
 * the corresponding conversation. Kept separate from chatStore so the inbox
 * badge is additive and does NOT suppress chat-history loading (which only runs
 * when a character's live message list is empty).
 *
 * The durable dedup is the backend `/ack` (delivered messages are not
 * re-served); `seenIds` guards against double-injection within a session.
 */
export const useProactiveStore = create<ProactiveState>((set, get) => ({
  seenIds: new Set<string>(),
  pendingByChar: {},
  ingest: (messages) => {
    const seen = get().seenIds
    const fresh = messages.filter((m) => !seen.has(m.id))
    if (fresh.length === 0) return []

    const nextSeen = new Set(seen)
    const nextPending: Record<string, ProactiveMessageDTO[]> = { ...get().pendingByChar }
    for (const m of fresh) {
      nextSeen.add(m.id)
      nextPending[m.character_id] = [...(nextPending[m.character_id] ?? []), m]
    }
    set({ seenIds: nextSeen, pendingByChar: nextPending })
    return fresh
  },
  drain: (characterId) => {
    const pending = get().pendingByChar[characterId] ?? []
    if (pending.length === 0) return []
    const nextPending = { ...get().pendingByChar }
    delete nextPending[characterId]
    set({ pendingByChar: nextPending })
    return pending
  },
  reset: () => set({ seenIds: new Set<string>(), pendingByChar: {} }),
}))
