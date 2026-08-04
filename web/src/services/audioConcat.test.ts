import { describe, expect, it } from 'vitest'
import { storedAudioFormat } from './audioConcat'

describe('storedAudioFormat', () => {
  // Regression: a WAV payload was mislabelled 'mp3', producing a base64 blob
  // tagged audio/mpeg that iOS Safari could not decode ("语音没能播放" after a
  // ~2s stall), while a refresh replaying the server file worked. Only genuine
  // mp3 may map to mp3; pcm16 and wav must both store as wav.
  it('keeps genuine mp3 as mp3', () => {
    expect(storedAudioFormat('mp3')).toBe('mp3')
  })

  it('maps wav to wav (was incorrectly collapsed to mp3)', () => {
    expect(storedAudioFormat('wav')).toBe('wav')
  })

  it('maps pcm16 to wav (wrapped into a RIFF container before storing)', () => {
    expect(storedAudioFormat('pcm16')).toBe('wav')
  })

  it('defaults unknown/undefined formats to wav, never mislabelling as mp3', () => {
    expect(storedAudioFormat(undefined)).toBe('wav')
    expect(storedAudioFormat('')).toBe('wav')
    expect(storedAudioFormat('opus')).toBe('wav')
  })
})
