import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeStore } from '../stores/themeStore'
import { useAppStore } from '../stores/appStore'
import { useChatStore } from '../stores/chatStore'
import { Toast } from '../components/ui/Toast'
import { TabBar } from '../components/ui/TabBar'
import { BottomSheet } from '../components/ui/BottomSheet'
import { CHARACTER_PROFILES, resolveCharacterProfile, type CharacterProfile } from '../data/uiContent'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { stageLabel, stageWithIntimacy, isColdWar, intimacyPercent } from '../utils/relationship'
// DISABLED 2026-07-24: 角色↔剧情关联功能暂停，见下方渲染块注释
// import { StoryInviteCard } from '../components/StoryInviteCard'
import type { CompanionDTO } from '../services/api'

interface CompanionVM {
  companion: CompanionDTO
  profile: CharacterProfile
}

export function CharacterPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useThemeStore()
  const { setCharacter } = useAppStore()
  const setActiveCharacter = useChatStore((s) => s.setActiveCharacter)
  const serverCharacters = useCharactersStore((s) => s.characters)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)
  const [toast, setToast] = useState({ visible: false, message: '' })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    loadCompanions()
  }, [loadCompanions])

  // Bond-center list is already sorted by the backend (unread/proactive → recency → intimacy).
  const companionVMs: CompanionVM[] = companions.map((c) => ({
    companion: c,
    profile: resolveCharacterProfile(c.character_id, c.display_name, c.avatar_url, {
      isOwner: c.is_owner && !c.is_builtin,
    }),
  }))

  // Cold-start / offline fallback: fall back to the raw character catalog so the
  // page never renders empty before /api/companions resolves.
  const fallbackProfiles: CharacterProfile[] =
    serverCharacters.length > 0
      ? serverCharacters.map((c) =>
          resolveCharacterProfile(c.id, c.display_name, c.avatar_url, { isOwner: c.is_owner && !c.is_builtin }),
        )
      : Object.values(CHARACTER_PROFILES)

  const pageBg =
    resolvedTheme === 'dark'
      ? '/assets/backgrounds/暗色聊天背景图.png'
      : '/assets/backgrounds/聊天背景图.png'

  const handleSelectCharacter = (charId: string) => {
    setCharacter(charId)
    setActiveCharacter(charId)
    navigate(`/chat/${charId}`)
  }

  const handleOpenBackstage = (charId: string) => {
    setCharacter(charId)
    setActiveCharacter(charId)
    navigate('/character-backstage')
  }

  const hero = companionVMs[0]
  const gallery = companionVMs.slice(1)
  const expanded = companionVMs.find((vm) => vm.companion.character_id === expandedId)

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {/* Background */}
      <img src={pageBg} alt="" className="absolute inset-0 w-full h-full object-cover z-0" />

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Status bar */}
        <div style={{ height: 'var(--safe-top)' }} />

        {/* Navigation bar */}
        <div className="relative z-20 flex items-center justify-between px-5 h-[44px] shrink-0">
          <button onClick={() => navigate('/home')} className="w-[44px] h-[44px] flex items-center justify-center">
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="10,2 2,10 10,18" />
            </svg>
          </button>
          <span className="text-[17px] font-medium text-[var(--color-ink)]">羁绊</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/my-characters')}
              className="h-[34px] px-3 rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] text-[13px] text-[var(--color-primary)] font-medium active:scale-[0.96] transition-transform"
            >
              我的角色
            </button>
            <button
              onClick={() => navigate('/characters/new')}
              className="w-[34px] h-[34px] rounded-full bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] flex items-center justify-center text-[var(--color-primary)] active:scale-[0.96] transition-transform"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="7" y1="1" x2="7" y2="13" />
                <line x1="1" y1="7" x2="13" y2="7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Bond center content */}
        <div className="relative z-10 flex-1 overflow-y-auto px-4 pt-3 pb-[80px]">
          {companionVMs.length === 0 ? (
            // Fallback: plain character list, same shape as before, while /api/companions loads.
            <div className="flex flex-col gap-3">
              {fallbackProfiles.map((char) => (
                <button
                  key={char.id}
                  onClick={() => handleSelectCharacter(char.id)}
                  className="relative w-full rounded-[24px] p-5 text-left active:scale-[0.98] transition-all duration-200 border bg-[var(--color-glass-55)] backdrop-blur-[16px] border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]"
                >
                  <div className="flex gap-4">
                    <div className="relative shrink-0">
                      <div
                        className="w-[80px] h-[80px] rounded-full p-[3px]"
                        style={{ background: `linear-gradient(135deg, ${char.tagBg}, transparent)` }}
                      >
                        <img src={char.avatar} alt={char.name} className="w-full h-full rounded-full object-cover" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[20px] font-bold text-[var(--color-ink)]">{char.name}</span>
                        <span
                          className="text-[12px] font-medium px-2 py-[3px] rounded-[12px]"
                          style={{ color: char.tagColor, backgroundColor: char.tagBg }}
                        >
                          {char.tag}
                        </span>
                      </div>
                      <p className="text-[13px] text-[var(--color-text-secondary)]">{char.summary}</p>
                    </div>
                    <div className="flex items-center shrink-0 pl-2">
                      <svg width="8" height="14" viewBox="0 0 8 14" fill="none" stroke="var(--color-chevron)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="1,1 7,7 1,13" />
                      </svg>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              {/* 今日陪伴大卡 */}
              {hero && (
                <HeroCard
                  vm={hero}
                  onChat={() => handleSelectCharacter(hero.companion.character_id)}
                  onOpenArchive={() => setExpandedId(hero.companion.character_id)}
                />
              )}

              {/* 陪伴长廊 */}
              {gallery.length > 0 && (
                <div>
                  <h3 className="text-[14px] font-medium text-[var(--color-text-secondary)] mb-2 px-1">陪伴长廊</h3>
                  <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1">
                    {gallery.map((vm) => (
                      <button
                        key={vm.companion.character_id}
                        onClick={() => handleSelectCharacter(vm.companion.character_id)}
                        className="relative shrink-0 w-[92px] flex flex-col items-center gap-1.5 rounded-[20px] p-3 bg-[var(--color-glass-55)] backdrop-blur-[12px] border border-[var(--color-border-glass)] active:scale-[0.96] transition-transform"
                      >
                        <div className="relative">
                          <div
                            className="w-[56px] h-[56px] rounded-full p-[2px]"
                            style={{ background: `linear-gradient(135deg, ${vm.profile.tagBg}, transparent)` }}
                          >
                            <img src={vm.profile.avatar} alt={vm.profile.name} className="w-full h-full rounded-full object-cover" />
                          </div>
                          {vm.companion.unread_count > 0 && (
                            <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-[16px] px-1 rounded-full bg-[var(--color-danger,#FF4D6D)] text-white text-[10px] font-medium flex items-center justify-center">
                              {vm.companion.unread_count > 9 ? '9+' : vm.companion.unread_count}
                            </span>
                          )}
                        </div>
                        <span className="text-[12px] font-medium text-[var(--color-ink)] truncate max-w-full">{vm.profile.name}</span>
                        <span className="text-[10px] text-[var(--color-text-secondary)]">{stageLabel(vm.companion.relationship_stage)}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* TabBar */}
        <TabBar />
      </div>

      <Toast visible={toast.visible} message={toast.message} onDismiss={() => setToast({ visible: false, message: '' })} />

      {/* 羁绊档案 页内展开 */}
      <BottomSheet open={!!expanded} onClose={() => setExpandedId(null)}>
        {expanded && (
          <ArchivePanel vm={expanded} onOpenBackstage={() => handleOpenBackstage(expanded.companion.character_id)} />
        )}
      </BottomSheet>
    </div>
  )
}

function HeroCard({
  vm,
  onChat,
  onOpenArchive,
}: {
  vm: CompanionVM
  onChat: () => void
  onOpenArchive: () => void
}) {
  const { companion, profile } = vm
  const coldWar = isColdWar(companion.relationship_stage)

  return (
    <div className="relative w-full rounded-[28px] p-5 bg-[var(--color-glass-55)] backdrop-blur-[16px] border border-[var(--color-border-glass)] shadow-[var(--shadow-soft)]">
      <div className="flex items-start gap-4">
        <div className="relative shrink-0">
          <div
            className="w-[96px] h-[96px] rounded-full p-[3px]"
            style={{ background: `linear-gradient(135deg, ${profile.tagBg}, transparent)` }}
          >
            <img src={profile.avatar} alt={profile.name} className="w-full h-full rounded-full object-cover" />
          </div>
          {companion.unread_count > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[22px] h-[22px] px-1.5 rounded-full bg-[var(--color-danger,#FF4D6D)] text-white text-[12px] font-medium flex items-center justify-center">
              {companion.unread_count > 9 ? '9+' : companion.unread_count}
            </span>
          )}
        </div>
        <div className="flex-1 min-w-0 pt-1">
          <div className="text-[12px] text-[var(--color-text-secondary)] mb-0.5">今日陪伴</div>
          <div className="text-[22px] font-bold text-[var(--color-ink)] mb-1">{profile.name}</div>
          <div className="text-[13px] font-medium text-[var(--color-primary)] mb-2">
            {stageWithIntimacy(companion.relationship_stage, companion.intimacy)}
          </div>

          {coldWar ? (
            <span className="inline-block text-[11px] font-medium px-2.5 py-1 rounded-full bg-[rgba(140,150,170,0.18)] text-[var(--color-text-secondary)]">
              闹别扭
            </span>
          ) : (
            <div className="w-full h-[6px] rounded-full bg-[var(--color-divider)] overflow-hidden">
              <div
                className="h-full rounded-full bg-[var(--color-primary)] transition-all"
                style={{ width: `${intimacyPercent(companion.intimacy)}%` }}
              />
            </div>
          )}
        </div>
      </div>

      {companion.last_message_text && (
        <p className="mt-3 text-[13px] text-[var(--color-text-secondary)] truncate">
          {companion.last_message_modality === 'voice' && '🎙 '}
          {companion.last_message_text}
        </p>
      )}

      {companion.has_proactive && (
        <p className="mt-1 text-[12px] text-[var(--color-primary)]">最近：主动来找过你</p>
      )}

      <div className="flex gap-2 mt-4">
        <button
          onClick={onChat}
          className="flex-1 h-[40px] rounded-full bg-[var(--color-primary)] text-white text-[14px] font-medium active:scale-[0.97] transition-transform"
        >
          继续聊天
        </button>
        <button
          onClick={onOpenArchive}
          className="flex-1 h-[40px] rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)] text-[14px] font-medium active:scale-[0.97] transition-transform"
        >
          羁绊档案
        </button>
        {/* 剧情邀约: Wave 3 占位，本轮不接后端 */}
      </div>
    </div>
  )
}

function ArchivePanel({ vm, onOpenBackstage }: { vm: CompanionVM; onOpenBackstage: () => void }) {
  const { companion, profile } = vm
  const sourceLabel = companion.source === 'built_in' ? '入驻角色' : '原创'

  return (
    <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto">
      <div className="flex items-center gap-3">
        <img src={profile.avatar} alt={profile.name} className="w-[64px] h-[64px] rounded-full object-cover" />
        <div>
          <div className="text-[18px] font-bold text-[var(--color-ink)]">{profile.name}</div>
          <div className="text-[13px] font-medium text-[var(--color-primary)]">
            {stageWithIntimacy(companion.relationship_stage, companion.intimacy)}
          </div>
        </div>
      </div>

      <div className="rounded-[16px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] p-4">
        <h4 className="text-[13px] font-medium text-[var(--color-text-secondary)] mb-2">最近陪伴</h4>
        <p className="text-[14px] text-[var(--color-ink)]">
          {companion.last_message_text || '还没有聊过天'}
        </p>
        <div className="flex gap-3 mt-2 text-[12px] text-[var(--color-text-secondary)]">
          {companion.unread_count > 0 && <span>{companion.unread_count} 条未读</span>}
          {companion.has_proactive && <span className="text-[var(--color-primary)]">主动来找过你</span>}
          <span>来源：{sourceLabel}</span>
        </div>
      </div>

      {/* 剧情邀约（Wave 3）— DISABLED 2026-07-24：角色↔剧情关联功能已暂停。
          恢复：取消 import 与下方注释即可。
      {companion.available_story_hook && (
        <StoryInviteCard characterId={companion.character_id} hook={companion.available_story_hook} />
      )} */}

      <div className="rounded-[16px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] p-4">
        <h4 className="text-[13px] font-medium text-[var(--color-text-secondary)] mb-2">共同回忆</h4>
        {/* TODO(Wave 4): 接相遇摘要（story-encounter → L3/L4 记忆），本轮无数据源 */}
        <p className="text-[13px] text-[var(--color-text-secondary)]">还没有共同经历的剧情，敬请期待。</p>
      </div>

      <button
        onClick={onOpenBackstage}
        className="w-full h-[44px] rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[var(--color-ink)] text-[14px] font-medium active:scale-[0.97] transition-transform"
      >
        声音与陪伴设置
      </button>
    </div>
  )
}
