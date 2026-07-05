import { useChatStore } from '../stores/chatStore'

interface CharacterOption {
  id: string
  name: string
  description: string
}

const CHARACTERS: CharacterOption[] = [
  { id: 'rin', name: 'Rin', description: '知性优雅学姐' },
  { id: 'dorothy', name: 'Dorothy', description: '元气活力少女' },
]

export function CharacterSelector() {
  const characterId = useChatStore((s) => s.characterId)
  const setCharacterId = useChatStore((s) => s.setCharacterId)

  return (
    <div className="flex items-center gap-2">
      {CHARACTERS.map((char) => (
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
