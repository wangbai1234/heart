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
    throw new ApiError(res.status, detailToMessage(errorBody?.detail, 'Request failed'))
  }

  return res.json()
}

/**
 * Normalize a FastAPI error `detail` into a human-readable string.
 *
 * `detail` can be:
 *   - a string (plain HTTPException)
 *   - an array of {loc, msg, type} (Pydantic v2 validation errors)
 *   - an object with a `code` (our structured errors, e.g. tier_forbidden)
 * Passing an object/array straight into an Error message renders as
 * "[object Object]", which is exactly the clone-upload bug this fixes.
 */
export function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail || fallback
  if (Array.isArray(detail)) {
    return (
      detail.map((d: any) => (d?.msg ?? JSON.stringify(d))).join('; ') || fallback
    )
  }
  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, any>
    if (d.code === 'tier_forbidden') {
      const label = d.provider === 'fish' ? '真人语音（Fish）' : '音色'
      return `${label}克隆需要会员权限，请先升级会员后再试。`
    }
    if (typeof d.message === 'string') return d.message
    if (typeof d.msg === 'string') return d.msg
  }
  return fallback
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
  needs_restoration?: boolean
  grace_end?: string | null
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

// ── Pricing / Membership / Shop (yuoyuo 商业化) ─────────────────────
// Shapes mirror docs/upgrade/yuoyuo_coin/api_contract.md §1.1–1.2.
// All amounts are display units (yuoyuo币, integer); backend already ÷100.

export interface PricingModel {
  id: string // 'deepseek' | 'grok' | 'claude'
  label: string
  cost: number // 币 per LLM turn
  tiers_allowed: string[]
}

export interface PricingAction {
  id: string // 'tts_mimo' | 'tts_fish' | 'clone_mimo' | 'clone_fish'
  label: string
  cost: number
}

export interface MembershipTierInfo {
  tier: string // 'free' | 'plus' | 'immersive'
  label: string
  price: number // ¥ / month
  sku: string | null
  benefits: string[]
  models: string[]
  tts: string[]
  clone: string[]
  monthly_grant: number
}

export interface ShopItem {
  sku: string
  label: string
  price: number // ¥
  credits: number // 到账总币数（已含 bonus）
  bonus: number
}

export interface Pricing {
  signup_grant: number
  afdian_url: string
  models: PricingModel[]
  actions: PricingAction[]
  membership_tiers: MembershipTierInfo[]
  shop: ShopItem[]
}

export async function getPricing(): Promise<Pricing> {
  return request('/credits/pricing')
}

export interface MembershipEntitlements {
  models: string[]
  tts: string[]
  clone: string[]
}

export interface Membership {
  tier: string
  expires_at: string | null // null for free
  monthly_grant: number
  entitlements: MembershipEntitlements
  binding_code: string
}

export async function getMembership(): Promise<Membership> {
  return request('/membership')
}

// ── Invite (yuoyuo 邀请系统) ────────────────────────────────────────

export interface InviteStage {
  threshold: number
  bonus: number
  reached: boolean
}

export interface InviteStatus {
  invite_code: string
  invite_url: string
  invited_count: number
  pending_count: number
  total_reward: number
  stages: InviteStage[]
}

export async function getInviteStatus(): Promise<InviteStatus> {
  return request('/invite/status')
}

export async function bindInvite(code: string): Promise<{ ok: boolean }> {
  return request('/invite/bind', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
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
    throw new Error(detailToMessage(data?.detail, `上传失败 (${res.status})`))
  }
  return data
}

// ── Account API ────────────────────────────────────────────────────

export async function clearConversations(): Promise<{ ok: boolean }> {
  return request('/account/clear-conversations', { method: 'POST' })
}

export async function deleteAccount(confirm: string): Promise<{ ok: boolean; message: string; grace_end?: string }> {
  return request('/account/delete', {
    method: 'POST',
    body: JSON.stringify({ confirm }),
  })
}

