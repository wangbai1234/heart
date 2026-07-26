import { describe, expect, it } from 'vitest'

import { reconcileTranscript, type StoryMessageVM } from './storyStore'

// The "剧情消失" resume fix: the transcript store is in-memory, so on re-entry
// loadRun must reconcile with the authoritative server transcript instead of
// keeping stale client state — while never wiping a turn that's still in flight.
// reconcileTranscript is that merge; these lock its two branches.

function vm(partial: Partial<StoryMessageVM> & { seq: number }): StoryMessageVM {
  return {
    id: `id-${partial.seq}`,
    turnId: null,
    role: 'gm',
    kind: 'narration',
    npcName: null,
    content: `c${partial.seq}`,
    ...partial,
  }
}

describe('reconcileTranscript', () => {
  it('not generating → replaces client state with the server transcript', () => {
    // A turn the client never saw (persisted server-side while away) must appear.
    const current = [vm({ seq: 1 })]
    const server = [vm({ seq: 1 }), vm({ seq: 2 }), vm({ seq: 3 })]
    expect(reconcileTranscript(current, server, false)).toEqual(server)
  })

  it('not generating → server truth wins even when client had more', () => {
    const current = [vm({ seq: 1 }), vm({ seq: 2 })]
    const server = [vm({ seq: 1 })]
    expect(reconcileTranscript(current, server, true).slice(0, 1)).toEqual(server)
  })

  it('generating → keeps the optimistic player line the server has not returned', () => {
    const player = vm({
      seq: Number.MAX_SAFE_INTEGER,
      role: 'player',
      turnId: 'turn-A',
      content: 'my move',
    })
    const current = [vm({ seq: 1 }), player]
    const server = [vm({ seq: 1 })] // server hasn't persisted turn-A yet
    const out = reconcileTranscript(current, server, true)
    expect(out).toHaveLength(2)
    expect(out[1]).toEqual(player)
  })

  it('generating → keeps live streamed bubbles (synthetic negative seq)', () => {
    const live = vm({ seq: -3, turnId: null, content: '…streaming' })
    const out = reconcileTranscript([vm({ seq: 1 }), live], [vm({ seq: 1 })], true)
    expect(out.map((m) => m.seq)).toEqual([1, -3])
  })

  it('generating → drops an optimistic line once the server returns its turn', () => {
    // Server has now persisted turn-A: the optimistic copy must not duplicate.
    const player = vm({
      seq: Number.MAX_SAFE_INTEGER,
      role: 'player',
      turnId: 'turn-A',
    })
    const current = [player]
    const server = [vm({ seq: 5, role: 'player', turnId: 'turn-A' })]
    const out = reconcileTranscript(current, server, true)
    expect(out).toEqual(server)
  })
})
