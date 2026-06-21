export interface AudioPlayer {
  init(): Promise<void>
  enqueue(chunk: ArrayBuffer): void
  flush(): void
  stop(): void
  isAlive(): boolean
  getAnalyser(): AnalyserNode | null
  onBufferedMs(cb: (ms: number) => void): void
}

class MSEAudioPlayer implements AudioPlayer {
  private mediaSource: MediaSource | null = null
  private sourceBuffer: SourceBuffer | null = null
  private audio: HTMLAudioElement
  private queue: ArrayBuffer[] = []
  private appending = false
  private stopped = false
  private bufferedMsCb: ((ms: number) => void) | null = null
  private audioCtx: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private objectUrl: string | null = null

  constructor() {
    this.audio = new Audio()
    this.audio.autoplay = true
  }

  async init(): Promise<void> {
    this.stopped = false
    this.mediaSource = new MediaSource()
    this.objectUrl = URL.createObjectURL(this.mediaSource)
    this.audio.src = this.objectUrl

    return new Promise<void>((resolve) => {
      this.mediaSource!.addEventListener('sourceopen', () => {
        this.sourceBuffer = this.mediaSource!.addSourceBuffer('audio/mpeg')
        this.sourceBuffer.addEventListener('updateend', () => {
          this.appending = false
          if (this.stopped) return
          this._drainQueue()
        })
        this._setupAnalyser()
        resolve()
      }, { once: true })
    })
  }

  private _setupAnalyser(): void {
    try {
      this.audioCtx = new AudioContext()
      const source = this.audioCtx.createMediaElementSource(this.audio)
      this.analyser = this.audioCtx.createAnalyser()
      this.analyser.fftSize = 256
      source.connect(this.analyser)
      this.analyser.connect(this.audioCtx.destination)
    } catch {
      // MediaElementSource already connected — ignore
    }
  }

  enqueue(chunk: ArrayBuffer): void {
    if (this.stopped) return
    this.queue.push(chunk)
    this._drainQueue()
  }

  private _drainQueue(): void {
    if (this.appending || !this.sourceBuffer || this.queue.length === 0) return
    if (this.sourceBuffer.updating) return

    this.appending = true
    const buf = this.queue.shift()!
    try {
      this.sourceBuffer.appendBuffer(buf)
    } catch {
      this.appending = false
    }

    this._reportBuffered()
  }

  private _reportBuffered(): void {
    if (!this.bufferedMsCb) return
    const sb = this.sourceBuffer
    if (sb && sb.buffered.length > 0) {
      const end = sb.buffered.end(sb.buffered.length - 1)
      const current = this.audio.currentTime
      this.bufferedMsCb((end - current) * 1000)
    }
  }

  flush(): void {
    // no-op for MSE — browser handles end of stream
  }

  stop(): void {
    this.stopped = true
    this.queue = []
    this.appending = false
    try { this.audio.pause() } catch { /* ignore */ }
    try { this.audio.currentTime = 0 } catch { /* ignore */ }
    try { this.audio.removeAttribute('src'); this.audio.load() } catch { /* ignore */ }
    try {
      if (this.objectUrl) {
        URL.revokeObjectURL(this.objectUrl)
        this.objectUrl = null
      }
    } catch { /* ignore */ }
    try {
      if (this.mediaSource?.readyState === 'open' && this.sourceBuffer && !this.sourceBuffer.updating) {
        this.sourceBuffer.abort()
        this.mediaSource.endOfStream()
      } else if (this.sourceBuffer?.updating) {
        this.sourceBuffer.abort()
      }
    } catch { /* ignore */ }
    try { this.audioCtx?.close() } catch { /* ignore */ }
    this.sourceBuffer = null
    this.mediaSource = null
    this.audioCtx = null
    this.analyser = null
  }

  isAlive(): boolean {
    return this.sourceBuffer !== null && !this.stopped
  }

  getAnalyser(): AnalyserNode | null {
    return this.analyser
  }

  onBufferedMs(cb: (ms: number) => void): void {
    this.bufferedMsCb = cb
  }
}

class WebAudioPlayer implements AudioPlayer {
  private audioCtx: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private sources: AudioBufferSourceNode[] = []
  private nextTime = 0
  private stopped = false
  private bufferedMsCb: ((ms: number) => void) | null = null

  async init(): Promise<void> {
    this.audioCtx = new AudioContext()
    this.analyser = this.audioCtx.createAnalyser()
    this.analyser.fftSize = 256
    this.analyser.connect(this.audioCtx.destination)
    this.nextTime = this.audioCtx.currentTime
  }

  enqueue(chunk: ArrayBuffer): void {
    if (!this.audioCtx || this.stopped) return

    this.audioCtx.decodeAudioData(chunk.slice(0)).then((audioBuffer) => {
      if (this.stopped || !this.audioCtx || !this.analyser) return

      const source = this.audioCtx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(this.analyser)

      const now = this.audioCtx.currentTime
      const overlapSec = 0.005 // 5ms overlap for smoother transitions
      const startTime = Math.max(this.nextTime - overlapSec, now)
      source.start(startTime)
      this.nextTime = startTime + audioBuffer.duration
      this.sources.push(source)

      source.onended = () => {
        const idx = this.sources.indexOf(source)
        if (idx >= 0) this.sources.splice(idx, 1)
      }

      this._reportBuffered()
    }).catch(() => {
      // decode error — skip chunk
    })
  }

  private _reportBuffered(): void {
    if (!this.bufferedMsCb || !this.audioCtx) return
    const bufferedMs = Math.max(0, (this.nextTime - this.audioCtx.currentTime) * 1000)
    this.bufferedMsCb(bufferedMs)
  }

  flush(): void {
    // nothing to flush — Web Audio plays on schedule
  }

  stop(): void {
    this.stopped = true
    for (const s of this.sources) {
      try { s.stop() } catch { /* already stopped */ }
    }
    this.sources = []
    this.nextTime = 0
    try { this.audioCtx?.close() } catch { /* ignore */ }
    this.audioCtx = null
    this.analyser = null
  }

  isAlive(): boolean {
    return this.audioCtx !== null
  }

  getAnalyser(): AnalyserNode | null {
    return this.analyser
  }

  onBufferedMs(cb: (ms: number) => void): void {
    this.bufferedMsCb = cb
  }
}

export function createAudioPlayer(format?: string): AudioPlayer {
  // MSE doesn't support audio/wav, so use WebAudio for PCM16/WAV format.
  if (format === 'pcm16' || typeof MediaSource === 'undefined') {
    return new WebAudioPlayer()
  }
  return new MSEAudioPlayer()
}

export function wrapPCM16AsWAV(
  pcmData: ArrayBuffer,
  sampleRate: number = 24000,
  numChannels: number = 1,
  bitsPerSample: number = 16,
): ArrayBuffer {
  const dataLength = pcmData.byteLength
  const headerLength = 44
  const totalLength = headerLength + dataLength
  const buffer = new ArrayBuffer(totalLength)
  const view = new DataView(buffer)

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, totalLength - 8, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true)
  view.setUint16(32, numChannels * bitsPerSample / 8, true)
  view.setUint16(34, bitsPerSample, true)
  writeString(36, 'data')
  view.setUint32(40, dataLength, true)

  new Uint8Array(buffer).set(new Uint8Array(pcmData), headerLength)
  return buffer
}
