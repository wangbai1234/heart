import { useEffect, useRef, useState } from 'react'

interface ImmersiveProfileFrameProps {
  title: string
  html: string
  fallbackHeight?: number
}

/** Keeps bespoke profile documents isolated while matching their content height. */
export function ImmersiveProfileFrame({
  title,
  html,
  fallbackHeight = 1400,
}: ImmersiveProfileFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(fallbackHeight)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    let observer: ResizeObserver | null = null
    const measure = () => {
      try {
        const body = iframe.contentDocument?.body
        if (body) setHeight(body.scrollHeight + 8)
      } catch {
        setHeight(fallbackHeight)
      }
    }
    const observeBody = () => {
      measure()
      const body = iframe.contentDocument?.body
      if (!body) return
      observer?.disconnect()
      observer = new ResizeObserver(measure)
      observer.observe(body)
    }

    iframe.addEventListener('load', observeBody)
    if (iframe.contentDocument?.readyState === 'complete') observeBody()
    return () => {
      iframe.removeEventListener('load', observeBody)
      observer?.disconnect()
    }
  }, [fallbackHeight, html])

  return (
    <iframe
      ref={iframeRef}
      title={title}
      srcDoc={html}
      style={{
        width: '100%',
        height: `${height}px`,
        border: 'none',
        display: 'block',
        background: 'transparent',
      }}
      sandbox="allow-same-origin"
    />
  )
}
