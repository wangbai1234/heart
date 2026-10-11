import { describe, expect, it } from 'vitest'

import { isDiscoverableCharacter } from './characterVisibility'

describe('isDiscoverableCharacter', () => {
  it("keeps the owner's private quick-created character visible", () => {
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: true,
      visibility: 'private',
      reviewStatus: 'not_required',
    })).toBe(true)
  })

  it("keeps the owner's pending workshop character visible", () => {
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: true,
      visibility: 'public',
      reviewStatus: 'pending',
    })).toBe(true)
  })

  it("hides another user's private or pending character", () => {
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: false,
      visibility: 'private',
      reviewStatus: 'not_required',
    })).toBe(false)
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: false,
      visibility: 'public',
      reviewStatus: 'pending',
    })).toBe(false)
  })

  it('shows public approved characters and existing companions', () => {
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: false,
      visibility: 'public',
      reviewStatus: 'approved',
    })).toBe(true)
    expect(isDiscoverableCharacter({
      isBuiltin: false,
      isOwner: false,
      visibility: 'private',
      reviewStatus: 'not_required',
      companion: { companion_status: 'active' },
    })).toBe(true)
  })
})

it('local selection admits approved unlisted but never private or pending owner entries', () => {
  const base = { localReview: true, isBuiltin: false, isOwner: true }
  expect(isDiscoverableCharacter({ ...base, visibility: 'unlisted', reviewStatus: 'approved' })).toBe(true)
  expect(isDiscoverableCharacter({ ...base, visibility: 'private', reviewStatus: 'approved' })).toBe(false)
  expect(isDiscoverableCharacter({ ...base, visibility: 'public', reviewStatus: 'pending' })).toBe(false)
})
