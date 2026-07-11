import { useAuthStore } from '../stores/authStore'
import { authNavigate } from './navigation'

const BASE_URL = '/api'

// Shared refresh promise — prevents concurrent refresh calls from each
// firing independently and triggering the reuse-detection revocation.
let refreshPromise: Promise<string> | null = null

async function doRefresh(refreshToken: string): Promise<string> {
  const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!refreshRes.ok) {
    throw new Error('Refresh failed')
  }

  const data = await refreshRes.json()
  const { user } = useAuthStore.getState()
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: user!,
  })
  return data.access_token
}

export async function doRefreshToken(refreshToken: string): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = doRefresh(refreshToken).finally(() => { refreshPromise = null })
  }
  await refreshPromise
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { accessToken, refreshToken, clearSession } = useAuthStore.getState()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  let res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  // 401 → try refresh (deduped)
  if (res.status === 401 && refreshToken) {
    try {
      if (!refreshPromise) {
        refreshPromise = doRefresh(refreshToken).finally(() => { refreshPromise = null })
      }
      const newToken = await refreshPromise

      // Retry original request with new token
      headers['Authorization'] = `Bearer ${newToken}`
      res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
    } catch {
      clearSession()
      authNavigate('/login')
      throw new Error('Session expired')
    }
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: 'Request failed' }))
    let message: string
    if (Array.isArray(errorBody.detail)) {
      // Pydantic v2 validation errors return an array of {loc, msg, type} objects
      message = errorBody.detail
        .map((d: any) => (d?.msg ?? JSON.stringify(d)))
        .join('; ')
    } else if (typeof errorBody.detail === 'string') {
      message = errorBody.detail
    } else {
      message = 'Request failed'
    }
    throw new ApiError(res.status, message)
  }

  return res.json()
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// ── Auth API ──────────────────────────────────────────────────────

export async function requestOtp(email: string): Promise<{ sent: boolean; cooldown: number; expires_in: number }> {
  return request('/auth/otp/request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function verifyOtp(
  email: string,
  code: string,
): Promise<{
  access_token: string
  refresh_token: string
  expires_in: number
  user: AuthUser
  needs_profile: boolean
}> {
  return request('/auth/otp/verify', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  })
}

