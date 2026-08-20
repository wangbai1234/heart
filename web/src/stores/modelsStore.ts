import { create } from 'zustand'
import { getModels, type ChatModelInfo } from '../services/api'

interface ModelsState {
  models: ChatModelInfo[]
  defaultModel: string
  loading: boolean
  loaded: boolean
  refresh: () => Promise<void>
}

export const useModelsStore = create<ModelsState>((set) => ({
  models: [],
  defaultModel: 'gemini-3.1',
  loading: false,
  loaded: false,
  refresh: async () => {
    set({ loading: true })
    try {
      const result = await getModels()
      set({ models: result.models, defaultModel: result.default_model, loaded: true })
    } finally {
      set({ loading: false })
    }
  },
}))
