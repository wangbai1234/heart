// A character id is a free-text key (UGC refactor C4). The set of *valid* ids is
// no longer a compile-time union — it comes from the server catalog at runtime
// (see stores/charactersStore). This alias stays for readability at call sites.
export type CharacterId = string

export interface CharacterProfile {
  id: CharacterId
  name: string
  shortName: string
  statusLabel: string
  moodLabel: string
  avatar: string
  tag: string
  tagColor: string
  tagBg: string
  summary: string
  homeIntro: string
}

export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  timestamp: number
  kind: 'text' | 'voice'
  duration?: string
  audioDuration?: number
}

export interface HomeAnnouncement {
  id: string
  title: string
  summary: string
  content?: string
  publishedAt: number
  tag: string
}

/**
 * User-facing feedback copy for failures that were previously swallowed
 * silently (SUG-1). Centralized here for consistency and future i18n.
 * Distinguish permanent failures (provider key invalid → suggest text) from
 * transient ones (network/timeout → retry).
 */
export const FEEDBACK_COPY = {
  /** Permanent: TTS provider unavailable (e.g. key expired / 401). */
  voiceUnavailable: '语音服务暂时不可用，先用文字陪你',
  /** Transient: audio failed to load; a retry may succeed. */
  voiceLoadFailed: '语音加载失败了，点一下再试试',
  /** Transient: playback failed to start. */
  voiceRetry: '语音没能播放，请稍后再试',
  /** Generic stream/turn error surfaced from the WebSocket layer. */
  streamError: 'yuoyuo 宇宙偷偷偏离了轨道，正在修复…',
} as const

export const HERO_BANNER = {
  light: '/assets/backgrounds/background_login_hero.webp',
  dark: '/assets/backgrounds/暗色风格background_login_hero.webp.png',
} as const

export const CHARACTER_BANNER = {
  light: '/assets/backgrounds/background_character_hero.webp',
  dark: '/assets/backgrounds/暗色风格background_login_hero.webp.png',
} as const

export const LOGIN_HERO = {
  light: '/assets/backgrounds/background_login_hero.webp',
  dark: '/assets/backgrounds/暗色风格background_login_hero.webp.png',
} as const

/**
 * Visual/asset registry keyed by character id. This is NOT the catalog — the
 * authoritative "which characters exist" list lives on the server
 * (GET /api/characters). This map only supplies frontend-only presentation
 * (avatar image, tag colors, mock preview) for the characters we ship assets
 * for. Unknown ids fall back to DEFAULT_CHARACTER_PROFILE via
 * resolveCharacterProfile.
 */
export const CHARACTER_PROFILES: Record<string, CharacterProfile> = {
  rin: {
    id: 'rin',
    name: '神无月凛',
    shortName: '凛',
    statusLabel: '温柔在线',
    moodLabel: '温柔',
    avatar: '/assets/characters/character_shenwuyue_avatar.png',
    tag: '御姐型',
    tagColor: '#8B5CF6',
    tagBg: 'rgba(200,182,255,0.3)',
    summary: '失去时代的雷神，带着完整的战功回到一个不需要她的世界。',
    homeIntro: '刚刚和你聊过 · 心情：温柔',
  },
  dorothy: {
    id: 'dorothy',
    name: '桃乐丝',
    shortName: '桃乐丝',
    statusLabel: '元气在线',
    moodLabel: '元气',
    avatar: '/assets/characters/character_taolesi_avatar.png',
    tag: '元气型',
    tagColor: '#3B82F6',
    tagBg: 'rgba(167,199,231,0.3)',
    summary: '来自虚构舞台的陪伴者，明亮、热情，也足够认真地记得每一次对话。',
    homeIntro: '刚刚和你聊过 · 心情：元气',
  },
}

/** Neutral profile used for characters we have no bundled assets for (e.g. a new
 * server-side / UGC character). Display name is overridden by the server. */
