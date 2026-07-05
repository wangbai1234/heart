import { create } from 'zustand'
import { concatAudioBase64 } from '../services/audioConcat'
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
  audioChunks?: { dataB64: string; durationMs: number; seq: number; format: 'wav' | 'mp3' }[]
}

export interface VadState {
  energy: number
  mood: string
  intimacy: number
}

function emptyMessages(): Record<CharacterId, Message[]> {
  return { rin: [], dorothy: [] }
}

interface ChatState {
  // Per-character threads (merged from conversationStore)
  threads: Record<CharacterId, ConversationMessage[]>
  activeCharacterId: CharacterId

  // Per-character streaming messages
  messages: Record<CharacterId, Message[]>
  isStreaming: boolean
  isPlaying: boolean
  currentTurnId: string | null
  vad: VadState
  characterId: string
  insufficientCredits: { needed: number; balance: number } | null
  clearedCharacters: Set<CharacterId>

  // Thread management (from conversationStore)
  setActiveCharacter: (id: CharacterId) => void
  appendMessage: (characterId: CharacterId, message: ConversationMessage) => void
  clearThread: (characterId: CharacterId) => void

  // Streaming management (from chatStore)
  addMessage: (characterId: CharacterId, msg: Message) => void
  appendToLast: (characterId: CharacterId, delta: string) => void
  setMessageAudio: (characterId: CharacterId, turnId: string, audioData: string, duration: number, format: string) => void
  appendMessageAudio: (
    characterId: CharacterId,
    turnId: string,
    dataB64: string,
    durationMs: number,
    seq: number,
    format: 'wav' | 'mp3',
  ) => void
  finalizeMessageAudio: (characterId: CharacterId, turnId: string) => void
  setStreaming: (v: boolean) => void
  setPlaying: (v: boolean) => void
  setCurrentTurnId: (id: string | null) => void
  setVad: (v: VadState) => void
  setCharacterId: (id: string) => void
  setInsufficientCredits: (needed: number, balance: number) => void
  clearInsufficientCredits: () => void
  clear: () => void
  clearMessages: (characterId: CharacterId) => void
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

  // Per-character streaming messages
  messages: emptyMessages(),
  isStreaming: false,
  isPlaying: false,
  currentTurnId: null,
  vad: { energy: 0, mood: 'neutral', intimacy: 0 },
  characterId: 'rin',
  insufficientCredits: null,
  clearedCharacters: new Set<CharacterId>(),

  // Thread management
  setActiveCharacter: (id) => set({ activeCharacterId: id }),
  appendMessage: (characterId, message) =>
    set((state) => {
      const cleared = new Set(state.clearedCharacters)
      cleared.delete(characterId)
      return {
        threads: {
          ...state.threads,
          [characterId]: [...state.threads[characterId], message],
        },
        clearedCharacters: cleared,
      }
    }),
  clearThread: (characterId) =>
    set((state) => ({
      threads: {
        ...state.threads,
        [characterId]: [],
      },
    })),

  // Streaming management — all keyed by characterId
  addMessage: (characterId, msg) =>
    set((s) => {
      const cleared = new Set(s.clearedCharacters)
      cleared.delete(characterId)
      return {
        messages: {
          ...s.messages,
          [characterId]: [...s.messages[characterId], msg],
        },
        clearedCharacters: cleared,
      }
    }),
  appendToLast: (characterId, delta) =>
    set((s) => {
      const msgs = [...s.messages[characterId]]
      const last = msgs[msgs.length - 1]
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + delta }
      }
      return { messages: { ...s.messages, [characterId]: msgs } }
    }),
  setMessageAudio: (characterId, turnId, audioData, duration, format) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [characterId]: s.messages[characterId].map(m =>
          m.id === turnId
            ? { ...m, audioData, audioDuration: duration, audioFormat: format }
            : m
        ),
      },
    })),
  appendMessageAudio: (characterId, turnId, dataB64, durationMs, seq, format) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [characterId]: s.messages[characterId].map(m => {
          if (m.id !== turnId) return m
          const chunks = m.audioChunks ? [...m.audioChunks] : []
          chunks.push({ dataB64, durationMs, seq, format })
          chunks.sort((a, b) => a.seq - b.seq)
          return { ...m, audioChunks: chunks, audioFormat: format }
        }),
      },
    })),
  finalizeMessageAudio: (characterId, turnId) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [characterId]: s.messages[characterId].map(m => {
          if (m.id !== turnId || !m.audioChunks || m.audioChunks.length === 0) return m
          const format = m.audioChunks[0].format
          const { dataB64, durationMs } = concatAudioBase64(m.audioChunks, format)
          return { ...m, audioData: dataB64, audioDuration: durationMs, audioFormat: format }
        }),
      },
    })),
  setStreaming: (v) => set({ isStreaming: v }),
  setPlaying: (v) => set({ isPlaying: v }),
  setCurrentTurnId: (id) => set({ currentTurnId: id }),
  setVad: (v) => set({ vad: v }),
  setCharacterId: (id) => set({ characterId: id }),
  setInsufficientCredits: (needed, balance) => set({ insufficientCredits: { needed, balance } }),
  clearInsufficientCredits: () => set({ insufficientCredits: null }),
  clear: () => set((s) => ({ messages: emptyMessages(), isStreaming: false, isPlaying: false, currentTurnId: null, characterId: s.characterId, insufficientCredits: null })),
  clearMessages: (characterId) =>
    set((s) => {
      const cleared = new Set(s.clearedCharacters)
      cleared.add(characterId)
      return {
        messages: { ...s.messages, [characterId]: [] },
        clearedCharacters: cleared,
        isStreaming: false,
        isPlaying: false,
        currentTurnId: null,
        insufficientCredits: null,
      }
    }),
}))
