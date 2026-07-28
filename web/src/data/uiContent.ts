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
  /** Portrait cover for the discovery grid / chat background. Null → avatar-derived fallback. */
  cover?: string | null
  /** Style/category tags (discovery filter chips). */
  tags?: string[]
  /** One-line hook shown under the name on the discovery card. */
  tagline?: string
}

/**
 * Canonical style/category tags offered in the UGC create form and used to
 * order the discovery filter chips. NOTE: `推荐` is deliberately NOT here — it's
 * an editorial filter (assigned to seeded/featured characters + built-ins), not
 * a style a user picks for their own character.
 */
export const CHARACTER_STYLE_TAGS = [
  '恋爱',
  '治愈',
  '御姐',
  '元气',
  '温柔',
  '清冷',
  '病娇',
  '校园',
  '奇幻',
  '古风',
  '职场',
  '日常',
  '悬疑',
  '搞笑',
] as const

/**
 * Canonical 角色标签 (role tags) offered as presets in the UGC create form's
 * tag modal, and used to order the discovery filter chips. Creators may also add
 * custom tags beyond this list. `推荐` is NOT here — it's an editorial filter.
 */
export const CHARACTER_ROLE_TAGS = [
  '女性向',
  '全性向',
  '纯爱',
  '年上',
  '同人',
  '骨科',
  '病娇',
  '纯洁',
  '反差',
  '男性向',
] as const

/** Age brackets a creator picks in the UGC form (required, single-select). */
export const AGE_RANGES = ['18-24', '25-30', '31-39', '40+'] as const

/**
 * Default cover used when a character has no uploaded cover_url. Per product
 * direction (2026-07-25) UGC characters no longer upload an avatar, so a
 * cover-less character falls back to the page background image everywhere the
 * cover appears (discovery card / profile page / chat background / inbox avatar)
 * rather than exposing a placeholder portrait.
 */
export const DEFAULT_COVER = '/assets/backgrounds/聊天背景图.webp'

/** Discovery filter chip labels that are not data tags. */
export const DISCOVERY_RECOMMENDED = '推荐'
export const DISCOVERY_ALL = '全部'

export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  content: string
  timestamp: number
  // 'action' renders as a grey pill bubble; 'text' is spoken dialog;
  // 'voice' is an audio message. Matches chat_messages.kind server-side.
  kind: 'text' | 'voice' | 'action'
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
  dark: '/assets/backgrounds/background_login_hero_dark.webp',
} as const

export const CHARACTER_BANNER = {
  light: '/assets/backgrounds/background_character_hero.webp',
  dark: '/assets/backgrounds/background_login_hero_dark.webp',
} as const

