import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { concatAudioBase64 } from '../services/audioConcat'
import { type CharacterId, type ConversationMessage } from '../data/uiContent'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  kind?: 'text' | 'voice' | 'action'
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
  lastFetchedAt: Record<string, number>
  // Per-character: a turn is in flight (from turn_start until turn_end/error).
  // Keyed by characterId so one character's turn never drives another's page
  // indicator or blocks sending to a different character.
  isStreaming: Record<string, boolean>
  isPlaying: boolean
  currentTurnId: string | null
  pendingAssistantTurnId: string | null
  vad: VadState
  characterId: string
  insufficientCredits: { needed: number; balance: number } | null
  modelForbidden: { model: string; tier: string } | null
  clearedCharacters: Set<CharacterId>

  isGenerating: Record<string, boolean>

  setLastFetchedAt: (characterId: string, ts: number) => void
  setGenerating: (cid: string, val: boolean) => void

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
  setStreaming: (cid: string, v: boolean) => void
  setPlaying: (v: boolean) => void
  setCurrentTurnId: (id: string | null) => void
  setPendingAssistantTurnId: (id: string | null) => void
  setVad: (v: VadState) => void
  setCharacterId: (id: string) => void
  setInsufficientCredits: (needed: number, balance: number) => void
  clearInsufficientCredits: () => void
  setModelForbidden: (model: string, tier: string) => void
  clearModelForbidden: () => void
  clear: () => void
  clearMessages: (characterId: CharacterId) => void
}

function cloneThreads(): Record<CharacterId, ConversationMessage[]> {
  return {
    rin: [],
    dorothy: [],
  }
}

export const useChatStore = create<ChatState>()(
  persist(
  (set) => ({
  // Per-character threads
  threads: cloneThreads(),
  activeCharacterId: 'rin',

  // Per-character streaming messages
  messages: emptyMessages(),
  lastFetchedAt: {},
  isGenerating: {},
  isStreaming: {},
  isPlaying: false,
  currentTurnId: null,
  pendingAssistantTurnId: null,
  vad: { energy: 0, mood: 'neutral', intimacy: 0 },
  characterId: 'rin',
  insufficientCredits: null,
  modelForbidden: null,
  clearedCharacters: new Set<CharacterId>(),

  setLastFetchedAt: (characterId, ts) =>
    set((s) => ({ lastFetchedAt: { ...s.lastFetchedAt, [characterId]: ts } })),
  setGenerating: (cid, val) =>
    set((s) => ({ isGenerating: { ...s.isGenerating, [cid]: val } })),

  // Thread management
  setActiveCharacter: (id) => set({ activeCharacterId: id }),
  appendMessage: (characterId, message) =>
    set((state) => {
      const cleared = new Set(state.clearedCharacters)
      cleared.delete(characterId)
      return {
        threads: {
          ...state.threads,
          [characterId]: [...(state.threads[characterId] ?? []), message],
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
          [characterId]: [...(s.messages[characterId] ?? []), msg],
        },
        clearedCharacters: cleared,
      }
    }),
  appendToLast: (characterId, delta) =>
    set((s) => {
      const msgs = [...(s.messages[characterId] ?? [])]
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
        [characterId]: (s.messages[characterId] ?? []).map(m =>
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
        [characterId]: (s.messages[characterId] ?? []).map(m => {
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
        [characterId]: (s.messages[characterId] ?? []).map(m => {
          if (m.id !== turnId || !m.audioChunks || m.audioChunks.length === 0) return m
          const format = m.audioChunks[0].format
          const { dataB64, durationMs } = concatAudioBase64(m.audioChunks, format)
          return { ...m, audioData: dataB64, audioDuration: durationMs, audioFormat: format }
        }),
      },
    })),
  setStreaming: (cid, v) =>
    set((s) => ({ isStreaming: { ...s.isStreaming, [cid]: v } })),
  setPlaying: (v) => set({ isPlaying: v }),
  setCurrentTurnId: (id) => set({ currentTurnId: id }),
  setPendingAssistantTurnId: (id) => set({ pendingAssistantTurnId: id }),
  setVad: (v) => set({ vad: v }),
  setCharacterId: (id) => set({ characterId: id }),
  setInsufficientCredits: (needed, balance) => set({ insufficientCredits: { needed, balance } }),
  clearInsufficientCredits: () => set({ insufficientCredits: null }),
  setModelForbidden: (model, tier) => set({ modelForbidden: { model, tier } }),
  clearModelForbidden: () => set({ modelForbidden: null }),
  clear: () => set((s) => ({ messages: emptyMessages(), isStreaming: {}, isPlaying: false, currentTurnId: null, characterId: s.characterId, insufficientCredits: null })),
  clearMessages: (characterId) =>
    set((s) => {
      const cleared = new Set(s.clearedCharacters)
      cleared.add(characterId)
      return {
        messages: { ...s.messages, [characterId]: [] },
        clearedCharacters: cleared,
        isStreaming: { ...s.isStreaming, [characterId]: false },
        isPlaying: false,
        isGenerating: { ...s.isGenerating, [characterId]: false },
        currentTurnId: null,
        pendingAssistantTurnId: null,
        insufficientCredits: null,
      }
    }),
  }),
  {
    name: 'yuoyuo-chat',
    partialize: (state) => ({
      messages: Object.fromEntries(
        Object.entries(state.messages).map(([cid, msgs]) => [
          cid,
          msgs.map((m) => ({ ...m, audioData: undefined, audioChunks: undefined })),
        ])
      ),
      threads: state.threads,
      lastFetchedAt: state.lastFetchedAt,
    }),
  }
))