export async function restoreAccount(): Promise<{ ok: boolean; message: string }> {
  return request('/account/restore', { method: 'POST' })
}

export async function exportData(): Promise<any> {
  return request('/account/export', { method: 'POST' })
}

// ── Chat API ───────────────────────────────────────────────────────

export async function getInboxSummary(): Promise<{
  items: Array<{
    character_id: string
    last_message_text: string
    last_message_at: string | null
    modality: string
    unread_count: number
  }>
}> {
  return request('/chat/inbox-summary')
}

export async function markCharacterRead(characterId: string): Promise<{ ok: boolean }> {
  return request(`/chat/${encodeURIComponent(characterId)}/mark-read`, { method: 'POST' })
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
    /** 'action' for grey pill bubbles, 'text' for spoken dialog, 'voice' for audio messages. */
    kind: 'text' | 'action' | 'voice' | null
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
  if (!res.ok || !data) throw new Error(detailToMessage(data?.detail, `上传失败 (${res.status})`))
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

/**
 * Switch which TTS engine (日常语音 'mimo' / 真人语音 'fish') the current user
 * hears for a character. Instant, per-user — the target engine must already have
 * a ready voice (409 otherwise); Fish requires a paid tier (403).
 */
export async function setCharacterVoiceProvider(
  characterId: string,
  provider: 'mimo' | 'fish',
): Promise<{ voice_provider: string }> {
  return request(`/characters/${characterId}/voice-provider`, {
    method: 'PATCH',
    body: JSON.stringify({ provider }),
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
  // TTS provider that owns this voice (mimo/fish/minimax). Drives the backstage
  // 语音聊天 tier highlight. Absent until the per-character-provider backend ships.
  voice_provider?: string | null
  // Providers with a ready voice the user can switch between (mimo/fish), and the
  // user's current per-character selection. Drive the 日常/真人 toggle state.
  available_providers?: string[]
  selected_provider?: string | null
  has_voice?: boolean
  // Populated by the backend only when clone_status='failed' — surfaces the
  // real reason (missing GroupId / unreachable audio URL / MiniMax quota)
  // so the toast is actionable instead of a generic retry prompt.
  error_msg?: string | null
}

export async function getPresetVoices(
  gender?: 'male' | 'female',
): Promise<{ presets: PresetVoiceDTO[] }> {
  const qs = gender ? `?gender=${gender}` : ''
  return request(`/voice/presets${qs}`)
}

/**
 * Fetch a preset voice sample as a Blob and return an object URL suitable for
 * `new Audio(url)`.  Sends the current Bearer token via fetch (since <audio>
 * cannot carry Authorization headers).  Caller is responsible for revoking
 * the URL with `URL.revokeObjectURL` once playback is done.
 */
export async function getPresetVoiceSampleUrl(presetId: string): Promise<string> {
  const { accessToken } = useAuthStore.getState()
  const res = await fetch(`${BASE_URL}/voice/presets/${encodeURIComponent(presetId)}/sample`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })
  if (!res.ok) {
    // Read the detail out so the UI can show what actually broke instead of
    // "please try again". The endpoint appends the provider's raw error to
    // `detail` (see backend/heart/api/routes_voice.py:get_preset_voice_sample).
    let detail = ''
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // ignore parse errors; res.ok=false without JSON body is possible
    }
    throw new ApiError(res.status, detail || `sample fetch failed: ${res.status}`)
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
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
  provider: string = 'mimo',
): Promise<{ ok: boolean; clone_status: string; balance: number }> {
  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(
    `/api/voice/clone?character_id=${encodeURIComponent(characterId)}&provider=${encodeURIComponent(provider)}`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: formData,
    },
  )
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, detailToMessage(data?.detail, '上传失败'))
  return data
}

export async function removeCharacterVoice(characterId: string): Promise<{ ok: boolean }> {
  return request(`/voice/${characterId}`, { method: 'DELETE' })
}

