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
    const fallback = statusFallback(res.status)
    const errorBody = await res.json().catch(() => ({ detail: fallback }))
    const detail = errorBody?.detail
    const code =
      detail && typeof detail === 'object' && typeof detail.code === 'string'
        ? detail.code
        : typeof detail === 'string'
          ? detail
          : undefined
    throw new ApiError(res.status, detailToMessage(detail, fallback), code)
  }

  return res.json()
}

/**
 * Stable backend error signals → friendly Chinese copy.
 *
 * Keyed by BOTH the machine codes the auth routes now emit
 * (e.g. `email_already_registered`) AND the legacy English OTP `detail`
 * strings, so every auth failure surfaces readable Chinese instead of a raw
 * "Not Found" / "Request failed" / English fragment. When you add a new
 * backend detail, add its friendly copy here too.
 */
const FRIENDLY_MESSAGES: Record<string, string> = {
  // ── Registration / login / password (machine codes) ──
  email_already_registered: '该邮箱已注册，请直接登录，或使用「忘记密码」找回。',
  invalid_invite_code: '邀请码无效，请检查后重试。',
  no_password_set: '该账号尚未设置密码，请使用验证码登录。',
  password_too_short: '密码至少 8 位，请重新设置。',
  invalid_credentials: '邮箱或密码错误，请重试。',
  email_not_registered: '该邮箱尚未注册，请先注册账号。',
  user_not_found: '账号不存在，请重新登录。',
  password_already_set: '你已设置过密码，请前往「修改密码」。',
  wrong_current_password: '当前密码不正确，请重试。',
  no_password_to_change: '你还没有设置密码，请先设置密码。',
  // ── OTP (legacy English detail strings) ──
  'Invalid or expired OTP': '验证码错误或已过期，请重新获取。',
  'Invalid or expired code': '验证码错误或已过期，请重新获取。',
  'OTP already used': '验证码已被使用，请重新获取。',
  'OTP expired': '验证码已过期，请重新获取。',
  'Code expired': '验证码已过期，请重新获取。',
  'Too many OTP attempts': '尝试次数过多，请稍后重新获取验证码。',
  'Too many attempts, request a new code': '尝试次数过多，请稍后重新获取验证码。',
  'Invalid OTP': '验证码错误，请重试。',
  'Invalid code': '验证码错误，请重试。',
  'User creation failed': '账号创建失败，请稍后重试。',
}

/** HTTP-status → generic Chinese fallback (never leak English / "Not Found"). */
export function statusFallback(status: number): string {
  if (status === 404) return '请求的服务暂不可用，请稍后重试。'
  if (status === 429) return '操作过于频繁，请稍后再试。'
  if (status >= 500) return '服务器开小差了，请稍后重试。'
  if (status === 401 || status === 403) return '登录状态已失效，请重新登录。'
  return '操作失败，请稍后重试。'
}

/**
 * Normalize a FastAPI error `detail` into a human-readable string.
 *
 * `detail` can be:
 *   - a string (plain HTTPException — either a machine code or legacy English)
 *   - an array of {loc, msg, type} (Pydantic v2 validation errors)
 *   - an object with a `code` (our structured errors, e.g. tier_forbidden)
 * Passing an object/array straight into an Error message renders as
 * "[object Object]", which is exactly the clone-upload bug this fixes.
 */
export function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') {
    return FRIENDLY_MESSAGES[detail] ?? (detail || fallback)
  }
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
    if (typeof d.code === 'string' && FRIENDLY_MESSAGES[d.code]) {
      return FRIENDLY_MESSAGES[d.code]
    }
    if (typeof d.message === 'string') return d.message
    if (typeof d.msg === 'string') return d.msg
  }
  return fallback
}

export class ApiError extends Error {
  status: number
  code?: string // structured error code from FastAPI detail (e.g. 'no_password_set')
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// ── Auth API ──────────────────────────────────────────────────────

export type OtpPurpose = 'login' | 'register' | 'password_reset'

export async function requestOtp(
  email: string,
  purpose: OtpPurpose = 'login',
): Promise<{ sent: boolean; cooldown: number; expires_in: number }> {
  return request('/auth/otp/request', {
    method: 'POST',
    body: JSON.stringify({ email, purpose }),
  })
}

/** Shape returned by all token-issuing auth endpoints. */
export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: AuthUser
  needs_profile: boolean
  needs_restoration?: boolean
  grace_end?: string | null
}

