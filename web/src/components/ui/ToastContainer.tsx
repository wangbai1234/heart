import { useToastStore } from '../../stores/toastStore'
import { Toast } from './Toast'

/**
 * Renders the global toast queue. Mounted once at the app root so any layer
 * (pages, hooks, the WebSocket/API layer) can surface a message via
 * `useToastStore.getState().show(...)`.
 */
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)

  return (
    <>
      {toasts.map((t, i) => (
        <Toast
          key={t.id}
          message={t.message}
          variant={t.variant}
          offsetIndex={i}
          visible
          onDismiss={() => dismiss(t.id)}
        />
      ))}
    </>
  )
}