export async function transcribeAudio(
  wav: Blob,
  durationMs: number,
): Promise<{ transcript: string; duration_ms: number; balance?: number; audio_url?: string | null }> {
  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')
  const formData = new FormData()
  formData.append('file', wav, 'recording.wav')
  formData.append('duration_ms', String(durationMs))
  const res = await fetch('/api/voice/transcribe', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, detailToMessage(data?.detail, '语音识别失败'))
  return data
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

// ── Story / 剧情 mode (SS09) ────────────────────────────────────────
// Read paths for the scenario catalog. Run lifecycle + WS land in PR3/PR4.
// `maturity='adult'` scenarios are age-gated: the server soft-locks them for
// unverified users (`locked:true`, blurb replaced with a gate hint) rather than
// hard-failing, so the UI can drive the user to /age-gate.

export interface ScenarioCardDTO {
  id: string
  title: string
  genre: string
  cover_url: string | null
  blurb: string
  maturity: 'all_ages' | 'adult'
  is_featured: boolean
  play_count: number
  locked: boolean
}

/** A single form field in a scenario's player-card template (StartRunSheet). */
export interface PlayerTemplateField {
  key: string
  label: string
  type: 'text' | 'textarea' | 'select'
  required: boolean
  options?: string[]
}

export interface PlayerTemplate {
  fields: PlayerTemplateField[]
}

export interface ScenarioDetailDTO extends ScenarioCardDTO {
  player_template: PlayerTemplate
}

export async function getScenarios(params?: {
  genre?: string
  featured?: boolean
  limit?: number
  offset?: number
}): Promise<{ count: number; scenarios: ScenarioCardDTO[] }> {
  const qs = new URLSearchParams()
  if (params?.genre) qs.set('genre', params.genre)
  if (params?.featured !== undefined) qs.set('featured', String(params.featured))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const suffix = qs.toString() ? `?${qs}` : ''
  return request(`/story/scenarios${suffix}`)
}

export async function getStoryGenres(): Promise<{
  genres: Array<{ genre: string; count: number }>
}> {
  return request('/story/genres')
}

export async function getScenario(scenarioId: string): Promise<ScenarioDetailDTO> {
  return request(`/story/scenarios/${encodeURIComponent(scenarioId)}`)
}

// ── Run lifecycle (PR4) ─────────────────────────────────────────────
// A run is one playthrough of a scenario. Turns stream over /api/story/ws;
// these REST calls start / list / resume / delete runs.

export type StoryRole = 'player' | 'gm' | 'npc' | 'system'
export type StoryKind = 'narration' | 'dialogue' | 'action'

/** A persisted story message (transcript row) or an opening bubble. */
export interface StoryBubbleDTO {
  id?: string
  turn_id: string | null
  seq?: number
  role?: StoryRole
  kind: StoryKind
  npc_name: string | null
  content: string
}

export interface StoryRunDTO {
  run_id: string
  scenario_id: string
  title: string
  status: 'active' | 'ended' | 'deleted'
  turn_count: number
  model: string
  created_at: string
  last_activity_at: string
}

export async function startRun(
  scenarioId: string,
  playerIdentity: Record<string, unknown>,
): Promise<{ run: StoryRunDTO; opening_bubbles: StoryBubbleDTO[] }> {
  return request('/story/runs', {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId, player_identity: playerIdentity }),
  })
}

export async function getRuns(): Promise<{ runs: StoryRunDTO[] }> {
  return request('/story/runs')
}

export async function getRun(
  runId: string,
  afterSeq = 0,
): Promise<{ run: StoryRunDTO; player_identity: Record<string, unknown>; messages: StoryBubbleDTO[] }> {
  const qs = afterSeq > 0 ? `?after_seq=${afterSeq}` : ''
  return request(`/story/runs/${encodeURIComponent(runId)}${qs}`)
}

export async function deleteRun(runId: string): Promise<{ ok: boolean }> {
  return request(`/story/runs/${encodeURIComponent(runId)}`, { method: 'DELETE' })
}