/** Register a new account: email + OTP(purpose=register) + password (+ optional invite). Auto-logs in. */
export async function registerWithPassword(
  email: string,
  otpCode: string,
  password: string,
  inviteCode?: string,
): Promise<TokenResponse> {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      otp_code: otpCode,
      password,
      invite_code: inviteCode || null,
    }),
  })
}

/**
 * Login with email + password.
 *
 * Uses a raw fetch (not `request()`) so the structured `detail.code` survives:
 * the backend returns 400 `{ detail: { code: 'no_password_set', message } }`
 * for OTP-only accounts, and the caller (LoginPage) auto-switches to the OTP
 * tab on that code. `detailToMessage()` in `request()` would flatten it away.
 */
export async function loginWithPassword(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/auth/login/password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!res.ok) {
    const fallback = statusFallback(res.status)
    const errorBody = await res.json().catch(() => ({ detail: fallback }))
    const detail = errorBody?.detail
    const code =
      detail && typeof detail === 'object' && typeof detail.code === 'string'
        ? detail.code
        : typeof detail === 'string'
          ? detail
          : undefined
    throw new ApiError(res.status, detailToMessage(detail, fallback), code)
  }

  return res.json()
}

/** Reset password via email + OTP(purpose=password_reset) + new password. Auto-logs in. */
export async function resetPassword(
  email: string,
  otpCode: string,
  newPassword: string,
): Promise<TokenResponse> {
  return request('/auth/password/reset', {
    method: 'POST',
    body: JSON.stringify({ email, otp_code: otpCode, new_password: newPassword }),
  })
}

