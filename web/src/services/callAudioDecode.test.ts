import { describe, it, expect } from 'vitest'
import { parseWavHeader, pcm16ToFloat32Mono, decodeCallChunk } from './callAudioDecode'

// Build a minimal canonical 44-byte PCM16 WAV header + data section.
function makeWav(samples: Int16Array, sampleRate: number, channels = 1): Uint8Array {
  const dataBytes = samples.length * 2
  const buf = new ArrayBuffer(44 + dataBytes)
  const v = new DataView(buf)
  const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }
  w(0, 'RIFF'); v.setUint32(4, 36 + dataBytes, true); w(8, 'WAVE')
  w(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true)
  v.setUint16(22, channels, true); v.setUint32(24, sampleRate, true)
  v.setUint32(28, sampleRate * channels * 2, true); v.setUint16(32, channels * 2, true)
  v.setUint16(34, 16, true)
  w(36, 'data'); v.setUint32(40, dataBytes, true)
  const out = new Uint8Array(buf)
  const dv = new DataView(buf)
  for (let i = 0; i < samples.length; i++) dv.setInt16(44 + i * 2, samples[i], true)
  return out
}

describe('parseWavHeader', () => {
  it('parses sample rate, channels, and data offset from a canonical header', () => {
    const wav = makeWav(new Int16Array([1, 2, 3, 4]), 44100)
    const h = parseWavHeader(wav)
    expect(h).not.toBeNull()
    expect(h!.sampleRate).toBe(44100)
    expect(h!.channels).toBe(1)
    expect(h!.bitDepth).toBe(16)
    expect(h!.dataOffset).toBe(44)
  })

  it('returns null for headerless PCM (no RIFF)', () => {
    const raw = new Uint8Array([0, 0, 1, 0, 2, 0])
    expect(parseWavHeader(raw)).toBeNull()
  })

  it('returns null for too-short input', () => {
    expect(parseWavHeader(new Uint8Array([1, 2, 3]))).toBeNull()
  })
})

describe('pcm16ToFloat32Mono', () => {
  it('converts int16 samples to [-1,1] floats', () => {
    const buf = new ArrayBuffer(6)
    const dv = new DataView(buf)
    dv.setInt16(0, 0, true)
    dv.setInt16(2, 0x7fff, true) // max positive → ~1.0
    dv.setInt16(4, -0x8000, true) // min → -1.0
    const out = pcm16ToFloat32Mono(new Uint8Array(buf), 0, 1)
    expect(out.length).toBe(3)
    expect(out[0]).toBeCloseTo(0, 5)
    expect(out[1]).toBeCloseTo(1, 4)
    expect(out[2]).toBeCloseTo(-1, 4)
  })

  it('averages interleaved stereo down to mono', () => {
    const buf = new ArrayBuffer(8)
    const dv = new DataView(buf)
    dv.setInt16(0, 0x4000, true); dv.setInt16(2, 0x4000, true) // frame 0: L=R
    dv.setInt16(4, 0x2000, true); dv.setInt16(6, 0x6000, true) // frame 1
    const out = pcm16ToFloat32Mono(new Uint8Array(buf), 0, 2)
    expect(out.length).toBe(2)
    expect(out[0]).toBeCloseTo(0x4000 / 0x7fff, 4)
  })
})

describe('decodeCallChunk', () => {
  it('decodes a self-contained WAV frame (first realtime frame / REST file)', () => {
    const wav = makeWav(new Int16Array([0x100, 0x200, 0x300]), 24000)
    const d = decodeCallChunk(wav, 0)
    expect(d).not.toBeNull()
    expect(d!.sampleRate).toBe(24000)
    expect(d!.channels).toBe(1)
    expect(d!.samples.length).toBe(3)
  })

  it('decodes a headerless PCM continuation frame using the forwarded rate', () => {
    const buf = new ArrayBuffer(4)
    const dv = new DataView(buf)
    dv.setInt16(0, 0x1000, true); dv.setInt16(2, 0x2000, true)
    const d = decodeCallChunk(new Uint8Array(buf), 44100)
    expect(d).not.toBeNull()
    expect(d!.sampleRate).toBe(44100) // no header → fell back to forwarded rate
    expect(d!.samples.length).toBe(2)
  })

  it('returns null for a headerless frame with no known rate (unschedulable)', () => {
    const raw = new Uint8Array([0, 0, 1, 0])
    expect(decodeCallChunk(raw, 0)).toBeNull()
  })
})
