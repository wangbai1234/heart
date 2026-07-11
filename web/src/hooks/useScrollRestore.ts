import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Saves and restores the scroll position of a scrollable container across
 * SPA navigations.  Attach the returned ref to the scrollable element.
 *
 * Scroll positions are keyed by the current pathname (+ optional suffix) and
 * stored in sessionStorage so they survive React unmounts but reset on new
 * browser sessions.
 *
 * @param suffix Optional extra key segment (e.g. a character id) to
 *               differentiate positions for the same route with different data.
 */
export function useScrollRestore(suffix?: string) {
  const { pathname } = useLocation()
  const key = `scroll:${pathname}${suffix ? `:${suffix}` : ''}`
  const ref = useRef<HTMLElement | null>(null)
  const savedRef = useRef(false)

  // Restore on mount
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const saved = sessionStorage.getItem(key)
    if (saved !== null) {
      el.scrollTop = Number(saved)
    }

    const save = () => {
      if (ref.current && !savedRef.current) {
        sessionStorage.setItem(key, String(ref.current.scrollTop))
      }
    }

    el.addEventListener('scroll', save, { passive: true })
    return () => {
      el.removeEventListener('scroll', save)
      // Save on unmount (covers back-navigation)
      if (ref.current) {
        sessionStorage.setItem(key, String(ref.current.scrollTop))
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return ref as React.RefObject<HTMLDivElement>
}
