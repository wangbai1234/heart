/**
 * 克隆音频预处理 — 浏览器端把任意输入（大 mp3 / m4a / 视频）压成小体积 WAV。
 *
 * 为什么不是「mp3 转 wav」：WAV 是无压缩 PCM，同一段音频转 WAV 只会更大。
 * 真正让上传变小的是「降采样 + 单声道 + 裁剪时长」。克隆只需要 10–30 秒、
 * 16kHz 单声道就足够，处理后一段 30 秒样本约 ~1MB，从根源避免上传失败。
 *
 * 流程：decodeAudioData → OfflineAudioContext 重采样(16kHz/mono) → 裁到 30s → WAV。
 * 视频文件（video/*）同样能被 decodeAudioData 抽出音轨（Chrome/Safari 支持常见容器）。
 */

const TARGET_SAMPLE_RATE = 16000
const MAX_DURATION_SEC = 30

export interface ProcessedAudio {
  file: File
  durationSec: number
  fromVideo: boolean
}

export function isVideoFile(file: File): boolean {
  return file.type.startsWith('video/') || /\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(file.name)
}

function getAudioContext(): typeof AudioContext | null {
  const w = window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }
  return w.AudioContext ?? w.webkitAudioContext ?? null
}

/** 浏览器是否支持预处理（老浏览器无 AudioContext 时回退到直传原文件）。 */
export function canPreprocess(): boolean {
  return getAudioContext() !== null && typeof OfflineAudioContext !== 'undefined'
}

/**
 * 解码 → 重采样到 16kHz 单声道 → 裁到 30s → 编码 WAV。
 * 抛错时调用方应回退到直传原文件（见 uploadVoiceClone 的兜底）。
 */
export async function preprocessForClone(file: File): Promise<ProcessedAudio> {
  const AC = getAudioContext()
  if (!AC || typeof OfflineAudioContext === 'undefined') {
    throw new Error('unsupported')
  }
  const fromVideo = isVideoFile(file)
  const arrayBuf = await file.arrayBuffer()

  // decodeAudioData 会从音频/视频容器里解出 PCM。用一次性 AudioContext 只为解码。
  const decodeCtx = new AC()
  let decoded: AudioBuffer
  try {
    decoded = await decodeCtx.decodeAudioData(arrayBuf.slice(0))
  } finally {
    void decodeCtx.close()
  }

  const srcRate = decoded.sampleRate
  const keepFrames = Math.min(decoded.length, Math.floor(MAX_DURATION_SEC * srcRate))
  const outFrames = Math.ceil((keepFrames / srcRate) * TARGET_SAMPLE_RATE)

  // 离线渲染做重采样 + 降到单声道；只取前 keepFrames 完成裁剪。
  const offline = new OfflineAudioContext(1, outFrames, TARGET_SAMPLE_RATE)
  const source = offline.createBufferSource()
  const shortBuf = offline.createBuffer(decoded.numberOfChannels, keepFrames, srcRate)
  for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
    shortBuf.copyToChannel(decoded.getChannelData(ch).subarray(0, keepFrames), ch)
  }
  source.buffer = shortBuf
  source.connect(offline.destination)
  source.start(0)
  const rendered = await offline.startRendering()

  const wav = encodeWav(rendered.getChannelData(0), TARGET_SAMPLE_RATE)
  const baseName = file.name.replace(/\.[^.]+$/, '') || 'clone'
  const outFile = new File([wav], `${baseName}.wav`, { type: 'audio/wav' })
  return { file: outFile, durationSec: rendered.duration, fromVideo }
}

/** 单声道 Float32 PCM → 16-bit PCM WAV（含 44 字节头）。 */
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const bytesPerSample = 2
  const dataLen = samples.length * bytesPerSample
  const buf = new ArrayBuffer(44 + dataLen)
  const view = new DataView(buf)

  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + dataLen, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true) // PCM chunk size
  view.setUint16(20, 1, true) // PCM format
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * bytesPerSample, true) // byte rate
  view.setUint16(32, bytesPerSample, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  writeStr(36, 'data')
  view.setUint32(40, dataLen, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += bytesPerSample
  }
  return buf
}
