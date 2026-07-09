import { useChatStore } from '../stores/chatStore'
import { useCharactersStore } from '../stores/charactersStore'
import { CHARACTER_PROFILES, resolveCharacterProfile } from '../data/uiContent'

interface CharacterOption {
  id: string
  name: string
  description: string
}

// Built-in fallback used before the server catalog loads (or if it fails).
const FALLBACK: CharacterOption[] = Object.values(CHARACTER_PROFILES).map((p) => ({
  id: p.id,
  name: p.shortName,
  description: p.tag,
}))

export function CharacterSelector() {
  const characterId = useChatStore((s) => s.characterId)
  const setCharacterId = useChatStore((s) => s.setCharacterId)
  const serverCharacters = useCharactersStore((s) => s.characters)

  const characters: CharacterOption[] =
    serverCharacters.length > 0
      ? serverCharacters.map((c) => {
          const profile = resolveCharacterProfile(c.id, c.display_name, c.avatar_url)
          return { id: c.id, name: c.display_name, description: profile.tag }
        })
      : FALLBACK

  return (
    <div className="flex items-center gap-2">
      {characters.map((char) => (
        <button
          key={char.id}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            characterId === char.id
              ? 'bg-[var(--color-accent)] text-white'
              : 'bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-border)]'
          }`}
          onClick={() => setCharacterId(char.id)}
          title={char.description}
        >
          {char.name}
        </button>
      ))}
    </div>
  )
}
