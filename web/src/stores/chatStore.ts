import { create } from 'zustand'
import { concatWavBase64 } from '../services/audioConcat'
import { type CharacterId, type ConversationMessage } from '../data/uiContent'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  kind?: 'text' | 'voice'
  duration?: string
  audioData?: string
  audioDuration?: number
  audioFormat?: string
  audioChunks?: { dataB64: string; durationMs: number; seq: number }[]
}

export interface VadState {
  energy: number
  mood: string
  intimacy: number
}

interface ChatState {
  // Per-character threads (merged from conversationStore)
  threads: Record<CharacterId, ConversationMessage[]>
  activeCharacterId: CharacterId

  // Real-time streaming state (from chatStore)
  messages: Message[]
  isStreaming: boolean
  isPlaying: boolean
  currentTurnId: string | null
  vad: VadState
  characterId: string
  insufficientCredits: { needed: number; balance: number } | null

  // Thread management (from conversationStore)
  setActiveCharacter: (id: CharacterId) => void
  appendMessage: (characterId: CharacterId, message: ConversationMessage) => void
  clearThread: (characterId: CharacterId) => void

  // Streaming management (from chatStore)
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
  setInsufficientCredits: (needed: number, balance: number) => void
  clearInsufficientCredits: () => void
  clear: () => void
  clearMessages: () => void
}

function cloneThreads(): Record<CharacterId, ConversationMessage[]> {
  return {
    rin: [],
    dorothy: [],
  }
}

export const useChatStore = create<ChatState>((set) => ({
  // Per-character threads
  threads: cloneThreads(),
  activeCharacterId: 'rin',

  // Streaming state
  messages: [],
  isStreaming: false,
  isPlaying: false,
  currentTurnId: null,
  vad: { energy: 0, mood: 'neutral', intimacy: 0 },
  characterId: 'rin',
  insufficientCredits: null,

  // Thread management
  setActiveCharacter: (id) => set({ activeCharacterId: id }),
  appendMessage: (characterId, message) =>
    set((state) => ({
      threads: {
        ...state.threads,
        [characterId]: [...state.threads[characterId], message],
      },
    })),
  clearThread: (characterId) =>
    set((state) => ({
      threads: {
        ...state.threads,
        [characterId]: [],
      },
    })),

  // Streaming management
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
  setInsufficientCredits: (needed, balance) => set({ insufficientCredits: { needed, balance } }),
  clearInsufficientCredits: () => set({ insufficientCredits: null }),
  clear: () => set((s) => ({ messages: [], isStreaming: false, isPlaying: false, currentTurnId: null, characterId: s.characterId, insufficientCredits: null })),
  clearMessages: () => set({ messages: [], isStreaming: false, isPlaying: false, currentTurnId: null, insufficientCredits: null }),
}))
