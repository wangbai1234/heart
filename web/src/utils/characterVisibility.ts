export interface DiscoverableCharacter {
  isBuiltin: boolean
  isOwner: boolean
  visibility?: string
  reviewStatus?: string
  companion?: { companion_status?: string } | null
}

/**
 * Decide whether a character belongs in the normal discovery lists.
 *
 * An owner must never lose sight of a character they just created: quick
 * characters default to private, while workshop characters can spend time in
 * pending review. Both are still the creator's characters and remain visible
 * to that creator. Other users only see public, approved characters unless an
 * existing companion relationship already grants continuity.
 */
export function isDiscoverableCharacter(character: DiscoverableCharacter): boolean {
  if (character.isBuiltin || character.isOwner) return true
  if (character.visibility === 'public' && character.reviewStatus === 'approved') return true
  return Boolean(
    character.companion && character.companion.companion_status !== 'locked',
  )
}
