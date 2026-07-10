import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

interface SwipeOptions {
  /** Target element ref. Falls back to document.body. */
  elementRef?: React.RefObject<HTMLElement | null>
  /** Route to navigate on right-swipe. Pass null to block right-swipe. */
  onRightSwipe?: (() => void) | null
  /** Minimum horizontal distance (px) to trigger. Default 60. */
  threshold?: number
  /** Maximum starting X (from left edge) for the swipe zone. Default 40. */
  edgeWidth?: number
  /** Disabled when true — hook still mounts, just no-ops. */
  disabled?: boolean
}

/**
 * Attaches a left-edge right-swipe listener to the given element (or document.body).
 * Does NOT block vertical scroll (touch-action: pan-y handles that natively).
 * Specifically handles:
 *   - Chat page: right-swipe → navigate('/home')
 *   - Home page: pass onRightSwipe={null} to block (prevents browser history.back)
 */
export function useSwipeNavigation({
  elementRef,
  onRightSwipe,
  threshold = 60,
  edgeWidth = 40,
  disabled = false,
}: SwipeOptions = {}) {
  const navigate = useNavigate()
  const startX = useRef(0)
  const startY = useRef(0)
  const locked = useRef<'none' | 'horizontal' | 'vertical'>('none')

  useEffect(() => {
    if (disabled) return

    const el = elementRef?.current ?? document.body

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length !== 1) return
      startX.current = e.touches[0].clientX
      startY.current = e.touches[0].clientY
      locked.current = 'none'
    }

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length !== 1) return
      const dx = e.touches[0].clientX - startX.current
      const dy = e.touches[0].clientY - startY.current
      if (locked.current === 'none') {
        // Determine axis after enough movement
        if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
          locked.current = Math.abs(dx) > Math.abs(dy) ? 'horizontal' : 'vertical'
        }
      }
      // If right-swipe is blocked (onRightSwipe === null) AND horizontal,
      // prevent default to stop browser back gesture
      if (locked.current === 'horizontal' && dx > 0 && onRightSwipe === null) {
        e.preventDefault()
      }
    }

    const onTouchEnd = (e: TouchEvent) => {
      if (locked.current !== 'horizontal') return
      const dx = e.changedTouches[0].clientX - startX.current
      const startedNearEdge = startX.current <= edgeWidth
      if (dx >= threshold && startedNearEdge) {
        if (onRightSwipe === null) return // blocked
        if (onRightSwipe) {
          onRightSwipe()
        } else {
          navigate(-1)
        }
      }
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    el.addEventListener('touchend', onTouchEnd, { passive: true })

    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
    }
  }, [disabled, elementRef, navigate, onRightSwipe, threshold, edgeWidth])
}
