import { afterEach, describe, expect, it, vi } from 'vitest'

import { detailToMessage, updateProfile } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('updateProfile', () => {
  it('sends every completed profile field in a JSON request body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, age_verified: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await updateProfile({
      display_name: '测试用户',
      gender: 'undisclosed',
      birthdate: '2000-01-01',
      timezone: 'Asia/Shanghai',
    })

    expect(fetchMock).toHaveBeenCalledWith('/api/profile/complete', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        display_name: '测试用户',
        gender: 'undisclosed',
        birthdate: '2000-01-01',
        timezone: 'Asia/Shanghai',
      }),
    }))
  })
})

describe('detailToMessage', () => {
  it('does not expose FastAPI Field required errors to users', () => {
    expect(detailToMessage([
      { loc: ['body'], msg: 'Field required', type: 'missing' },
    ], 'fallback')).toBe('资料提交不完整，请刷新页面后重试')
  })

  it('names a missing profile field when FastAPI provides one', () => {
    expect(detailToMessage([
      { loc: ['body', 'birthdate'], msg: 'Field required', type: 'missing' },
    ], 'fallback')).toBe('请填写出生日期')
  })
})