/** Set a password for an OTP-only account (Bearer required). 409 if already set. */
export async function setPassword(password: string): Promise<{ ok: boolean }> {
  return request('/auth/password/set', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

/** Change password for an account that already has one (Bearer required). */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ ok: boolean }> {
  return request('/auth/password/change', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
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
  has_password?: boolean
}

// ── Credits API ────────────────────────────────────────────────────

export async function getBalance(): Promise<{ balance: number }> {
  return request('/credits/balance')
}

export async function dailyCheckin(): Promise<{
  granted: boolean
  already: boolean
  coins: number
  balance: number
}> {
  return request('/credits/checkin', { method: 'POST' })
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
  /** 爱发电 order/create 深链（未配置时为 null）；前端会追加 ?custom_order_id=<绑定码>。 */
  checkout_url?: string | null
}

export interface ShopItem {
  sku: string
  label: string
  price: number // ¥
  credits: number // 到账总币数（已含 bonus）
  bonus: number
  /** 爱发电 order/create 深链（未配置时为 null）；前端会追加 ?custom_order_id=<绑定码>。 */
  checkout_url?: string | null
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
  // Items complimentary on this tier (charged 0). Slugs: deepseek | grok | tts |
  // clone | asr | story_unlock | story_chat. Everything else is charged per use.
  free: string[]
}

export interface VoiceCallQuota {
  free_minutes: number
  used_minutes: number
  remaining_minutes: number
  minute_cost_coins: number
}

export interface Membership {
  tier: string
  expires_at: string | null // null for free
  monthly_grant: number
  entitlements: MembershipEntitlements
  voice_call: VoiceCallQuota
  binding_code: string
}

export async function getMembership(): Promise<Membership> {
  return request('/membership')
}

/** Bill one minute of an active voice call (heartbeat every 60s). */
export async function voiceCallHeartbeat(
  callId: string,
  minute: number,
): Promise<{ status: 'free' | 'charged' | 'insufficient'; balance: number }> {
  return request('/voice/call/heartbeat', {
    method: 'POST',
    body: JSON.stringify({ call_id: callId, minute }),
  })
}

/** This month's voice-call free-minute allowance + usage. */
export async function getVoiceCallQuota(): Promise<VoiceCallQuota & { tier: string; month_key: string }> {
  return request('/voice/call/quota')
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

// ── Companion Aggregation API (bond center) ──────────────────────────

export interface CompanionDTO {
  character_id: string
  display_name: string
  avatar_url?: string | null
  source: 'built_in' | 'user_created'
  is_owner: boolean
  is_builtin: boolean
  /** Catalog visibility (built-ins are always 'public'); drives the 可见范围 label. */
  visibility: 'public' | 'unlisted' | 'private'
  has_voice: boolean
  companion_status: 'locked' | 'encountered' | 'companioned'
  relationship_stage: string // RAW enum: STRANGER/ACQUAINTANCE/FRIEND/CONFIDANT/ROMANTIC_INTEREST/LOVER/BONDED/cold_war
  intimacy: number // 0..1
  last_message_text: string
  last_message_at: string | null
  last_message_modality: 'text' | 'voice' | null
  unread_count: number
  has_proactive: boolean
  /** Portrait cover for the discovery grid / chat background (short S3 proxy URL). */
  cover_url?: string | null
  /** Style/category tags (mirrors CharacterDTO.tags). */
  tags?: string[]
  /** Wave 3: 剧情邀约. Present only when the user qualifies for a linked scenario hook. */
  available_story_hook?: StoryHookDTO | null
}

/** A story-invitation card payload (character↔scenario hook the user qualifies for). */
export interface StoryHookDTO {
  scenario_id: string
  invite_title: string
  invite_copy: string
  cta_label: string
  cooldown_hours: number
}

export async function getCompanions(): Promise<{ companions: CompanionDTO[] }> {
  return request('/companions')
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
    /** 'action' grey pill, 'text' dialog, 'voice' audio, 'call_summary' 通话时长条,
     *  'transfer' 转账气泡(用户), 'transfer_receipt' 收款气泡(角色). */
    kind: 'text' | 'action' | 'voice' | 'call_summary' | 'transfer' | 'transfer_receipt' | null
  }>
  next_cursor: string | null
}> {
  const params = new URLSearchParams({ character_id: characterId })
  if (cursor) params.set('cursor', cursor)
  params.set('limit', String(limit))
  return request(`/chat/history?${params}`)
}

/**
 * Generate first-encounter opening scene for a character.
 * Idempotent: returns {already_exists: true} if the user already has messages.
 */
export async function generateOpening(characterId: string): Promise<{
  already_exists: boolean
  messages: Array<{
    id: string
    role: string
    content: string
    modality: string
    audio_url: string | null
    audio_duration_ms: number | null
    credits_charged: number | null
    turn_id: string | null
    created_at: string | null
    kind: 'text' | 'action' | null
  }>
}> {
  return request(`/chat/opening?character_id=${encodeURIComponent(characterId)}`, {
    method: 'POST',
  })
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
  /** Portrait cover for the discovery grid / chat background (short S3 proxy URL). */
  cover_url?: string | null
  /** Style/category tags used by the discovery filter chips. */
  tags?: string[]
  /** Engagement heat: distinct user count who chatted with this character. */
  chat_user_count?: number
  /** Moderation state: not_required | pending | approved | rejected. Owner-only meaning. */
  review_status?: string
  /** Rejection reason — only populated for the character's owner. */
  review_reason?: string | null
  /** One-line public plot hook shown under the name (display-only, ≤60 chars). */
  tagline?: string | null
  /** ISO-8601 creation timestamp — drives the「新角色」(newest) discovery sort. */
  created_at?: string | null
}

export async function getCharacters(): Promise<{ characters: CharacterDTO[] }> {
  return request('/characters')
}

/** One of the caller's own characters with its review progress. */
export interface ReviewUpdateDTO {
  id: string
  display_name: string
  visibility: string
  review_status: 'not_required' | 'pending' | 'approved' | 'rejected'
  review_reason: string | null
  submitted_at: string | null
  reviewed_at: string | null
  /** A terminal result the user hasn't confirmed yet (drives the result popup). */
  needs_ack: boolean
}

export async function getReviewUpdates(): Promise<{
  characters: ReviewUpdateDTO[]
  approved_count: number
}> {
  return request('/characters/review/updates')
}

export async function ackReviewResult(characterId: string): Promise<{ ok: boolean }> {
  return request('/characters/review/ack', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId }),
  })
}

/**
 * Public-facing character profile for the discovery / profile page
 * (GET /api/characters/{id}/profile). Only public presentation fields — the
 * backend deliberately never exposes internal persona (core_wound / core_fear …).
 * Every field degrades to '' / [] so the UI renders purely by presence.
 */
export interface CharacterProfileDTO {
  id: string
  display_name: string
  creator_name: string
  avatar_url: string | null
  cover_url: string | null
  /** Age bracket the creator picked (e.g. "18-24"); null when unset. */
  age_range?: string | null
  tags: string[]
  tagline: string
  archetype_label: string
  one_liner: string
  intro: string
  personality: Array<{ label: string; value: number | null }>
  source: string
  has_voice: boolean
}

export async function getCharacterProfile(id: string): Promise<CharacterProfileDTO> {
  return request(`/characters/${encodeURIComponent(id)}/profile`)
}

// ── UGC Character CRUD ─────────────────────────────────────────────

