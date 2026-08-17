import { useEffect, useRef, useState } from 'react'

/**
 * Pull-to-refresh for a scrollable container (mobile / PWA).
 *
 * Attach the returned `bind` ref to the same scroll element you already scroll.
 * When the user drags down while the container is at the very top, a pull
 * distance accumulates (damped) until it passes `threshold`; releasing there
 * runs `onRefresh` and shows a spinner until the promise settles.
 *
 * Touch-only by design: desktop uses focus/visibility refresh + no gesture, so
 * we never hijack mouse drags or wheel scrolling.
 *
 * @param onRefresh  async work to run on release-past-threshold.
 * @param threshold  px of pull needed to trigger (default 64).
 */
export function usePullToRefresh(
  onRefresh: () => Promise<void> | void,
  threshold = 64,
) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  // Keep the latest callback without re-binding listeners every render.
  const onRefreshRef = useRef(onRefresh)
  onRefreshRef.current = onRefresh
  const refreshingRef = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    let startY = 0
    let pulling = false

    const onTouchStart = (e: TouchEvent) => {
      // Only arm the gesture when already scrolled to the top and idle.
      if (el.scrollTop <= 0 && !refreshingRef.current && e.touches.length === 1) {
        startY = e.touches[0].clientY
        pulling = true
      } else {
        pulling = false
      }
    }

    const onTouchMove = (e: TouchEvent) => {
      if (!pulling) return
      const dy = e.touches[0].clientY - startY
      if (dy <= 0) {
        // Scrolling up / normal scroll — cancel the pull.
        setPull(0)
        pulling = false
        return
      }
      // The container is at top and the finger moves down: this is a pull, not a
      // scroll. Prevent the native rubber-band so the indicator drives feedback.
      if (e.cancelable) e.preventDefault()
      // Rubber-band damping: the further you pull, the harder it gets.
      const damped = Math.min(dy * 0.5, threshold * 1.8)
      setPull(damped)
    }

    const onTouchEnd = () => {
      if (!pulling) return
      pulling = false
      setPull((current) => {
        if (current >= threshold && !refreshingRef.current) {
          refreshingRef.current = true
          setRefreshing(true)
          Promise.resolve(onRefreshRef.current())
            .catch(() => { /* swallow — the store keeps prior data */ })
            .finally(() => {
              refreshingRef.current = false
              setRefreshing(false)
              setPull(0)
            })
          return threshold // hold the indicator open while refreshing
        }
        return 0
      })
    }

    // touchmove must be non-passive so preventDefault can suppress rubber-band.
    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    el.addEventListener('touchend', onTouchEnd, { passive: true })
    el.addEventListener('touchcancel', onTouchEnd, { passive: true })
    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
      el.removeEventListener('touchcancel', onTouchEnd)
    }
  }, [threshold])

  return { bind: ref, pull, refreshing, threshold }
}
