export type CharacterId = 'rin' | 'dorothy'

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
  publishedAt: number
  tag: string
}

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

export const CHARACTER_PROFILES: Record<CharacterId, CharacterProfile> = {
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

const now = Date.now()
const minutes = (value: number) => now - value * 60 * 1000

export const CONVERSATION_THREADS: Record<CharacterId, ConversationMessage[]> = {
  rin: [
    {
      id: 'rin-1',
      role: 'assistant',
      content: '早上好，昨晚睡得怎么样？',
      timestamp: minutes(128),
      kind: 'text',
    },
    {
      id: 'rin-2',
      role: 'user',
      content: '做了个奇怪的梦。',
      timestamp: minutes(126),
      kind: 'text',
    },
    {
      id: 'rin-3',
      role: 'assistant',
      content: '讲给我听呀～我陪着你。',
      timestamp: minutes(124),
      kind: 'text',
    },
    {
      id: 'rin-4',
      role: 'user',
      content: '今天有点想和你多聊一会儿。',
      timestamp: minutes(122),
      kind: 'text',
    },
    {
      id: 'rin-5',
      role: 'assistant',
      content: 'AI 朗读 · 可点击播放',
      timestamp: minutes(120),
      kind: 'voice',
      duration: '0:18',
    },
  ],
  dorothy: [
    {
      id: 'dorothy-1',
      role: 'assistant',
      content: '晚安呀，记得多喝水，明天见~',
      timestamp: minutes(78),
      kind: 'text',
    },
    {
      id: 'dorothy-2',
      role: 'assistant',
      content: '我给你留了一条新的晚安消息，记得点开听听呀。',
      timestamp: minutes(75),
      kind: 'text',
    },
  ],
}

export const HOME_ANNOUNCEMENTS: HomeAnnouncement[] = [
  {
    id: 'notice-0704',
    title: '角色后台已上线，语音开关支持按角色单独保存',
    summary: '现在可以在聊天页右上角进入角色后台，为不同角色分别设置语音回复偏好。',
    publishedAt: now - 4 * 60 * 60 * 1000,
    tag: '最新',
  },
  {
    id: 'notice-0702',
    title: '会员兑换页已升级，激活码输入与引导流程更顺滑',
    summary: '兑换码支持直接粘贴与自动分组填写，首次引导也同步更新为三屏新版说明。',
    publishedAt: now - 28 * 60 * 60 * 1000,
    tag: '更新',
  },
  {
    id: 'notice-0629',
    title: '私密对话能力优化，聊天记录展示更接近真实消息产品',
    summary: '聊天入口改为先查看会话列表，再进入对应角色的具体会话页面。',
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