/** Mirrors backend CharacterDraft (heart/ss01_soul/draft.py). */
export interface CharacterDraftDTO {
  display_name: { zh?: string; ja?: string; en?: string }
  avatar_url?: string
  /** Portrait cover (short S3 proxy URL from POST /api/characters/cover — never base64). */
  cover_url?: string
  /** Up to 10 role/category tags for the discovery filter. */
  tags?: string[]
  persona: string
  greeting_style: 'warm' | 'cool' | 'playful' | 'reserved' | 'intense'
  speech_samples?: string[]
  /** Optional background history (0–1500 chars). */
  backstory?: string
  /** Up to 5 signature catchphrases (each ≤50 chars). */
  catchphrases?: string[]
  /** Up to 10 hard-never rules from the creator (each ≤200 chars). */
  hard_never_user?: string[]
  gender?: 'male' | 'female'
  /** Age bracket the creator picked (e.g. "18-24"); one of AGE_RANGES. */
  age_range?: string
  /** Authored first-encounter opening, played back verbatim (no runtime LLM). */
  opening?: string
  /** Public profile blurb shown to users (display-only, not fed to the model). */
  intro?: string
  /** One-line public tagline under the name (display-only, ≤60 chars). */
  tagline?: string
  sliders: {
    warmth: number
    talkativeness: number
    directness: number
    humor: number
    playfulness: number
    steadiness: number
  }
  locale?: string
  /** Intended visibility on publish. public/unlisted enter review; private is immediate. */
  visibility?: 'public' | 'unlisted' | 'private'
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

/**
 * Upload a character portrait cover. The file must already be a compressed WebP
 * (see utils/imageCompress — 800px / q0.8); the backend is S3-only and rejects
 * with 413 when storage is unavailable rather than inlining base64 into the DB.
 */
export async function uploadCharacterCover(file: File): Promise<{ cover_url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const { accessToken } = (await import('../stores/authStore')).useAuthStore.getState()
  if (!accessToken) throw new Error('未登录')
  const res = await fetch('/api/characters/cover', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  const data = await res.json().catch(() => null)
  if (!res.ok || !data) throw new Error(detailToMessage(data?.detail, `封面上传失败 (${res.status})`))
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

/**
 * Generate a first-encounter opening draft with the main model for the creator
 * to accept or edit. Not persisted; creates no character. The saved opening is
 * later played back verbatim (see ss10_opening.generator) with no runtime LLM.
 */
export async function generateOpeningPreview(input: {
  display_name?: string
  persona: string
  backstory?: string
  tags?: string[]
  greeting_style?: string
}): Promise<{ opening: string }> {
  return request('/characters/opening-preview', {
    method: 'POST',
    body: JSON.stringify(input),
  })
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
  // True when the returned voice is THIS user's personal override on a public
  // character they don't own (not published to other users). Drives a hint on
  // the config screen. Absent/false → canonical (owner-set or built-in).
  is_personal?: boolean
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
): Promise<{ ok: boolean; voice_type: string; clone_status: string; is_personal?: boolean }> {
  return request('/voice/preset', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, preset_voice_id: presetVoiceId }),
  })
}

export async function uploadVoiceClone(
  characterId: string,
  file: File,
  provider: string = 'fish',
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

// Persist a single WeChat-style call-summary bubble after a voice call ends.
// The per-turn call rows are hidden from history (channel='call'); this row
// (kind='call_summary') shows the total duration. Returns the mm:ss string.
export async function createCallSummary(
  characterId: string,
  durationMs: number,
): Promise<{ ok: boolean; duration: string }> {
  return request('/chat/call-summary', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, duration_ms: durationMs }),
  })
}

// WeChat-style transfer. The character decides (LLM) whether to 收下 based on
// personality + recent conversation + amount/note. Returns the (resolved)
// transfer bubble, the character's reply bubble(s), and whether it was accepted.
export interface TransferRow {
  id: string
  role: 'user' | 'assistant'
  content: string
  kind: string
  turn_id: string
}
export async function sendTransfer(
  characterId: string,
  amount: number,
  note: string,
): Promise<{ ok: boolean; transfer: TransferRow; replies: TransferRow[]; accepted: boolean }> {
  return request('/chat/transfer', {
    method: 'POST',
    body: JSON.stringify({ character_id: characterId, amount, note }),
  })
}

// --- Proactive messages (SS06 Inner Loop) ---

export interface ProactiveSegment {
  kind: 'text' | 'action'
  content: string
}

