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
      role: 'assistant',
      content: 'AI 朗读 · 可点击播放',
      timestamp: minutes(122),
      kind: 'voice',
      duration: '0:18',
    },
    {
      id: 'rin-5',
      role: 'user',
      content: '好。',
      timestamp: minutes(120),
      kind: 'text',
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
      role: 'user',
      content: '我会在这里等你哦。',
      timestamp: minutes(75),
      kind: 'text',
    },
  ],
}

export function getHeroBanner(theme: 'light' | 'dark') {
  return HERO_BANNER[theme]
}

export function getCharacterBanner(theme: 'light' | 'dark') {
  return CHARACTER_BANNER[theme]
}

export function getLoginHero(theme: 'light' | 'dark') {
  return LOGIN_HERO[theme]
}

export function getConversationPreview(messages: ConversationMessage[]) {
  const last = messages[messages.length - 1]
  if (!last) return '开始新的对话'
  if (last.kind === 'voice') {
    return `语音消息 · ${last.duration ?? '0:00'}`
  }
  return last.content || '新的消息'
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
