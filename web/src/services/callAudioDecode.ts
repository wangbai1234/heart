/**
 * Decode one realtime voice-call audio chunk into linear PCM float samples for
 * Web Audio scheduling.
 *
 * Why this exists: a voice call streams audio as many small frames the instant
 * they are synthesized. mp3 frames are slices of one continuous stream and are
 * NOT independently decodable by the browser (`<audio>`/`decodeAudioData` on a
 * lone slice fails silently) — that was the "call has no sound" bug. So calls
 * use Fish's wav format, whose payload is linear PCM16 we can turn into an
 * AudioBuffer by hand, chunk by chunk, with no container-level decode.
 *
 * A chunk may be one of three shapes and we detect, not assume:
 *   - a self-contained WAV file (REST fallback sends one per sentence; the first
 *     realtime frame carries the RIFF header) → parse header, take PCM after it
 *   - a headerless PCM16 continuation frame (later realtime frames) → raw samples
 * mp3 is handled by the caller via decodeAudioData (self-contained REST files).
 */

export interface DecodedPcm {
  samples: Float32Array // interleaved is collapsed to mono-or-first-channel below
  sampleRate: number
  channels: number
}

function readAscii(bytes: Uint8Array, off: number, len: number): string {
  let s = ''
  for (let i = 0; i < len; i++) s += String.fromCharCode(bytes[off + i])
  return s
}

/**
 * Parse a WAV header if present. Returns the PCM data offset, sample rate,
 * channels, and bit depth. Returns null when the bytes don't start with RIFF
 * (i.e. a headerless PCM continuation frame).
 */
export function parseWavHeader(
  bytes: Uint8Array,
): { dataOffset: number; sampleRate: number; channels: number; bitDepth: number } | null {
  if (bytes.length < 12) return null
  if (readAscii(bytes, 0, 4) !== 'RIFF' || readAscii(bytes, 8, 4) !== 'WAVE') return null
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let offset = 12
  let sampleRate = 0
  let channels = 1
  let bitDepth = 16
  while (offset + 8 <= bytes.length) {
    const chunkId = readAscii(bytes, offset, 4)
    const chunkSize = view.getUint32(offset + 4, true)
    if (chunkId === 'fmt ') {
      channels = view.getUint16(offset + 10, true) || 1
      sampleRate = view.getUint32(offset + 12, true)
      bitDepth = view.getUint16(offset + 22, true) || 16
    } else if (chunkId === 'data') {
      return { dataOffset: offset + 8, sampleRate, channels, bitDepth }
    }
    offset += 8 + chunkSize
    if (offset % 2 !== 0) offset++ // chunks are word-aligned
  }
  return null
}

/**
 * Convert PCM16 little-endian bytes (mono or interleaved) to a mono Float32Array
 * in [-1, 1]. For multi-channel input we average channels — a call is a single
 * voice, so this is transparent and keeps the AudioBuffer mono.
 */
export function pcm16ToFloat32Mono(bytes: Uint8Array, dataOffset: number, channels: number): Float32Array {
  const usableBytes = bytes.length - dataOffset
  const sampleCount = Math.floor(usableBytes / 2) // int16 samples across all channels
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const ch = Math.max(1, channels)
  const frames = Math.floor(sampleCount / ch)
  const out = new Float32Array(frames)
  for (let f = 0; f < frames; f++) {
    let acc = 0
    for (let c = 0; c < ch; c++) {
      const s = view.getInt16(dataOffset + (f * ch + c) * 2, true)
      acc += s < 0 ? s / 0x8000 : s / 0x7fff
    }
    out[f] = acc / ch
  }
  return out
}

/**
 * Decode one call audio chunk (wav-with-header OR headerless pcm16 frame) into
 * mono float samples + the sample rate to schedule at. `fallbackRate` is the
 * server-forwarded sample_rate, used when the frame has no header of its own.
 */
export function decodeCallChunk(bytes: Uint8Array, fallbackRate: number): DecodedPcm | null {
  const header = parseWavHeader(bytes)
  if (header) {
    if (header.bitDepth !== 16) return null // we only build 16-bit PCM buffers
    return {
      samples: pcm16ToFloat32Mono(bytes, header.dataOffset, header.channels),
      sampleRate: header.sampleRate || fallbackRate,
      channels: 1,
    }
  }
  // Headerless continuation frame: whole payload is interleaved PCM16 samples.
  if (!fallbackRate) return null // can't schedule without a known rate
  return {
    samples: pcm16ToFloat32Mono(bytes, 0, 1),
    sampleRate: fallbackRate,
    channels: 1,
  }
}