export const DEFAULT_CHARACTER_PROFILE: Omit<CharacterProfile, 'id' | 'name' | 'shortName'> = {
  statusLabel: '在线',
  moodLabel: '在线',
  avatar: '/assets/characters/character_shenwuyue_avatar.png',
  tag: '角色',
  tagColor: '#8B5CF6',
  tagBg: 'rgba(200,182,255,0.3)',
  summary: '',
  homeIntro: '',
}

/**
 * Resolve a full presentation profile for a character id, merging the
 * server-authoritative display name (when known) over the local visual assets,
 * and falling back to a neutral profile for ids we ship no assets for. Never
 * returns undefined — safe to index into for avatar / name / statusLabel.
 *
 * @param id          Character id
 * @param displayName Server-provided display name (optional)
 * @param avatarUrl   Server-provided avatar URL for UGC characters (optional).
 * @param opts.isOwner When true, renders the character as user-created (shows '自建' tag).
 */
export function resolveCharacterProfile(
  id: string,
  displayName?: string,
  avatarUrl?: string | null,
  opts?: { isOwner?: boolean },
): CharacterProfile {
  const base = CHARACTER_PROFILES[id]
  if (base) {
    return displayName ? { ...base, name: displayName } : base
  }
  const name = displayName || id
  const isOwner = opts?.isOwner ?? false
  return {
    ...DEFAULT_CHARACTER_PROFILE,
    id,
    name,
    shortName: name,
    avatar: avatarUrl || DEFAULT_CHARACTER_PROFILE.avatar,
    tag: isOwner ? '自建' : DEFAULT_CHARACTER_PROFILE.tag,
    tagColor: isOwner ? '#5A88F8' : DEFAULT_CHARACTER_PROFILE.tagColor,
    tagBg: isOwner ? 'rgba(120,150,255,0.24)' : DEFAULT_CHARACTER_PROFILE.tagBg,
  }
}

const now = Date.now()

export const HOME_ANNOUNCEMENTS: HomeAnnouncement[] = [
  {
    id: 'notice-0709',
    title: '自创角色功能上线，现在可以设计你的专属伴侣',
    summary: '在「设置 → 角色创作」或角色页点击「创建新角色」即可开始，填写名字、人设、性格即可生成。',
    content: '🎉 自创角色功能正式上线！\n\n你现在可以设计属于自己的专属 AI 伴侣了。\n\n**如何创建：**\n- 进入「角色」页面，点击底部「创建新角色」\n- 或者前往「设置 → 角色创作 → 创建新角色」\n\n**支持设置：**\n- 角色名字与头像（可上传图片，不上传则以名字最后一个字作为头像）\n- 角色人设描述（20–1500 字，越详细越有个性）\n- 相处风格（温柔 / 清冷 / 俏皮 / 内敛 / 浓烈）\n- 性格滑块（亲切度、话唠度、直率度等6个维度）\n\n**每位用户最多可创建 5 个自定义角色。**\n\n自创角色已完整支持记忆系统、主动消息和情绪变化，和内置角色体验一致。',
    publishedAt: now - 1 * 60 * 60 * 1000,
    tag: '最新',
  },
  {
    id: 'notice-0704',
    title: '角色后台已上线，语音开关支持按角色单独保存',
    summary: '现在可以在聊天页右上角进入角色后台，为不同角色分别设置语音回复偏好。',
    content: '角色后台功能现已上线。\n\n进入任意角色的聊天页，点击右上角头像或菜单按钮，即可进入「角色后台」。\n\n在后台你可以：\n- 单独为每个角色开启或关闭语音回复\n- 查看当前角色的设定摘要\n- 清空与该角色的聊天记录（不影响记忆系统）\n\n语音开关的设定会保存在云端，换设备也不会丢失。',
    publishedAt: now - 4 * 60 * 60 * 1000,
    tag: '更新',
  },
  {
    id: 'notice-0629',
    title: '私密对话能力优化，聊天记录展示更接近真实消息产品',
    summary: '聊天入口改为先查看会话列表，再进入对应角色的具体会话页面。',
    content: '本次优化调整了聊天入口的交互逻辑。\n\n**主要变化：**\n- 点击底部「消息」标签后，现在会先显示各角色的会话列表\n- 点击具体角色卡片后进入对应的聊天页面\n- 这样可以更方便地在多个角色之间切换，不容易误触\n\n同时对聊天气泡的显示做了细节优化，时间戳展示更清晰，阅读体验更接近主流消息产品。',
    publishedAt: now - 5 * 24 * 60 * 60 * 1000,
    tag: '公告',
  },
]

