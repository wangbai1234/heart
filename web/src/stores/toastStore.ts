import { create } from 'zustand'

export type ToastVariant = 'info' | 'error' | 'success'

export interface ToastItem {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastState {
  toasts: ToastItem[]
  /** Enqueue a toast. Identical messages already visible are coalesced. */
  show: (message: string, variant?: ToastVariant) => void
  dismiss: (id: string) => void
}

let seq = 0

/**
 * Global toast queue. Usable from React (`useToastStore(s => ...)`) and from
 * non-React callers (`useToastStore.getState().show(...)`) such as the
 * WebSocket hook and the API layer, which previously had no way to surface
 * failures to the user (SUG-1).
 */
export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  show: (message, variant = 'info') => {
    if (!message) return
    seq += 1
    const id = `toast-${seq}`
    set((state) => {
      // Coalesce: don't stack the same message if it's already on screen.
      if (state.toasts.some((t) => t.message === message)) return state
      return { toasts: [...state.toasts, { id, message, variant }] }
    })
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}))