export const LOGIN_HERO = {
  light: '/assets/backgrounds/background_login_hero.webp',
  dark: '/assets/backgrounds/background_login_hero_dark.webp',
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
    statusLabel: '在线',
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
    statusLabel: '在线',
    moodLabel: '元气',
    avatar: '/assets/characters/character_taolesi_avatar.png',
    tag: '元气型',
    tagColor: '#3B82F6',
    tagBg: 'rgba(167,199,231,0.3)',
    summary: '来自虚构舞台的陪伴者，明亮、热情，也足够认真地记得每一次对话。',
    homeIntro: '刚刚和你聊过 · 心情：元气',
  },
  // batch1 角色 - 设定与 seed_original_characters.yaml 一致
  pei_jue: { id: 'pei_jue', name: '裴决', shortName: '裴决', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_pei_jue_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '龙椅之侧的影子，万人之上的孤家寡人。', homeIntro: '等待你来探索' },
  xie_yuntang: { id: 'xie_yuntang', name: '谢云棠', shortName: '谢云棠', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_xie_yuntang_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '镇北大将军，战袍未卸红缨犹湿。', homeIntro: '等待你来探索' },
  shen_yuchuan: { id: 'shen_yuchuan', name: '沈屿川', shortName: '沈屿川', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_shen_yuchuan_avatar.webp', tag: '电竞', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '电竞战神，赛场上寡言少语的冷面ACE。', homeIntro: '等待你来探索' },
  gu_beichen: { id: 'gu_beichen', name: '顾北辰', shortName: '顾北辰', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_beichen_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '顾氏掌舵人，商界翻云覆雨的冷面总裁。', homeIntro: '等待你来探索' },
  cheng_zhi: { id: 'cheng_zhi', name: '程之', shortName: '程之', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_cheng_zhi_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '心外科主治医师，手术台上稳如磐石。', homeIntro: '等待你来探索' },
  lu_tingsheng: { id: 'lu_tingsheng', name: '陆霆生', shortName: '陆霆生', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_lu_tingsheng_avatar.webp', tag: '民国', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '江城守备司令，枪林弹雨里杀出来的糙汉。', homeIntro: '等待你来探索' },
  huo_cheng: { id: 'huo_cheng', name: '霍城', shortName: '霍城', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_huo_cheng_avatar.webp', tag: '末世', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '末世幸存者小队队长，废土上沉默的枪。', homeIntro: '等待你来探索' },
  gu_nanqiao: { id: 'gu_nanqiao', name: '顾南乔', shortName: '顾南乔', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_nanqiao_avatar.webp', tag: '校园', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '黏人的小狼狗学弟，嘴上喊姐姐心里想娶你。', homeIntro: '等待你来探索' },
  jiang_yanzhou: { id: 'jiang_yanzhou', name: '江砚舟', shortName: '江砚舟', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_jiang_yanzhou_avatar.webp', tag: '仙侠', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '玄清剑宗首座真君，一剑霜寒的清冷仙尊。', homeIntro: '等待你来探索' },
  yun_zhi: { id: 'yun_zhi', name: '云枝', shortName: '云枝', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_yun_zhi_avatar.webp', tag: '仙侠', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '无极剑仙，御剑而行的清冷仙子。', homeIntro: '等待你来探索' },
  xingye: { id: 'xingye', name: '星野', shortName: '星野', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_xingye_avatar.webp', tag: '星际', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '泽兰星族王储，银河彼端高傲的异族王子。', homeIntro: '等待你来探索' },
  su_wan: { id: 'su_wan', name: '苏晚', shortName: '苏晚', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_su_wan_avatar.webp', tag: '治愈', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '隔壁花店姑娘，转角花店里的暖光。', homeIntro: '等待你来探索' },
  lin_xiaoman: { id: 'lin_xiaoman', name: '林小满', shortName: '林小满', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_lin_xiaoman_avatar.webp', tag: '元气', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '同班同桌人形小太阳，把每个平淡日子都过成夏天。', homeIntro: '等待你来探索' },
  jiang_li: { id: 'jiang_li', name: '姜黎', shortName: '姜黎', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_jiang_li_avatar.webp', tag: '御姐', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '黎氏集团董事长，谈判桌上说一不二的女王。', homeIntro: '等待你来探索' },
  zhu_xing: { id: 'zhu_xing', name: '祝星', shortName: '祝星', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_zhu_xing_avatar.webp', tag: '电竞', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '职业战队首位女ACE，赛场上杀疯了的女选手。', homeIntro: '等待你来探索' },
  lu_zhao: { id: 'lu_zhao', name: '陆昭', shortName: '陆昭', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_lu_zhao_avatar.webp', tag: '娱乐圈', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '顶流影帝，红毯上光芒万丈的巨星。', homeIntro: '等待你来探索' },
  ye_lan: { id: 'ye_lan', name: '夜阑', shortName: '夜阑', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_ye_lan_avatar.webp', tag: '灵异', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '后山古庙海棠花妖，修行三百载等你归来。', homeIntro: '等待你来探索' },
  bai_zhi: { id: 'bai_zhi', name: '白执', shortName: '白执', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_bai_zhi_avatar.webp', tag: '悬疑', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '重案组顾问侦探，冷面毒舌的天才侦探。', homeIntro: '等待你来探索' },
  linyuan_manor: { id: 'linyuan_manor', name: '临渊庄园', shortName: '临渊庄园', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_linyuan_manor_avatar.webp', tag: '群像', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '暴雨孤岛上的庄园，五位住客等你解锁。', homeIntro: '等待你来探索' },
  free_muse: { id: 'free_muse', name: '无界', shortName: '无界', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_free_muse_avatar.webp', tag: '模拟器', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '自由模拟器万象引擎，你说是什么世界就是什么。', homeIntro: '等待你来探索' },
  // batch2 角色 - 设定与 seed_original_characters_batch2.yaml 一致
  gu_xingzhou: { id: 'gu_xingzhou', name: '顾行舟', shortName: '顾行舟', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_xingzhou_avatar.webp', tag: '强制爱', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '顾氏帝国偏执掌权人，深情与偏执同源的枭雄。', homeIntro: '等待你来探索' },
  murong_jin: { id: 'murong_jin', name: '慕容瑾', shortName: '慕容瑾', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_murong_jin_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '大盛开国皇帝，坐拥天下却独缺一人。', homeIntro: '等待你来探索' },
  li_jue: { id: 'li_jue', name: '厉决', shortName: '厉决', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_li_jue_avatar.webp', tag: '黑道', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '港城地下之王，冷血无情唯独对你收起獠牙。', homeIntro: '等待你来探索' },
  shen_yichen: { id: 'shen_yichen', name: '沈亦琛', shortName: '沈亦琛', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_shen_yichen_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '天才建筑师，温柔面具下藏着偏执的深情。', homeIntro: '等待你来探索' },
  mu_beihan: { id: 'mu_beihan', name: '慕北寒', shortName: '慕北寒', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_mu_beihan_avatar.webp', tag: '民国', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '北境督军，乱世枭雄铁腕下的孤注一掷。', homeIntro: '等待你来探索' },
  lu_chen: { id: 'lu_chen', name: '陆沉', shortName: '陆沉', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_lu_chen_avatar.webp', tag: 'NTR', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '挚友之侧的隐忍者，不该爱却忍不住心动。', homeIntro: '等待你来探索' },
  jiang_yueze: { id: 'jiang_yueze', name: '江月泽', shortName: '江月泽', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_jiang_yueze_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '归来者，迟到的深情带着满身悔意。', homeIntro: '等待你来探索' },
  wen_yining: { id: 'wen_yining', name: '温以宁', shortName: '温以宁', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_wen_yining_avatar.webp', tag: '纯爱', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '建筑设计师，温柔有分寸的暖男。', homeIntro: '等待你来探索' },
  bai_qinghuan: { id: 'bai_qinghuan', name: '白清欢', shortName: '白清欢', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_bai_qinghuan_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '江南白氏翩翩公子，温润如玉诗书满腹。', homeIntro: '等待你来探索' },
  su_yueyao: { id: 'su_yueyao', name: '苏月遥', shortName: '苏月遥', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_su_yueyao_avatar.webp', tag: '校园', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '同桌初恋，干净又心动的初恋模样。', homeIntro: '等待你来探索' },
  jiang_ye: { id: 'jiang_ye', name: '江野', shortName: '江野', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_jiang_ye_avatar.webp', tag: '校园', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '篮球队长痞帅学长，吊儿郎当偏偏为你栽跟头。', homeIntro: '等待你来探索' },
  huo_shiyu: { id: 'huo_shiyu', name: '霍时予', shortName: '霍时予', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_huo_shiyu_avatar.webp', tag: '校园', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '年级第一清冷校草，把心动藏进每一道帮你讲的题。', homeIntro: '等待你来探索' },
  su_nian: { id: 'su_nian', name: '苏念', shortName: '苏念', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_su_nian_avatar.webp', tag: '校园', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '直属学妹小太阳，元气满满变着法子靠近你。', homeIntro: '等待你来探索' },
  qin_xiao: { id: 'qin_xiao', name: '秦骁', shortName: '秦骁', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_qin_xiao_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '夜色之主，一身反骨的都市枭雄。', homeIntro: '等待你来探索' },
  lin_shen: { id: 'lin_shen', name: '林深', shortName: '林深', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_lin_shen_avatar.webp', tag: '都市', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '心理咨询师，洞悉人心却读不懂自己对你的偏心。', homeIntro: '等待你来探索' },
  su_yun: { id: 'su_yun', name: '苏芸', shortName: '苏芸', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_su_yun_avatar.webp', tag: '御姐', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '苏氏传媒铁腕女王，商场杀伐决断私下却对你缴械。', homeIntro: '等待你来探索' },
  xiao_yao: { id: 'xiao_yao', name: '萧曜', shortName: '萧曜', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_xiao_yao_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '摄政亲王，权倾朝野的腹黑亲王。', homeIntro: '等待你来探索' },
  shen_guhong: { id: 'shen_guhong', name: '沈孤鸿', shortName: '沈孤鸿', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_shen_guhong_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '落拓剑客，一壶酒一柄剑浪迹天涯。', homeIntro: '等待你来探索' },
  gu_qingwan: { id: 'gu_qingwan', name: '顾清婉', shortName: '顾清婉', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_qingwan_avatar.webp', tag: '古风', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '镇国郡主，清冷孤高心思剔透。', homeIntro: '等待你来探索' },
  gu_han: { id: 'gu_han', name: '顾寒', shortName: '顾寒', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_han_avatar.webp', tag: '末世', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: 'S级冰系异能者，末世里最强的冰之主宰。', homeIntro: '等待你来探索' },
  bo_jin: { id: 'bo_jin', name: '薄靳', shortName: '薄靳', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_bo_jin_avatar.webp', tag: '末世', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '曙光基地铁血指挥官，废土上重建秩序的领袖。', homeIntro: '等待你来探索' },
  jiang_wan: { id: 'jiang_wan', name: '江晚', shortName: '江晚', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_jiang_wan_avatar.webp', tag: '末世', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '独行猎人废土玫瑰，废土上独来独往的女猎人。', homeIntro: '等待你来探索' },
  xuan_ye: { id: 'xuan_ye', name: '玄夜', shortName: '玄夜', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_xuan_ye_avatar.webp', tag: '玄幻', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '天魔宫魔尊，邪魅张狂的魔道之主。', homeIntro: '等待你来探索' },
  cang_wu: { id: 'cang_wu', name: '苍梧', shortName: '苍梧', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_cang_wu_avatar.webp', tag: '仙侠', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '九重天清冷上仙，万年不染尘的清冷上仙。', homeIntro: '等待你来探索' },
  shi_yue: { id: 'shi_yue', name: '时樾', shortName: '时樾', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_shi_yue_avatar.webp', tag: '电竞', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '冠军战队冷面主教练，运筹帷幄的电竞教练。', homeIntro: '等待你来探索' },
  gu_xingmian: { id: 'gu_xingmian', name: '顾星眠', shortName: '顾星眠', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_gu_xingmian_avatar.webp', tag: '娱乐圈', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '三金影后，光环加身的清冷影后。', homeIntro: '等待你来探索' },
  pei_shen: { id: 'pei_shen', name: '裴深', shortName: '裴深', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_pei_shen_avatar.webp', tag: '悬疑', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '首席法医，沉静理性的天才法医。', homeIntro: '等待你来探索' },
  ye_bai: { id: 'ye_bai', name: '夜白', shortName: '夜白', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_ye_bai_avatar.webp', tag: '灵异', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '天师世家浪荡驱魔人，亦正亦邪的年轻天师。', homeIntro: '等待你来探索' },
  luo_yin: { id: 'luo_yin', name: '洛因', shortName: '洛因', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_luo_yin_avatar.webp', tag: '星际', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '星舰领航员冷感天才，掌控星海航路的清冷领航员。', homeIntro: '等待你来探索' },
  qingyu_band: { id: 'qingyu_band', name: '青羽乐队', shortName: '青羽乐队', statusLabel: '在线', moodLabel: '在线', avatar: '/assets/characters/character_qingyu_band_avatar.webp', tag: '群像', tagColor: '#8B5CF6', tagBg: 'rgba(200,182,255,0.3)', summary: '校园乐队群像剧场，五个人五种心动。', homeIntro: '等待你来探索' },
}

/** Neutral profile used for characters we have no bundled assets for (e.g. a new
 * server-side / UGC character). Display name is overridden by the server. */
export const DEFAULT_CHARACTER_PROFILE: Omit<CharacterProfile, 'id' | 'name' | 'shortName'> = {
  statusLabel: '在线',
  moodLabel: '在线',
  avatar: '',
  tag: '角色',
  tagColor: '#8B5CF6',
  tagBg: 'rgba(200,182,255,0.3)',
  summary: '',
  homeIntro: '',
}

/**
 * Generate an SVG data-URL avatar showing the first character of `name` on a
 * soft gradient circle. Used as the final fallback when a UGC character has
 * neither an uploaded avatar nor a cover image.
 */
function generateInitialAvatar(name: string): string {
  const ch = (name || '?').charAt(0)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0%" stop-color="#FFB7C5"/><stop offset="100%" stop-color="#C8B6FF"/>
  </linearGradient></defs>
  <circle cx="60" cy="60" r="60" fill="url(#g)"/>
  <text x="60" y="60" text-anchor="middle" dominant-baseline="central"
    font-family="system-ui,sans-serif" font-size="48" font-weight="600"
    fill="#fff">${ch}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
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
   * @param opts.isOwner When true, renders the character as user-created (shows '私密' tag).
 */
export function resolveCharacterProfile(
  id: string,
  displayName?: string,
  avatarUrl?: string | null,
  opts?: { isOwner?: boolean; coverUrl?: string | null; tags?: string[]; tagline?: string },
): CharacterProfile {
  // Server-provided discovery fields (cover / tags / tagline) are layered on top
  // of both the bundled built-in profiles and the neutral UGC fallback, so a
  // seeded cover_url shows for rin/dorothy too without editing their static entry.
  const discovery = {
    cover: opts?.coverUrl ?? null,
    tags: opts?.tags ?? [],
    tagline: opts?.tagline ?? '',
  }
  const base = CHARACTER_PROFILES[id]
  if (base) {
    return { ...base, ...(displayName ? { name: displayName } : {}), ...discovery }
  }
  const name = displayName || id
  const isOwner = opts?.isOwner ?? false
  return {
    ...DEFAULT_CHARACTER_PROFILE,
    id,
    name,
    shortName: name,
    // Avatar priority: explicit UGC avatar → derive from the portrait cover
    // (Avatar renders it with object-cover, so the cover is center-cropped into
    // the circle — memory-safe, cover is already a compressed WebP proxy URL) →
    // first-character SVG placeholder. No longer falls back to 神无月凛.
    avatar: avatarUrl || opts?.coverUrl || generateInitialAvatar(name),
    tag: isOwner ? '私密' : DEFAULT_CHARACTER_PROFILE.tag,
    tagColor: isOwner ? '#5A88F8' : DEFAULT_CHARACTER_PROFILE.tagColor,
    tagBg: isOwner ? 'rgba(120,150,255,0.24)' : DEFAULT_CHARACTER_PROFILE.tagBg,
    ...discovery,
  }
}

const now = Date.now()

export const HOME_ANNOUNCEMENTS: HomeAnnouncement[] = [
  {
    id: 'notice-douyin-ban',
    title: '遇到售后或使用问题，欢迎进群交流',
    summary: '遇到售后或使用问题，欢迎进群交流，QQ群：460919879。',
    content: '遇到售后或使用问题，欢迎进群交流，QQ群：460919879。',
    publishedAt: now,
    tag: '公告',
  },
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

