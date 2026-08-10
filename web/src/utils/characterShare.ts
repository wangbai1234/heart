/**
 * Character share-link helpers.
 *
 * The share link is the canonical profile URL `<origin>/character/<id>`. Anyone
 * holding it can open a `public` or `unlisted`+`approved` character's profile
 * and start a chat (backend gate: GET /api/characters/:id/profile). The same
 * link opens in the browser for logged-out visitors and inside the installed
 * PWA for members via the in-app "打开分享链接" paste flow.
 */

// character_id shape mirrors the backend SoulSpec pattern: ^[a-z][a-z0-9_]*$
const CID_RE = /^[a-z][a-z0-9_]*$/

/** Build the shareable profile URL for a character. */
export function buildShareLink(characterId: string): string {
  return `${window.location.origin}/character/${characterId}`
}

/**
 * Extract a character_id from arbitrary pasted text — a full share URL, a
 * `/character/<id>` path fragment, or a bare id. Returns null when nothing
 * looks like a valid id, so the caller can surface a "链接无效" hint rather
 * than navigate to a dead route.
 */
export function parseCharacterId(raw: string): string | null {
  const text = (raw || '').trim()
  if (!text) return null

  // 1) Anything containing a /character/<id> segment (full URL or path).
  const pathMatch = text.match(/\/character\/([a-z][a-z0-9_]*)/i)
  if (pathMatch) {
    const id = pathMatch[1].toLowerCase()
    return CID_RE.test(id) ? id : null
  }

  // 2) A bare id pasted on its own.
  const bare = text.toLowerCase()
  if (CID_RE.test(bare)) return bare

  return null
}