export async function refresh(refreshToken: string): Promise<{
  access_token: string
  refresh_token: string
  expires_in: number
}> {
  return request('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

export async function logout(refreshToken?: string): Promise<{ ok: boolean }> {
  return request('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

export async function getMe(): Promise<{ user: AuthUser }> {
  return request('/auth/me')
}

export interface AuthUser {
  id: string
  email: string
  display_name: string | null
  avatar_url: string | null
  gender: string | null
  birthdate: string | null
  age_verified: boolean
  credits_balance: number
}

// ── Credits API ────────────────────────────────────────────────────

export async function getBalance(): Promise<{ balance: number }> {
  return request('/credits/balance')
}

export async function getTransactions(cursor?: string, limit = 20): Promise<{
  items: Array<{ delta: number; type: string; ref_type: string; balance_after: number; created_at: string }>
  next_cursor: string | null
}> {
  const params = new URLSearchParams()
  if (cursor) params.set('cursor', cursor)
  params.set('limit', String(limit))
  return request(`/credits/transactions?${params}`)
}

export async function redeemCode(code: string): Promise<{ ok: boolean; credited: boolean; balance: number }> {
  return request('/credits/redeem', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function getPricing(): Promise<{
  signup_grant: number
  per_text: number
  per_voice: number
  afdian_url: string
  tiers: Array<{ label: string; price: number; credits: number }>
}> {
  return request('/credits/pricing')
}

// ── Profile API ────────────────────────────────────────────────────

export async function getProfile(): Promise<{ user: AuthUser }> {
  return request('/profile')
}

export async function updateProfile(data: {
  display_name?: string
  gender?: string
  birthdate?: string
  timezone?: string
}): Promise<{ ok: boolean; age_verified: boolean | null; message?: string }> {
  return request('/profile', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function uploadAvatar(file: File): Promise<{ avatar_url: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')

  const res = await fetch('/api/profile/avatar', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })

  const data = await res.json().catch(() => null)
  if (!res.ok || !data) {
    throw new Error(data?.detail || `上传失败 (${res.status})`)
  }
  return data
}

// ── Account API ────────────────────────────────────────────────────

export async function clearConversations(): Promise<{ ok: boolean }> {
  return request('/account/clear-conversations', { method: 'POST' })
}

export async function deleteAccount(confirm: string): Promise<{ ok: boolean; message: string }> {
  return request('/account/delete', {
    method: 'POST',
    body: JSON.stringify({ confirm }),
  })
}

export async function exportData(): Promise<any> {
  return request('/account/export', { method: 'POST' })
}

// ── Chat API ───────────────────────────────────────────────────────

export async function getInboxSummary(): Promise<{
  items: Array<{ character_id: string; last_message_text: string; last_message_at: string | null; modality: string }>
}> {
  return request('/chat/inbox-summary')
}

export async function getChatHistory(
  characterId: string,
  cursor?: string,
  limit = 30,
): Promise<{
  items: Array<{
    id: string
    role: string
    content: string
    modality: string
    audio_url: string | null
    audio_duration_ms: number | null
    credits_charged: number | null
    turn_id: string | null
    created_at: string
  }>
  next_cursor: string | null
}> {
  const params = new URLSearchParams({ character_id: characterId })
  if (cursor) params.set('cursor', cursor)
  params.set('limit', String(limit))
  return request(`/chat/history?${params}`)
}

// ── Character Catalog API ──────────────────────────────────────────

/**
 * A character as returned by the server catalog (UGC refactor C2).
 * `display_name` is authoritative (derived from the Soul Spec); visual assets
 * (avatar / colors) remain a frontend concern — see resolveCharacterProfile.
 */
export interface CharacterDTO {
  id: string
  display_name: string
  visibility: string
  is_builtin: boolean
  is_owner: boolean
  avatar_url?: string | null
  has_voice?: boolean
}

export async function getCharacters(): Promise<{ characters: CharacterDTO[] }> {
  return request('/characters')
}

// ── UGC Character CRUD ─────────────────────────────────────────────

/** Mirrors backend CharacterDraft (heart/ss01_soul/draft.py). */
export interface CharacterDraftDTO {
  display_name: { zh?: string; ja?: string; en?: string }
  avatar_url?: string
  persona: string
  greeting_style: 'warm' | 'cool' | 'playful' | 'reserved' | 'intense'
  speech_samples?: string[]
  gender?: 'male' | 'female'
  sliders: {
    warmth: number
    talkativeness: number
    directness: number
    humor: number
    playfulness: number
    steadiness: number
  }
  locale?: string
}

export async function uploadCharacterAvatar(file: File): Promise<{ avatar_url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')
  const res = await fetch('/api/characters/avatar', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok || !data) throw new Error(data?.detail || `上传失败 (${res.status})`)
  return data
}

export async function createCharacter(draft: CharacterDraftDTO): Promise<{
  id: string
  display_name: string
  spec_version: string
  visibility: string
}> {
  return request('/characters', { method: 'POST', body: JSON.stringify(draft) })
}

export async function updateCharacter(
  characterId: string,
  draft: CharacterDraftDTO,
): Promise<{ id: string; spec_version: string }> {
  return request(`/characters/${characterId}`, { method: 'PATCH', body: JSON.stringify(draft) })
}

export async function getCharacterDraft(characterId: string): Promise<CharacterDraftDTO> {
  return request(`/characters/${characterId}/draft`)
}

export async function setCharacterVisibility(
  characterId: string,
  visibility: 'public' | 'unlisted' | 'private',
): Promise<{ id: string; visibility: string }> {
  return request(`/characters/${characterId}/visibility`, {
    method: 'PATCH',
    body: JSON.stringify({ visibility }),
  })
}

export async function disableCharacter(
  characterId: string,
): Promise<{ id: string; status: string }> {
  return request(`/characters/${characterId}/disable`, { method: 'POST' })
}

// ── Character Settings API ─────────────────────────────────────────

export async function getCharacterSettings(characterId: string): Promise<{ voice_enabled: boolean }> {
  return request(`/characters/${characterId}/settings`)
}

export async function updateCharacterSettings(
  characterId: string,
  voiceEnabled: boolean,
): Promise<{ voice_enabled: boolean }> {
  return request(`/characters/${characterId}/settings`, {
    method: 'PATCH',
    body: JSON.stringify({ voice_enabled: voiceEnabled }),
  })
}

export async function clearCharacterConversations(characterId: string): Promise<{ ok: boolean }> {
  return request(`/characters/${characterId}/clear-conversations`, {
    method: 'POST',
  })
}

// ── Voice management ──────────────────────────────────────────────────────────

export interface PresetVoiceDTO {
  id: string
  name: string
  voice_id: string
  provider: string
  description?: string | null
  sample_url?: string | null
  gender?: 'male' | 'female'
}

export interface CharacterVoiceDTO {
  configured: boolean
  voice_type?: 'preset' | 'clone'
  clone_status?: 'pending' | 'processing' | 'ready' | 'failed'
  preset_voice_id?: string | null
  preset_name?: string | null
  has_voice?: boolean
}

export async function getPresetVoices(
  gender?: 'male' | 'female',
): Promise<{ presets: PresetVoiceDTO[] }> {
  const qs = gender ? `?gender=${gender}` : ''
  return request(`/voice/presets${qs}`)
}

export async function getCharacterVoice(characterId: string): Promise<CharacterVoiceDTO> {
  return request(`/voice/${characterId}`)
}

export async function setPresetVoice(
  characterId: string,
  presetVoiceId: string,
): Promise<{ ok: boolean; voice_type: string; clone_status: string }> {
  return request('/voice/preset', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, preset_voice_id: presetVoiceId }),
  })
}

export async function uploadVoiceClone(
  characterId: string,
  file: File,
): Promise<{ ok: boolean; clone_status: string; balance: number }> {
  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`/api/voice/clone?character_id=${encodeURIComponent(characterId)}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  const data = await res.json()
  if (!res.ok) throw new ApiError(res.status, data.detail || '上传失败')
  return data
}

export async function removeCharacterVoice(characterId: string): Promise<{ ok: boolean }> {
  return request(`/voice/${characterId}`, { method: 'DELETE' })
}

// --- Proactive messages (SS06 Inner Loop) ---

export interface ProactiveMessageDTO {
  id: string
  character_id: string
  content: string
  trigger_type: string
  created_at: string
}

export async function getPendingProactive(
  userId: string,
  characterId?: string,
): Promise<{ user_id: string; character_id: string | null; count: number; messages: ProactiveMessageDTO[] }> {
  const params = new URLSearchParams({ user_id: userId })
  if (characterId) params.set('character_id', characterId)
  return request(`/proactive/pending?${params.toString()}`)
}

export async function ackProactive(
  userId: string,
  messageIds: string[],
): Promise<{ acknowledged: number }> {
  const params = new URLSearchParams({ user_id: userId })
  return request(`/proactive/ack?${params.toString()}`, {
    method: 'POST',
    body: JSON.stringify({ message_ids: messageIds }),
  })
}
