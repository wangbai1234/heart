import type { ScenarioCardDTO } from '../../services/api'

/**
 * A single scenario tile for the Explore grid (SS09 PR2).
 *
 * Cover falls back to a genre-tinted gradient when `cover_url` is null (the
 * bulk importer leaves covers empty initially). Adult scenarios show a 🔞 label
 * (display only — scenarios are not age-gated).
 */

// Stable per-genre gradient so cover-less cards are still visually distinct.
const GENRE_GRADIENT: Record<string, string> = {
  校园恋爱: 'linear-gradient(135deg, #FFD6E0 0%, #FFB7C5 100%)',
  悬疑: 'linear-gradient(135deg, #A7B0C7 0%, #6B7392 100%)',
  末日无限流: 'linear-gradient(135deg, #C7A7A7 0%, #8E6B6B 100%)',
  修仙: 'linear-gradient(135deg, #BEE3D4 0%, #7ECBA5 100%)',
  古风宫斗: 'linear-gradient(135deg, #E7C7A7 0%, #C79A6B 100%)',
  现代豪门: 'linear-gradient(135deg, #C8B6FF 0%, #A78BFA 100%)',
  西幻: 'linear-gradient(135deg, #A7C7E7 0%, #6B9BD1 100%)',
  其他: 'linear-gradient(135deg, #E0D6F0 0%, #C8B6FF 100%)',
}

function genreGradient(genre: string): string {
  return GENRE_GRADIENT[genre] ?? GENRE_GRADIENT['其他']
}

interface ScenarioCardProps {
  scenario: ScenarioCardDTO
  onOpen: (id: string) => void
}

export function ScenarioCard({ scenario, onOpen }: ScenarioCardProps) {
  const { id, title, genre, cover_url, play_count, maturity } = scenario

  return (
    <button
      onClick={() => onOpen(id)}
      className="group relative flex flex-col text-left w-full rounded-[20px] overflow-hidden bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)] active:scale-[0.97] transition-transform"
    >
      {/* Cover */}
      <div
        className="relative w-full aspect-[3/4]"
        style={cover_url ? undefined : { background: genreGradient(genre) }}
      >
        {cover_url && (
          <img src={cover_url} alt="" className="absolute inset-0 w-full h-full object-cover" />
        )}
        {/* Genre chip */}
        <span className="absolute top-2 left-2 inline-flex h-[22px] items-center rounded-full bg-black/25 px-2 text-[11px] font-medium text-white backdrop-blur-[4px]">
          {genre}
        </span>
        {/* Adult label (display only) */}
        {maturity === 'adult' && (
          <span className="absolute top-2 right-2 inline-flex h-[22px] items-center rounded-full bg-black/35 px-1.5 text-[12px] backdrop-blur-[4px]">
            🔞
          </span>
        )}
      </div>

      {/* Meta */}
      <div className="px-2.5 pt-2 pb-2.5">
        <p className="text-[14px] font-semibold leading-[1.35] text-[var(--color-ink)] line-clamp-1">
          {title}
        </p>
        <div className="mt-1 flex items-center gap-1 text-[12px] text-[var(--color-text-muted)]">
          <span>🔥</span>
          <span>{formatPlays(play_count)}</span>
        </div>
      </div>
    </button>
  )
}

function formatPlays(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w 人玩过`
  return `${n} 人玩过`
}
