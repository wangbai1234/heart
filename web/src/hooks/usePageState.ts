import { useState, useCallback } from 'react'

export type PageState =
  | 'loading'
  | 'loaded'
  | 'empty'
  | 'offline'
  | 'error'
  | 'transition'

interface UsePageStateReturn {
  state: PageState
  setState: (s: PageState) => void
  isLoading: boolean
  isLoaded: boolean
  isEmpty: boolean
  isOffline: boolean
  isError: boolean
  showDialog: boolean
  showToast: boolean
  showBottomSheet: boolean
  toastMessage: string
  setShowDialog: (v: boolean) => void
  triggerToast: (msg: string) => void
  setShowBottomSheet: (v: boolean) => void
}

export function usePageState(initial: PageState = 'loaded'): UsePageStateReturn {
  const [state, setState] = useState<PageState>(initial)
  const [showDialog, setShowDialog] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [showBottomSheet, setShowBottomSheet] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  const triggerToast = useCallback((msg: string) => {
    setToastMessage(msg)
    setShowToast(true)
    setTimeout(() => setShowToast(false), 2200)
  }, [])

  return {
    state,
    setState,
    isLoading: state === 'loading',
    isLoaded: state === 'loaded',
    isEmpty: state === 'empty',
    isOffline: state === 'offline',
    isError: state === 'error',
    showDialog,
    showToast,
    showBottomSheet,
    toastMessage,
    setShowDialog,
    triggerToast,
    setShowBottomSheet,
  }
}
