/**
 * WAV base64 拼接工具 — 将多个 WAV base64 片段合并为一个完整 WAV。
 *
 * 假设所有片段具有相同的采样率、位深和声道数（均由 MiMo API 以 24kHz/16bit/mono 输出）。
 */

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes
}

function bytesToB64(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

function concatBinaryBase64(chunks: { dataB64: string; durationMs: number }[]) {
  if (chunks.length === 0) return { dataB64: '', durationMs: 0 }
  if (chunks.length === 1) return chunks[0]

  const parts = chunks.map((chunk) => b64ToBytes(chunk.dataB64))
  const totalLength = parts.reduce((sum, part) => sum + part.length, 0)
  const output = new Uint8Array(totalLength)

  let offset = 0
  for (const part of parts) {
    output.set(part, offset)
    offset += part.length
  }

  return {
    dataB64: bytesToB64(output),
    durationMs: chunks.reduce((sum, chunk) => sum + chunk.durationMs, 0),
  }
}

/**
 * 从 WAV 文件头中解析出 header 长度（通常 44 字节，但可能有 extra fmt chunk）。
 */
function wavHeaderLength(bytes: Uint8Array): number {
  // RIFF header: 4 bytes "RIFF" + 4 bytes size + 4 bytes "WAVE"
  // Then chunks follow. The "fmt " chunk tells us where data starts.
  if (bytes.length < 12) return 44 // fallback
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)

  // Find "data" chunk
  let offset = 12 // skip RIFF + WAVE
  while (offset + 8 <= bytes.length) {
    const chunkId = String.fromCharCode(bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3])
    const chunkSize = view.getUint32(offset + 4, true)
    if (chunkId === 'data') {
      return offset + 8 // header ends where data begins
    }
    offset += 8 + chunkSize
    if (offset % 2 !== 0) offset++ // chunks are word-aligned
  }
  return 44 // fallback
}

/**
 * 将多个 base64 WAV 片段拼接为一个 base64 WAV。
 * 第一个片段的 header 作为输出 header，后续片段只取 PCM data 部分。
 */
export function concatWavBase64(chunks: { dataB64: string; durationMs: number }[]): {
  dataB64: string
  durationMs: number
} {
  if (chunks.length === 0) return { dataB64: '', durationMs: 0 }
  if (chunks.length === 1) return chunks[0]

  const firstBytes = b64ToBytes(chunks[0].dataB64)
  const headerLen = wavHeaderLength(firstBytes)
  const header = firstBytes.slice(0, headerLen)

  // Collect PCM data from all chunks
  const pcmParts: Uint8Array[] = []
  let totalDurationMs = 0

  for (const chunk of chunks) {
    const bytes = b64ToBytes(chunk.dataB64)
    const hdrLen = wavHeaderLength(bytes)
    pcmParts.push(bytes.slice(hdrLen))
    totalDurationMs += chunk.durationMs
  }

  // Calculate total PCM data length
  let totalPcmLen = 0
  for (const part of pcmParts) totalPcmLen += part.length

  // Build output: header + all PCM data
  const output = new Uint8Array(headerLen + totalPcmLen)
  output.set(header, 0)

  // Patch the RIFF chunk size field (bytes 4-7, little-endian)
  const view = new DataView(output.buffer)
  view.setUint32(4, output.length - 8, true)

  // Patch the data chunk size field (at headerLen - 4 to headerLen)
  view.setUint32(headerLen - 4, totalPcmLen, true)

  let offset = headerLen
  for (const part of pcmParts) {
    output.set(part, offset)
    offset += part.length
  }

  return { dataB64: bytesToB64(output), durationMs: totalDurationMs }
}

export function concatAudioBase64(
  chunks: { dataB64: string; durationMs: number }[],
  format: 'wav' | 'mp3',
): {
  dataB64: string
  durationMs: number
} {
  return format === 'wav' ? concatWavBase64(chunks) : concatBinaryBase64(chunks)
}
