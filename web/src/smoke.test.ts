import { describe, expect, it } from 'vitest'

// Smoke test: proves the vitest runner is wired into CI (scripts/ci.sh
// stage_frontend). Real behavioral tests (e.g. storyBubbles.test.ts) land in
// the parser-fix PR; this file only guarantees `npx vitest run` executes.
describe('vitest runner', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
