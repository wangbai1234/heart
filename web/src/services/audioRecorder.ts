/**
 * Convert any audio Blob to a 16kHz mono 16-bit PCM WAV Blob.
 * MIMO ASR only accepts WAV/MP3; browsers record webm/opus or mp4,
 * so we decode via AudioContext and re-encode before uploading.
 */
export async function blobToWav16k(blob: Blob): Promise<Blob> {
  const audioCtx = new AudioContext()
  try {
    const arrayBuffer = await blob.arrayBuffer()
    const decoded = await audioCtx.decodeAudioData(arrayBuffer)

    const targetSampleRate = 16000
    const numChannels = 1
    const numFrames = Math.ceil((decoded.length * targetSampleRate) / decoded.sampleRate)

    const offlineCtx = new OfflineAudioContext(numChannels, numFrames, targetSampleRate)
    const source = offlineCtx.createBufferSource()
    source.buffer = decoded
    source.connect(offlineCtx.destination)
    source.start(0)

    const rendered = await offlineCtx.startRendering()
    const pcmData = rendered.getChannelData(0)

    return encodePcmToWav(pcmData, targetSampleRate)
  } finally {
    audioCtx.close()
  }
}

function encodePcmToWav(pcmFloat32: Float32Array, sampleRate: number): Blob {
  const numSamples = pcmFloat32.length
  const bytesPerSample = 2
  const dataSize = numSamples * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  // RIFF header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')

  // fmt chunk
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)          // chunk size
  view.setUint16(20, 1, true)           // PCM
  view.setUint16(22, 1, true)           // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * bytesPerSample, true) // byte rate
  view.setUint16(32, bytesPerSample, true)              // block align
  view.setUint16(34, 16, true)          // bits per sample

  // data chunk
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  // PCM samples (float32 → int16)
  let offset = 44
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, pcmFloat32[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}
