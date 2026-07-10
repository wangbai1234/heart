import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
}

function getTimeBasedTheme(): 'light' | 'dark' {
  const h = new Date().getHours()
  return h >= 8 && h < 20 ? 'light' : 'dark'
}

function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'light') return 'light'
  if (theme === 'dark') return 'dark'
  return getTimeBasedTheme()
}

function applyTheme(resolved: 'light' | 'dark') {
  document.documentElement.setAttribute('data-theme', resolved)
}

let autoThemeInterval: ReturnType<typeof setInterval> | null = null

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      resolvedTheme: 'light',
      setTheme: (theme) => {
        const resolved = resolveTheme(theme)
        applyTheme(resolved)
        set({ theme, resolvedTheme: resolved })

        if (autoThemeInterval) {
          clearInterval(autoThemeInterval)
          autoThemeInterval = null
        }
        if (theme === 'system') {
          autoThemeInterval = setInterval(() => {
            const current = get()
            if (current.theme !== 'system') return
            const next = getTimeBasedTheme()
            if (next !== current.resolvedTheme) {
              applyTheme(next)
              set({ resolvedTheme: next })
            }
          }, 60_000)
        }
      },
    }),
    {
      name: 'yuoyuo-theme',
      onRehydrateStorage: () => {
        return (state) => {
          if (state) {
            const resolved = resolveTheme(state.theme)
            applyTheme(resolved)
            useThemeStore.setState({ resolvedTheme: resolved })
            if (state.theme === 'system') {
              autoThemeInterval = setInterval(() => {
                const current = useThemeStore.getState()
                if (current.theme !== 'system') return
                const next = getTimeBasedTheme()
                if (next !== current.resolvedTheme) {
                  applyTheme(next)
                  useThemeStore.setState({ resolvedTheme: next })
                }
              }, 60_000)
            }
          }
        }
      },
    },
  ),
)
