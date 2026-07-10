import { useState, useEffect } from 'react'

interface VisualViewportState {
  height: number
  keyboardOpen: boolean
  keyboardHeight: number
}

export function useVisualViewport(): VisualViewportState {
  const [state, setState] = useState<VisualViewportState>(() => ({
    height: window.visualViewport?.height ?? window.innerHeight,
    keyboardOpen: false,
    keyboardHeight: 0,
  }))

  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return

    const update = () => {
      const vvHeight = vv.height
      const windowHeight = window.innerHeight
      // Keyboard is open when visualViewport is significantly shorter than window
      const kbHeight = Math.max(0, windowHeight - vvHeight)
      setState({
        height: vvHeight,
        keyboardOpen: kbHeight > 80,
        keyboardHeight: kbHeight,
      })
    }

    vv.addEventListener('resize', update)
    vv.addEventListener('scroll', update)
    update()
    return () => {
      vv.removeEventListener('resize', update)
      vv.removeEventListener('scroll', update)
    }
  }, [])

  return state
}