export interface ProactiveMessageDTO {
  id: string
  character_id: string
  content: string
  // Server-split bubbles: dialog vs parenthetical action/narration, in order.
  // Falls back to a single text bubble from `content` if absent (older server).
  segments?: ProactiveSegment[]
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
// Read paths for the scenario catalog + run lifecycle + WS.
// `maturity` is retained in the DTO for back-compat but is NOT rendered anywhere:
// the 纯爱/18禁 distinction was dropped from the product (2026-08-02). Scenarios
// are not age-gated (registration already restricts signup to adults).

export interface ScenarioCardDTO {
  id: string
  title: string
  genre: string
  cover_url: string | null
  blurb: string
  maturity: 'all_ages' | 'adult'
  is_featured: boolean
  play_count: number
  /** Free (普通) users may unlock/play only free_tier scenarios. */
  free_tier: boolean
}

/** A single form field in a scenario's player-card template (StartRunSheet). */
export interface PlayerTemplateField {
  key: string
  label: string
  /**
   * text/textarea → free text; select/radio → single choice from `options`;
   * checkbox → multi-select (value is a string[] of picked options).
   */
  type: 'text' | 'textarea' | 'select' | 'radio' | 'checkbox'
  required: boolean
  options?: string[]
}

export interface PlayerTemplate {
  fields: PlayerTemplateField[]
}

export interface ScenarioDetailDTO extends ScenarioCardDTO {
  player_template: PlayerTemplate
  /** True once the caller has permanently unlocked (paid for) this scenario. */
  unlocked: boolean
  /** True if the caller's tier is eligible to unlock this scenario. */
  tier_allowed: boolean
  /** One-time unlock price, in 悠悠币 (display coins). */
  unlock_cost_coins: number
  /** Per-minute playtime price, in 悠悠币 (display coins). */
  minute_cost_coins: number
}

export async function unlockScenario(
  scenarioId: string,
): Promise<{ ok: boolean; already: boolean; balance: number }> {
  return request(`/story/scenarios/${encodeURIComponent(scenarioId)}/unlock`, {
    method: 'POST',
  })
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

/** A scenario the user recently played (deduplicated by scenario_id). */
export interface RecentScenarioDTO {
  run_id: string
  scenario_id: string
  title: string
  cover_url: string | null
  genre: string
  turn_count: number
  last_activity_at: string
}

export async function getRecentScenarios(limit = 4): Promise<{ scenarios: RecentScenarioDTO[] }> {
  return request(`/story/recent-scenarios?limit=${limit}`)
}

/** The caller's current active run for a scenario, or null (resume vs restart). */
export async function getActiveRun(scenarioId: string): Promise<{ run: StoryRunDTO | null }> {
  return request(`/story/scenarios/${encodeURIComponent(scenarioId)}/active-run`)
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

// ── Admin: character review ────────────────────────────────────────
// These bypass the bearer-token `request()` helper: the admin console is not a
// logged-in user session, it authenticates with the X-Admin-Key header (value =
// backend ADMIN_SECRET_KEY). The key is held in component state only, never
// persisted. A 403 means a wrong/empty key; a 503 means the backend has no
// ADMIN_SECRET_KEY configured.

export interface PendingCharacterDTO {
  id: string
  display_name: string
  owner_user_id: string | null
  owner_email: string | null
  visibility: string
  avatar_url: string | null
  cover_url: string | null
  persona: string | null
  intro: string | null
  tagline: string | null
  backstory: string | null
  opening: string | null
  greeting_style: string | null
  gender: string | null
  age_range: string | null
  tags: string[]
  catchphrases: string[]
  speech_samples: string[]
  hard_never_user: string[]
  submitted_at: string | null
}

async function adminRequest<T>(path: string, adminKey: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Key': adminKey,
      ...(options.headers as Record<string, string>),
    },
  })
  if (!res.ok) {
    const fallback = statusFallback(res.status)
    const body = await res.json().catch(() => ({ detail: fallback }))
    throw new ApiError(res.status, detailToMessage(body?.detail, fallback))
  }
  return res.json()
}

export async function adminListPendingCharacters(
  adminKey: string,
): Promise<{ pending: PendingCharacterDTO[]; count: number }> {
  return adminRequest('/admin/characters/pending', adminKey)
}

export async function adminApproveCharacter(
  characterId: string,
  adminKey: string,
): Promise<{ ok: boolean; id: string; coins_granted: number; milestone_plus_granted: boolean }> {
  return adminRequest(`/admin/characters/${encodeURIComponent(characterId)}/approve`, adminKey, {
    method: 'POST',
  })
}

export async function adminRejectCharacter(
  characterId: string,
  reason: string,
  adminKey: string,
): Promise<{ ok: boolean; id: string; reason: string }> {
  return adminRequest(`/admin/characters/${encodeURIComponent(characterId)}/reject`, adminKey, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}
