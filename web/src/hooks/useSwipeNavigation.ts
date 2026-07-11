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
  /**
   * Priority level for this listener.  Higher number = wins over lower.
   * Global default in App.tsx uses priority=0; per-page hooks use priority=1.
   * When a priority-1 listener is mounted, priority-0 listeners are silenced.
   */
  priority?: number
}

// Module-level counter: tracks the highest-priority listener currently mounted.
// Priority-0 (global) silences itself when any priority-1 listener is active.
let _maxPriority = 0
let _listenerCount = 0 // per-priority-1 refcount

/**
 * Attaches a left-edge right-swipe listener to the given element (or document.body).
 * Does NOT block vertical scroll (touch-action: pan-y handles that natively).
 *
 * Priority model:
 *   - App.tsx mounts with priority=0 as a global default.
 *   - Per-page calls mount with priority=1 and override the global.
 *   - Only one handler fires per swipe.
 */
export function useSwipeNavigation({
  elementRef,
  onRightSwipe,
  threshold = 60,
  edgeWidth = 40,
  disabled = false,
  priority = 1,
}: SwipeOptions = {}) {
  const navigate = useNavigate()
  const startX = useRef(0)
  const startY = useRef(0)
  const locked = useRef<'none' | 'horizontal' | 'vertical'>('none')

  useEffect(() => {
    if (priority === 1) {
      _listenerCount++
      _maxPriority = 1
    }
    return () => {
      if (priority === 1) {
        _listenerCount = Math.max(0, _listenerCount - 1)
        if (_listenerCount === 0) _maxPriority = 0
      }
    }
  }, [priority])

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
        if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
          locked.current = Math.abs(dx) > Math.abs(dy) ? 'horizontal' : 'vertical'
        }
      }
      if (locked.current === 'horizontal' && dx > 0 && onRightSwipe === null) {
        e.preventDefault()
      }
    }

    const onTouchEnd = (e: TouchEvent) => {
      // Lower-priority global listener yields when a page-level listener is mounted
      if (priority < _maxPriority) return
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
  }, [disabled, elementRef, navigate, onRightSwipe, threshold, edgeWidth, priority])
}