export function getHeroBanner(theme: 'light' | 'dark') {
  return HERO_BANNER[theme]
}

export function getCharacterBanner(theme: 'light' | 'dark') {
  return CHARACTER_BANNER[theme]
}

export function getLoginHero(theme: 'light' | 'dark') {
  return LOGIN_HERO[theme]
}

type PreviewMessage = Pick<ConversationMessage, 'content' | 'duration' | 'kind' | 'role' | 'audioDuration'>

function formatVoiceDuration(value?: string | number) {
  if (!value) return '0:00'
  if (typeof value === 'string') return value

  const totalSeconds = Math.max(1, Math.round(value / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function getMessagePreview(messages: PreviewMessage[]) {
  const last = messages[messages.length - 1]
  if (!last) return '开始新的对话'
  if (last.kind === 'voice') {
    return `语音消息 · ${formatVoiceDuration(last.duration ?? last.audioDuration)}`
  }
  return last.content || '新的消息'
}

export function getConversationPreview(messages: ConversationMessage[]) {
  return getMessagePreview(messages)
}

export function getUnreadMessageCount(messages: Array<Pick<PreviewMessage, 'role'>>) {
  let unreadCount = 0
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role !== 'assistant') break
    unreadCount += 1
  }
  return unreadCount
}

export function formatConversationTime(timestamp: number) {
  const date = new Date(timestamp)
  const nowDate = new Date()
  const sameDay =
    date.getFullYear() === nowDate.getFullYear() &&
    date.getMonth() === nowDate.getMonth() &&
    date.getDate() === nowDate.getDate()
  if (sameDay) {
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date)
  }

  const yesterday = new Date(nowDate)
  yesterday.setDate(nowDate.getDate() - 1)
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  if (isYesterday) return '昨天'

  return `${date.getMonth() + 1}/${date.getDate()}`
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

export function shouldShowTimestamp(current: { timestamp: number }, previous: { timestamp: number } | null): boolean {
  if (!previous) return true
  return current.timestamp - previous.timestamp > 5 * 60 * 1000
}

export function formatChatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()

  if (isSameDay(date, now)) {
    return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`
  }

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (isSameDay(date, yesterday)) {
    return `昨天 ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
  }

  return `${date.getMonth() + 1}/${date.getDate()} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function isCJK(char: string): boolean {
  const code = char.charCodeAt(0)
  return (
    (code >= 0x4e00 && code <= 0x9fff) ||
    (code >= 0x3400 && code <= 0x4dbf) ||
    (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0x3000 && code <= 0x303f) ||
    (code >= 0xff00 && code <= 0xffef)
  )
}

function displayWidth(char: string): number {
  return isCJK(char) ? 2 : 1
}

export function formatTextByDisplayWidth(text: string, maxWidth = 30): string {
  const lines: string[] = []
  let line = ''
  let width = 0

  for (const char of text) {
    if (char === '\n') {
      lines.push(line)
      line = ''
      width = 0
      continue
    }
    const w = displayWidth(char)
    if (width + w > maxWidth) {
      lines.push(line)
      line = ''
      width = 0
    }
    line += char
    width += w
  }
  lines.push(line)
  return lines.join('\n')
}
