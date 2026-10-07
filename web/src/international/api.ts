import i18n, { supportedLocale, type Locale } from '../i18n'
import { useAuthStore } from '../stores/authStore'
import { doRefreshToken } from '../services/api'

export interface Preferences {
  interface_language: Locale
  response_language: Locale
  action_style: 'parentheses' | 'asterisks' | 'fullwidth'
}
export function initialPreferences(): Preferences {
  return { interface_language: supportedLocale(i18n.language), response_language: supportedLocale(i18n.language), action_style: 'parentheses' }
}
export class InternationalApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) { super(message); this.status = status; this.code = code }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const perform = () => fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json', 'Accept-Language': i18n.language,
      ...(useAuthStore.getState().accessToken ? { Authorization: `Bearer ${useAuthStore.getState().accessToken}` } : {}),
      ...options.headers,
    },
  })
  let response = await perform()
  const refreshToken = useAuthStore.getState().refreshToken
  if (response.status === 401 && refreshToken) {
    try { await doRefreshToken(refreshToken); response = await perform() }
    catch { useAuthStore.getState().clearSession() }
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401) useAuthStore.getState().clearSession()
    const detail = data.detail
    const code = typeof detail === 'string' ? detail : detail?.code ?? ''
    const key = i18n.exists(code) ? code : response.status === 429 ? 'rateLimited'
      : response.status === 401 ? 'sessionExpired' : /OTP|code.*expired|Invalid code/i.test(code) ? 'otpInvalid' : 'error'
    throw new InternationalApiError(response.status, code, i18n.t(key))
  }
  return data as T
}
export const json = (method: string, value: unknown): RequestInit => ({ method, body: JSON.stringify(value) })
