import { create } from 'zustand'
import { concatWavBase64 } from '../services/audioConcat'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  audioData?: string      // base64 WAV 音频（完整拼接后）
  audioDuration?: number  // 时长（毫秒）
  audioFormat?: string    // "wav" | "mp3"
  audioChunks?: { dataB64: string; durationMs: number; seq: number }[]  // 逐句音频片段
}

export interface VadState {
  energy: number
  mood: string
  intimacy: number
}

interface ChatState {
  messages: Message[]
  isStreaming: boolean
  isPlaying: boolean
  currentTurnId: string | null
  vad: VadState
  characterId: string
  addMessage: (msg: Message) => void
  appendToLast: (delta: string) => void
  setMessageAudio: (turnId: string, audioData: string, duration: number, format: string) => void
  appendMessageAudio: (turnId: string, dataB64: string, durationMs: number, seq: number) => void
  finalizeMessageAudio: (turnId: string) => void
  setStreaming: (v: boolean) => void
  setPlaying: (v: boolean) => void
  setCurrentTurnId: (id: string | null) => void
  setVad: (v: VadState) => void
  setCharacterId: (id: string) => void
  clear: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  isPlaying: false,
  currentTurnId: null,
  vad: { energy: 0, mood: 'neutral', intimacy: 0 },
  characterId: 'rin',
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendToLast: (delta) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + delta }
      }
      return { messages: msgs }
    }),
  setMessageAudio: (turnId, audioData, duration, format) =>
    set((s) => ({
      messages: s.messages.map(m =>
        m.id === turnId
          ? { ...m, audioData, audioDuration: duration, audioFormat: format }
          : m
      ),
    })),
  appendMessageAudio: (turnId, dataB64, durationMs, seq) =>
    set((s) => ({
      messages: s.messages.map(m => {
        if (m.id !== turnId) return m
        const chunks = m.audioChunks ? [...m.audioChunks] : []
        chunks.push({ dataB64, durationMs, seq })
        chunks.sort((a, b) => a.seq - b.seq)
        return { ...m, audioChunks: chunks }
      }),
    })),
  finalizeMessageAudio: (turnId) =>
    set((s) => ({
      messages: s.messages.map(m => {
        if (m.id !== turnId || !m.audioChunks || m.audioChunks.length === 0) return m
        const { dataB64, durationMs } = concatWavBase64(m.audioChunks)
        return { ...m, audioData: dataB64, audioDuration: durationMs, audioFormat: 'wav' }
      }),
    })),
  setStreaming: (v) => set({ isStreaming: v }),
  setPlaying: (v) => set({ isPlaying: v }),
  setCurrentTurnId: (id) => set({ currentTurnId: id }),
  setVad: (v) => set({ vad: v }),
  setCharacterId: (id) => set({ characterId: id }),
  clear: () => set({ messages: [], isStreaming: false, isPlaying: false, currentTurnId: null, characterId: 'rin' }),
}))
