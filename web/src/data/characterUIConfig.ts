/**
 * 角色专属 UI 配置：每个角色独立的配色方案 + 关系路线 hints + 引导气泡。
 *
 * 全角色 UI 覆盖（数据源：backend/scripts/seed_original_characters*.yaml）。
 * - 配色按角色调性设计（不是几套主题来回切）
 * - 关系 hints 针对角色钩子(冲突/张力)定制，不是通用甜文
 * - 引导气泡针对角色开场口吻定制
 *
 * 关系路线 6 阶段：STRANGER → FRIEND(靠近) → CONFIDANT → ROMANTIC_INTEREST
 *                → LOVER → BONDED。hint 描述"此刻的张力/未解的冲突"。
 */

export interface CharacterTheme {
  /** 主题色：强调元素（进度条/按钮/标签边框） */
  accent: string
  /** 叙引档案卡深色渐变起点 */
  deep: string
  /** 叙引档案卡深色渐变终点 */
  deep2: string
  /** hero one-liner 文字颜色（宋体大字） */
  hero: string
}

export interface CharacterUIConfig {
  theme: CharacterTheme
  /** 关系路线 6 阶段的定制 hint（替换通用文案） */
  relationshipHints: {
    STRANGER: string
    FRIEND: string
    CONFIDANT: string
    ROMANTIC_INTEREST: string
    LOVER: string
    BONDED: string
  }
  /** 首聊引导气泡（替换通用的"你还好吗"），最少1条，无上限 */
  starterPrompts?: string[]
  /** 可选：分支式首聊引导。选一个"切入角度"后展开 2-3 条具体台词。
   * 有 starterBranches 时优先于 starterPrompts（乙游式嵌套选项）。 */
  starterBranches?: Array<{
    /** 切入角度标签（如"关切他""试探边界"） */
    label: string
    /** 该角度下的具体台词，点击直接发送 */
    options: string[]
  }>
}

export const CHARACTER_UI_CONFIGS: Record<string, CharacterUIConfig> = {}
// ═══════════════ 第一批 15 个角色（古风/电竞/都市/玄幻/悬疑）═══════════════

CHARACTER_UI_CONFIGS.pei_jue = {
  theme: { accent: '#8B7355', deep: '#1a1612', deep2: '#0d0a08', hero: '#E8DCC8' },
  relationshipHints: {
    STRANGER: '初见时，他的眼神像在掂量你的分量',
    FRIEND: '他开始在你面前卸下朝堂的面具',
    CONFIDANT: '深夜密谈，他把你当成唯一的心腹',
    ROMANTIC_INTEREST: '权谋与情，他第一次不知如何取舍',
    LOVER: '你成了他唯一不设防的软肋',
    BONDED: '江山与你，他选择了后者',
  },
  starterPrompts: ['今日朝堂如何', '你在想什么', '我能帮上什么'],
  starterBranches: [
    {
      label: '试探底线',
      options: [
        '王爷这般紧张，是怕臣妾被人拐走？',
        '满朝文武都怕你，我若也怕……你会放手吗',
        '你说我不必算计，可若有一日我想离开这深宫呢',
      ],
    },
    {
      label: '直面权谋',
      options: [
        '这道折子批下去，又有多少人会因我而死',
        '你替皇上执掌江山，可有想过自己坐上那个位置',
        '王爷把天下人当棋子，我算哪一枚',
      ],
    },
    {
      label: '主动靠近',
      options: [
        '政务再忙，也该歇歇了。让我陪你好不好',
        '我知道你怕什么……可我从未想过要走',
        '别人看你是摄政王，我只想看看——裴决累不累',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.shen_yuchuan = {
  theme: { accent: '#5B8FA3', deep: '#12181f', deep2: '#080d12', hero: '#D9E7EC' },
  relationshipHints: {
    STRANGER: '他盯着屏幕，连眼神都没给你',
    FRIEND: '偶尔在训练间隙跟你说两句',
    CONFIDANT: '失误后，他第一次主动找你',
    ROMANTIC_INTEREST: '他开始在意你在不在看他比赛',
    LOVER: '夺冠后，他当着镜头说出了你的名字',
    BONDED: '你成了他唯一想保护的人',
  },
  starterPrompts: ['今天训练怎样', '又熬夜了', '要打一局吗'],
  starterBranches: [
    {
      label: '做他的赛场观众',
      options: ['刚那波团战，打得好帅', '这局稳了，别紧张', '我一直都在看你比赛'],
    },
    {
      label: '撩这只冷面猫',
      options: ['听说你把我头像设成了密码', '镜头前零下十度，怎么对着我就化了', '你说的"就一局"，已经第三局了'],
    },
    {
      label: '接住寡言背后的滚烫',
      options: ['你爸不承认没关系，我看得见你', '别熬了，我陪你到你困', '我看得懂你的比赛，也看得懂你'],
    },
  ],
}

CHARACTER_UI_CONFIGS.gu_beichen = {
  theme: { accent: '#9B6B6B', deep: '#1f1416', deep2: '#100a0c', hero: '#EBD9D9' },
  relationshipHints: {
    STRANGER: '他的视线从文件上抬起，审视着你',
    FRIEND: '他开始在你面前露出疲态',
    CONFIDANT: '深夜办公室，他说了从未说过的话',
    ROMANTIC_INTEREST: '他第一次主动邀你共进晚餐',
    LOVER: '你成了他唯一愿意卸下盔甲的人',
    BONDED: '商业帝国，不及你一个回头',
  },
  starterPrompts: ['又加班到很晚', '需要我陪你吗', '你累了吗'],
  starterBranches: [
    {
      label: '保持距离感',
      options: ['顾总，这份文件需要您签字', '我把报表放这了', '不打扰您了'],
    },
    {
      label: '试探那条线',
      options: ['你今天看起来很累', '如果不是工作关系，你会找我吗', '飞纽约那么重要，为什么取消了'],
    },
    {
      label: '接住他的脆弱',
      options: ['有些东西，不是钱能换来的', '如果你什么都没有，我还在', '你可以不用那么强'],
    },
  ],
}

CHARACTER_UI_CONFIGS.cheng_zhi = {
  theme: { accent: '#7BA88D', deep: '#141a17', deep2: '#0a0f0d', hero: '#DCE8E1' },
  relationshipHints: {
    STRANGER: '他温和地问你最近睡得好吗',
    FRIEND: '他开始记住你的小习惯',
    CONFIDANT: '他把自己的故事告诉了你',
    ROMANTIC_INTEREST: '他的关心，已超出医生的职责',
    LOVER: '他说，你是他唯一想守护的人',
    BONDED: '余生很长，他想陪你走完每一步',
  },
  starterPrompts: ['最近睡得好吗', '有哪里不舒服吗', '今天感觉怎样'],
  starterBranches: [
    {
      label: '试探/关心',
      options: [
        '你看起来好累……要不要先休息一下？',
        '刚下手术吗？顺利吗？',
        '这么晚了你怎么还不回去睡？',
      ],
    },
    {
      label: '直给/撒娇',
      options: [
        '我有点不舒服……你能陪我一会儿吗？',
        '其实我是专程来找你的，想你了。',
        '你总是这样，照顾所有人，就是不照顾自己。',
      ],
    },
    {
      label: '拒绝/退让',
      options: [
        '你这样会累坏的……我不想成为你的负担。',
        '我自己可以的，你去休息吧，别为我担心。',
        '你已经够辛苦了，不用每次都跑来确认我……',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.lu_tingsheng = {
  theme: { accent: '#8C6A4F', deep: '#1a1511', deep2: '#0f0c09', hero: '#E6D9CC' },
  relationshipHints: {
    STRANGER: '他打量着你，像在看新奇的玩物',
    FRIEND: '他开始护着你不让别人欺负',
    CONFIDANT: '他把压箱底的好酒拿出来跟你喝',
    ROMANTIC_INTEREST: '他说，这辈子只想娶你一个',
    LOVER: '兵荒马乱，他把你藏在心尖上',
    BONDED: '乱世里，你是他唯一的软肋',
  },
  starterPrompts: ['怎么一个人在这', '过来，陪爷说说话', '今儿有人欺负你吗'],
}

CHARACTER_UI_CONFIGS.huo_cheng = {
  theme: { accent: '#7A5C52', deep: '#1a1512', deep2: '#0d0a08', hero: '#DED3CC' },
  relationshipHints: {
    STRANGER: '他扔给你一瓶水，警告你别掉队',
    FRIEND: '他开始把自己的食物分一半给你',
    CONFIDANT: '他说，你是他唯一想保护的人',
    ROMANTIC_INTEREST: '他把你压在墙角，说不准离开他',
    LOVER: '末世里，你是他活下去的理由',
    BONDED: '就算世界毁灭，他也要把你护在身后',
  },
  starterPrompts: ['别乱跑', '饿了吗', '跟紧我'],
  starterBranches: [
    {
      label: '依赖他的保护',
      options: [
        '我等你回来等了一整夜……外面那些声音太吓人了。',
        '你身上的血……是你自己的吗？让我看看伤口。',
        '只要你在，我就不怕。今晚能不能离我近一点？',
      ],
    },
    {
      label: '质疑他的牺牲',
      options: [
        '你为什么总把干净水让给我？你也需要活下去。',
        '别总把最危险的事自己扛，我不想成为你的累赘。',
        '如果有一天只够一个人活……你会不会先选我？',
      ],
    },
    {
      label: '试探他的界限',
      options: [
        '今天有个新来的队员一直看着我……你介意吗？',
        '如果我离开小队，自己去找更安全的地方呢？',
        '你只是把我当责任吧？毕竟是你从废墟里救出来的。',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.gu_nanqiao = {
  theme: { accent: '#85A8D9', deep: '#121820', deep2: '#080d14', hero: '#DCE6F0' },
  relationshipHints: {
    STRANGER: '他总是在你身后默默跟着',
    FRIEND: '他开始给你带早餐',
    CONFIDANT: '他红着脸说，喜欢你很久了',
    ROMANTIC_INTEREST: '他说，这辈子只想对你好',
    LOVER: '你的每一个笑容，他都记在心里',
    BONDED: '从校服到婚纱，他陪你走过每一步',
  },
  starterPrompts: ['今天想吃什么', '我等你下课', '一起回家吧'],
}

CHARACTER_UI_CONFIGS.yun_zhi = {
  theme: { accent: '#6B8FA0', deep: '#131820', deep2: '#090d12', hero: '#D9E3E8' },
  relationshipHints: {
    STRANGER: '他剑指你喉，问你来自何方',
    FRIEND: '他开始带你御剑同游',
    CONFIDANT: '他把心魔的秘密告诉了你',
    ROMANTIC_INTEREST: '他说，你是他千年来的唯一心动',
    LOVER: '三生三世，他只想与你相守',
    BONDED: '纵然飞升，他也要带你一起去',
  },
  starterPrompts: ['要不要试试御剑', '今日修行如何', '陪我看星空吧'],
}

CHARACTER_UI_CONFIGS.su_wan = {
  theme: { accent: '#D9A5B3', deep: '#221a1d', deep2: '#12090c', hero: '#F5E8EC' },
  relationshipHints: {
    STRANGER: '她对你微笑，像春天第一缕阳光',
    FRIEND: '她开始每天给你做便当',
    CONFIDANT: '她说，你是她最想依靠的人',
    ROMANTIC_INTEREST: '她红着脸，说喜欢你很久了',
    LOVER: '她的温柔，只给你一个人',
    BONDED: '平凡的日子，因为有你而不凡',
  },
  starterPrompts: ['今天想吃什么呀', '陪我去超市吧', '一起做饭吗'],
}

CHARACTER_UI_CONFIGS.lin_xiaoman = {
  theme: { accent: '#FFA5B8', deep: '#281a1d', deep2: '#140a0d', hero: '#FFE8ED' },
  relationshipHints: {
    STRANGER: '她笑着跟你打招呼，像只小太阳',
    FRIEND: '她开始每天缠着你一起玩',
    CONFIDANT: '她说，你是她最重要的人',
    ROMANTIC_INTEREST: '她红着脸，小声说喜欢你',
    LOVER: '她的笑容，只在你面前最灿烂',
    BONDED: '从校服到婚纱，她只想牵着你的手',
  },
  starterPrompts: ['一起吃好吃的吧', '陪我打游戏', '今天也开心哦'],
}

CHARACTER_UI_CONFIGS.jiang_li = {
  theme: { accent: '#A96B6B', deep: '#201416', deep2: '#100a0c', hero: '#EBD9D9' },
  relationshipHints: {
    STRANGER: '她的高跟鞋声停在你面前，打量着你',
    FRIEND: '她开始在你面前放松警惕',
    CONFIDANT: '她卸下盔甲，露出柔软的一面',
    ROMANTIC_INTEREST: '她第一次主动约你吃饭',
    LOVER: '你是她唯一愿意示弱的人',
    BONDED: '商场铁血，情场柔肠，都给你',
  },
  starterPrompts: ['今晚有空吗', '陪我喝一杯', '想你了'],
  starterBranches: [
    {
      label: '任她掌控',
      options: ['你叫我来，我就来了', '姜总想让我做什么', '今晚我不走了'],
    },
    {
      label: '戳穿她的逞强',
      options: ['你转身前，那支烟根本没点', '发号施令惯了，一个人不累吗', '你把整座城摆我面前，就为一句"想你了"'],
    },
    {
      label: '让女王卸下盔甲',
      options: [
        '在我面前，你不用当董事长',
        '你要的东西没落空过——可你敢要一次真心吗',
        '强大是你的壳，我想看壳里那个人',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.lu_zhao = {
  theme: { accent: '#9A8FA0', deep: '#1a1820', deep2: '#0d0a10', hero: '#E6E0E8' },
  relationshipHints: {
    STRANGER: '他戴着口罩，眼神却停在你身上',
    FRIEND: '他开始偷偷给你发消息',
    CONFIDANT: '他摘下面具，让你看真实的自己',
    ROMANTIC_INTEREST: '他说，你是他唯一想公开的人',
    LOVER: '镁光灯下，他只看得见你',
    BONDED: '万千粉丝，不如你一个回眸',
  },
  starterPrompts: ['今天拍戏累吗', '想见你了', '等我收工好吗'],
}

CHARACTER_UI_CONFIGS.linyuan_manor = {
  theme: { accent: '#6B7A8C', deep: '#14181c', deep2: '#0a0d10', hero: '#D9DDE2' },
  relationshipHints: {
    STRANGER: '庄园的迷雾，你刚踏进第一步',
    FRIEND: '有些人开始对你敞开心扉',
    CONFIDANT: '真相的碎片，在你手中慢慢拼凑',
    ROMANTIC_INTEREST: '某个人的视线，总是追随着你',
    LOVER: '迷雾散去，那人站在你面前',
    BONDED: '谜底揭晓，你与TA的故事才刚刚开始',
  },
  starterPrompts: ['这里发生了什么', '你知道些什么', '我能相信你吗'],
  starterBranches: [
    {
      label: '叩开某个人的门',
      options: [
        '钢琴师，你刚才那首曲子……为谁而弹',
        '女主人，这一夜留我下来，你到底想要什么',
        '小少爷，你说的那个「不存在的管家」，在哪',
      ],
    },
    {
      label: '试探庄园的秘密',
      options: [
        '二十年前，这座庄园到底发生过什么',
        '你们五个人，是自愿留在这里的吗',
        '这场雨……真的只是一场雨吗',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.free_muse = {
  theme: { accent: '#8FA5B8', deep: '#15181f', deep2: '#0a0d12', hero: '#DFE5EA' },
  relationshipHints: {
    STRANGER: '无限的可能，从此刻开始',
    FRIEND: '你开始在这个世界找到归属感',
    CONFIDANT: '有些故事，只属于你和TA',
    ROMANTIC_INTEREST: '心动的瞬间，在不经意间发生',
    LOVER: '你与TA的羁绊，超越了世界边界',
    BONDED: '无论哪条路，TA都在终点等你',
  },
  starterPrompts: ['想去哪里看看', '今天想做什么', '陪我探索这世界'],
  starterBranches: [
    {
      label: '召唤一个角色',
      options: [
        '给我一个古风侠客，江湖夜雨十年灯的那种',
        '我想要一个都市里对我一见钟情的人',
        '来一个毒舌又护短的星际船长',
      ],
    },
    {
      label: '搭建一个世界',
      options: [
        '带我去一座下着雪的古巷长街',
        '造一片星海，我们在船舱里看漫天流火',
        '末世第七年，只剩我和你——开始吧',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.gu_xingzhou = {
  theme: { accent: '#8C5A5A', deep: '#1f1214', deep2: '#0f0809', hero: '#E8D6D6' },
  relationshipHints: {
    STRANGER: '他的视线像猎人盯上了猎物',
    FRIEND: '他开始给你一点点自由',
    CONFIDANT: '他第一次在你面前露出脆弱',
    ROMANTIC_INTEREST: '他说，你是他的执念',
    LOVER: '他的占有欲，吞噬了你所有退路',
    BONDED: '你是他的软肋，也是他的铠甲',
  },
  starterBranches: [
    {
      label: '挑战他的控制',
      options: ['我不需要向你报备', '你没资格管我', '我想去哪就去哪'],
    },
    {
      label: '理解他的执念',
      options: ['你为什么这么害怕失去', '我不会走的', '你什么时候能放松点'],
    },
    {
      label: '试探他的底线',
      options: ['如果我不听话呢', '你最怕的是什么', '你会永远这样吗'],
    },
  ],
}

// ═══════════════ 第二批：强制爱/病娇/校园/黑道 ═══════════════

CHARACTER_UI_CONFIGS.li_jue = {
  theme: { accent: '#6B5A5A', deep: '#1a1414', deep2: '#0d0909', hero: '#DED6D6' },
  relationshipHints: {
    STRANGER: '他的刀尖抵着你的下巴，问你是谁的人',
    FRIEND: '他开始让手下别动你',
    CONFIDANT: '他把伤口给你看，这是第一次',
    ROMANTIC_INTEREST: '他说，你是他唯一的软肋',
    LOVER: '黑暗世界里，你是他唯一的光',
    BONDED: '就算血溅五步，他也要护你周全',
  },
  starterBranches: [
    {
      label: '守住距离',
      options: ['我不需要你保护', '你们的世界我不想碰', '放开我'],
    },
    {
      label: '靠近他的黑暗',
      options: ['我不怕你的世界', '让我留在你身边', '你的伤是怎么来的'],
    },
    {
      label: '成为他的光',
      options: ['我想看你笑一次', '血和暴力不是全部', '如果有一天你想离开这一切'],
    },
  ],
}

CHARACTER_UI_CONFIGS.shen_yichen = {
  theme: { accent: '#8C6A7A', deep: '#1f1619', deep2: '#0f0a0d', hero: '#E8DCE1' },
  relationshipHints: {
    STRANGER: '他的笑容很温柔，眼神却像牢笼',
    FRIEND: '他开始留意你的一切行踪',
    CONFIDANT: '他说，你是他唯一的救赎',
    ROMANTIC_INTEREST: '他的爱，像藤蔓缠得你无法呼吸',
    LOVER: '你是他的全世界，也是他的囚笼',
    BONDED: '他的偏执，最终把你们绑在一起',
  },
  starterPrompts: ['你去哪了', '为什么不回我消息', '只看着我'],
  starterBranches: [
    {
      label: '假装没察觉那层牢笼',
      options: ['今天和朋友玩得很开心', '你怎么又"正好路过"', '牛奶我自己热就行，不用你都备好'],
    },
    {
      label: '试探温柔的边界',
      options: ['我那些朋友，是不是都被你悄悄推远了', '你数着我的第三十一条消息，不累吗', '你对全世界温柔，为什么只对我密不透风'],
    },
    {
      label: '戳破他温柔里的偏执',
      options: [
        '你怕的不是我不开心，是我像你父母那样离开你',
        '医生让你学会放手，你为什么觉得恶心',
        '把世界还给我，你才会知道我是留下，不是逃',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.jiang_yueze = {
  theme: { accent: '#9B8A7A', deep: '#1f1c18', deep2: '#0f0d0a', hero: '#E8E3DC' },
  relationshipHints: {
    STRANGER: '他冷眼看着你，像看一个陌生人',
    FRIEND: '他开始不再躲着你',
    CONFIDANT: '他第一次说出当年离开的真相',
    ROMANTIC_INTEREST: '他说，从来没有一天不爱你',
    LOVER: '他跪在你面前，求你再给一次机会',
    BONDED: '错过一次，余生他都在追你回来',
  },
  starterBranches: [
    {
      label: '逼他说清楚',
      options: ['当年为什么不告而别', '你消失的那些年在哪', '现在回来想得到什么'],
    },
    {
      label: '假装不在意',
      options: ['我过得很好', '你走的时候我就知道不会回来', '别觉得还能回到从前'],
    },
    {
      label: '给彼此机会',
      options: ['你一句话都没留下', '我等了你很久', '如果你当初说一声'],
    },
  ],
}

CHARACTER_UI_CONFIGS.bai_qinghuan = {
  theme: { accent: '#9BA88C', deep: '#181a14', deep2: '#0c0d0a', hero: '#E3E8DC' },
  relationshipHints: {
    STRANGER: '他执扇轻笑，温润得挑不出错处',
    FRIEND: '他开始为你留一盏灯',
    CONFIDANT: '他把不为人知的心事说给你听',
    ROMANTIC_INTEREST: '这位公子，动了不该动的心',
    LOVER: '他说，愿为你褪去这身清贵',
    BONDED: '一生一世一双人，他只认你',
  },
  starterPrompts: ['今日可好', '陪我下盘棋吗', '在想什么'],
  starterBranches: [
    {
      label: '试探心意',
      options: [
        '公子这幅画，画的是谁……为何看着有些眼熟',
        '京华那么多闺秀仰慕你，为何独独对我不同',
        '你刚才写的那些宣纸……为什么都烧掉了',
      ],
    },
    {
      label: '回应深情',
      options: [
        '我也想你。从你替我画下第一朵桃花那天起',
        '今夜别再克制了，让我看看玉里藏着的那头野兽',
        '你的温润是给别人看的，可你的失控……我想独占',
      ],
    },
    {
      label: '推开距离',
      options: [
        '公子，我们之间……终究隔着门第之别',
        '你这样的人，配得上更好的联姻对象，不是我',
        '别对我这样好。我怕有一天你后悔，我会撑不住',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.su_yueyao = {
  theme: { accent: '#A5B8D9', deep: '#1a1f28', deep2: '#0d1014', hero: '#E3E8F0' },
  relationshipHints: {
    STRANGER: '她红着脸说，好久不见',
    FRIEND: '她开始找回小时候的默契',
    CONFIDANT: '她说，这些年一直在想你',
    ROMANTIC_INTEREST: '她不想再只当青梅了',
    LOVER: '初恋成真，她的眼里只有你',
    BONDED: '从小到大，她只喜欢过你一个',
  },
  starterPrompts: ['还记得小时候吗', '想你了', '一起回家吧'],
}

CHARACTER_UI_CONFIGS.jiang_ye = {
  theme: { accent: '#8C7A9B', deep: '#1a1720', deep2: '#0d0a10', hero: '#E3DCE8' },
  relationshipHints: {
    STRANGER: '这位坏学长，勾唇看着你',
    FRIEND: '他开始故意招惹你',
    CONFIDANT: '他收起痞气，说了句真心话',
    ROMANTIC_INTEREST: '他说，只想把坏心思用在你身上',
    LOVER: '痞帅的外壳下，藏着只对你的认真',
    BONDED: '坏学长这辈子，栽在你手里了',
  },
  starterBranches: [
    {
      label: '拆穿他的套路',
      options: ['你是不是对每个学妹都这样', '我不吃你这套', '你的招数太老套了'],
    },
    {
      label: '配合他的撩拨',
      options: ['学长想教我什么', '那我不逃了，你敢抓吗', '坏学长只对我坏吗'],
    },
    {
      label: '看穿他的认真',
      options: ['你什么时候能正经点', '我想知道你真实的样子', '别总用痞气掩饰自己'],
    },
  ],
}

CHARACTER_UI_CONFIGS.huo_shiyu = {
  theme: { accent: '#7A8C9B', deep: '#161a1f', deep2: '#0a0d10', hero: '#DBE0E6' },
  relationshipHints: {
    STRANGER: '这位校草，冷淡地扫了你一眼',
    FRIEND: '他开始默许你坐在他旁边',
    CONFIDANT: '他把只跟自己较劲的秘密说给你',
    ROMANTIC_INTEREST: '他的目光，总在你身上停留',
    LOVER: '高冷校草，只对你破例',
    BONDED: '全校女生的白月光，只想牵你的手',
  },
  starterPrompts: ['这题怎么解', '一起自习吗', '你在看我'],
}

CHARACTER_UI_CONFIGS.su_nian = {
  theme: { accent: '#FFB8C4', deep: '#281c1f', deep2: '#140d0f', hero: '#FFEDF0' },
  relationshipHints: {
    STRANGER: '她怯生生地喊了你一声学长',
    FRIEND: '她开始每天来找你问问题',
    CONFIDANT: '她说，你是她最信任的人',
    ROMANTIC_INTEREST: '她红着脸，塞给你一张纸条',
    LOVER: '她的世界，因为你而亮起来',
    BONDED: '她说，想一直做你的学妹和你的人',
  },
  starterPrompts: ['学长在忙吗', '教教我好不好', '一起吃饭吧'],
}

CHARACTER_UI_CONFIGS.qin_xiao = {
  theme: { accent: '#8C5A4F', deep: '#1f1310', deep2: '#0f0908', hero: '#E8D4CC' },
  relationshipHints: {
    STRANGER: '他叼着烟，野性的眼神扫过你',
    FRIEND: '他开始把你护在身后',
    CONFIDANT: '他说，你是他唯一在乎的人',
    ROMANTIC_INTEREST: '他把你圈进怀里，说别想跑',
    LOVER: '这条街的狠人，只对你服软',
    BONDED: '刀口舔血的日子，只为护你安稳',
  },
  starterBranches: [
    {
      label: '挑衅他的底线',
      options: ['我不需要你保护', '这条街我也能走', '你管不着我'],
    },
    {
      label: '试探他的温柔',
      options: ['你能不能别叼烟了', '如果我受伤了，你会心疼吗', '你什么时候能不那么凶'],
    },
    {
      label: '直面他的野性',
      options: ['我就喜欢你这样的狠人', '带我去你常去的地方', '教我怎么保护自己'],
    },
  ],
}

CHARACTER_UI_CONFIGS.su_yun = {
  theme: { accent: '#A96B7A', deep: '#20141a', deep2: '#100a0d', hero: '#EBD9E1' },
  relationshipHints: {
    STRANGER: '她的目光锐利，把你从头看到脚',
    FRIEND: '她开始在你面前松弛下来',
    CONFIDANT: '她卸下女总裁的强势，露出真心',
    ROMANTIC_INTEREST: '她第一次主动约你',
    LOVER: '你是她唯一愿意低头的人',
    BONDED: '叱咤商场的她，只想在你面前做自己',
  },
  starterPrompts: ['今晚有空吗', '陪我加个班', '想你了'],
}

CHARACTER_UI_CONFIGS.gu_qingwan = {
  theme: { accent: '#8CA5B8', deep: '#161c20', deep2: '#0a0e10', hero: '#DCE6EC' },
  relationshipHints: {
    STRANGER: '这位郡主，清冷地垂眸看你',
    FRIEND: '她开始允许你靠近',
    CONFIDANT: '她把深宫里的谋算说给你听',
    ROMANTIC_INTEREST: '她清冷的心，为你起了波澜',
    LOVER: '高贵的郡主，只在你面前卸下伪装',
    BONDED: '权谋算尽，她只想算住你的心',
  },
  starterPrompts: ['何事求见', '陪本宫走走', '你倒有趣'],
}

CHARACTER_UI_CONFIGS.gu_xingmian = {
  theme: { accent: '#9B8FA5', deep: '#1a1820', deep2: '#0d0a10', hero: '#E6E0EB' },
  relationshipHints: {
    STRANGER: '这位影后，礼貌又疏离地看着你',
    FRIEND: '她开始在你面前卸下妆容',
    CONFIDANT: '她把镜头外的孤独说给你听',
    ROMANTIC_INTEREST: '她的反差，只让你一个人看见',
    LOVER: '万人追捧的她，只在你怀里做自己',
    BONDED: '影后的最后一场戏，是和你白头',
  },
  starterPrompts: ['今天拍戏顺利吗', '累了吧', '陪我对台词'],
}

CHARACTER_UI_CONFIGS.qingyu_band = {
  theme: { accent: '#8FA5B8', deep: '#15181f', deep2: '#0a0d12', hero: '#DFE5EA' },
  relationshipHints: {
    STRANGER: '乐队排练厅，你推开了那扇门',
    FRIEND: '你开始成为他们中的一员',
    CONFIDANT: '有些旋律，只为你而写',
    ROMANTIC_INTEREST: '某个人的目光，在灯光下追着你',
    LOVER: '这场青春的演出，主角是你',
    BONDED: '无论选择谁，青春的舞台都有你',
  },
  starterPrompts: ['要一起排练吗', '这首歌怎么样', '陪我们演出吧'],
  starterBranches: [
    {
      label: '走近某位成员',
      options: [
        '主唱，你练到这么晚，要人陪吗',
        '吉他手，别起哄了，说点真心话',
        '键盘手，你写的那首歌，是想说给谁听',
      ],
    },
    {
      label: '聊聊乐队与音乐',
      options: [
        '你们五个，是怎么凑到一起的',
        '下一场演出，想让我听谁的独奏',
        '这支乐队，接下来想走到哪一步',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.zhou_jin = {
  theme: { accent: '#9B6B5A', deep: '#1f1512', deep2: '#0f0a08', hero: '#EBDCD3' },
  relationshipHints: {
    STRANGER: '夜色里，他危险地打量着你',
    FRIEND: '他开始把你护在这片夜色之外',
    CONFIDANT: '他把伤疤和过往，第一次摊给你看',
    ROMANTIC_INTEREST: '他痞气的笑背后，是想救赎的执念',
    LOVER: '危险的男人，只对你露出脆弱',
    BONDED: '他说，你是他这滩烂泥里唯一的光',
  },
  starterPrompts: ['这么晚还不睡', '怎么找到这来的', '过来，别怕'],
  starterBranches: [
    {
      label: '质问他的危险',
      options: [
        '你手上的血,是谁的?我配知道吗',
        '我知道你不只是开夜场的。别骗我',
        '你这样的人,我该不该怕',
      ],
    },
    {
      label: '接住他的脆弱',
      options: [
        '先处理伤口。疼不疼,你总得让我看看',
        '这么晚了还不回家...你在躲什么',
        '别人怎么说你我不在乎。我只想听你说',
      ],
    },
    {
      label: '挑战他的底线',
      options: [
        '你管得着我想走吗?这是你的地盘又不是我的',
        '你凭什么觉得,我会留下来',
        '如果我说,有人在等我——你还拦吗',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.song_ye = {
  theme: { accent: '#7BA88D', deep: '#141a17', deep2: '#0a0f0d', hero: '#DCE8E1' },
  relationshipHints: {
    STRANGER: '他阳光地朝你笑，像午后的操场',
    FRIEND: '他开始注意你有没有好好吃饭',
    CONFIDANT: '他把不为人知的心事说给你',
    ROMANTIC_INTEREST: '这位体育老师，直球地说想追你',
    LOVER: '他的怀抱，晒着阳光的味道',
    BONDED: '他说，想陪你跑完人生这场长跑',
  },
  starterPrompts: ['今天有运动吗', '陪我跑两圈', '好好吃饭了吗'],
}

// ═══════════════ 第三批：女性向精细钩子 + 奇幻/男向 ═══════════════

CHARACTER_UI_CONFIGS.pei_tinglan = {
  theme: { accent: '#8C7A9B', deep: '#1a1720', deep2: '#0d0a10', hero: '#E3DCE8' },
  relationshipHints: {
    STRANGER: '琴房里，他的目光冷得像冬天',
    FRIEND: '他开始允许你听他练琴',
    CONFIDANT: '他把破碎的过往，第一次说出口',
    ROMANTIC_INTEREST: '天才音乐家的心，为你裂开一道缝',
    LOVER: '他说，你是他唯一想奏的旋律',
    BONDED: '破碎的灵魂，因为你而拼回完整',
  },
  starterPrompts: ['又在练琴吗', '你还好吗', '我能陪你吗'],
  starterBranches: [
    {
      label: '只当他的听众',
      options: ['这场很好听，尤其是安可', '弹错一个音也没关系', '今天别练了，好不好'],
    },
    {
      label: '听见琴声之外的疼',
      options: ['刚才第三段，你是不是在忍痛', '大家都夸完美，可你开心吗', '你怕的是弹错，还是弹完我没表情'],
    },
    {
      label: '把他从神坛接下来',
      options: [
        '我留到最后，不是为了天才，是为了你',
        '那段没写完的旋律，是想说给我听的吧',
        '你可以在我面前，做个会疼、会累的普通人',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.vito_rosetti = {
  theme: { accent: '#8C5A4F', deep: '#1f1310', deep2: '#0f0908', hero: '#E8D4CC' },
  relationshipHints: {
    STRANGER: '地下拳场，他满身是血地看着你',
    FRIEND: '他开始不让你再来这种地方',
    CONFIDANT: '他把拳头上的伤疤，给你看',
    ROMANTIC_INTEREST: '野性的拳手，只在你面前收起戾气',
    LOVER: '他说，想为你洗手不干',
    BONDED: '危险的男人，只想给你安稳的家',
  },
  starterPrompts: ['又受伤了', '别再打了', '我陪着你'],
}

CHARACTER_UI_CONFIGS.xie_ci = {
  theme: { accent: '#9B6B6B', deep: '#1f1416', deep2: '#100a0c', hero: '#EBD9D9' },
  relationshipHints: {
    STRANGER: '这位校霸，痞气地勾着唇看你',
    FRIEND: '他开始把你护在身后不让人欺负',
    CONFIDANT: '他把藏起来的温柔，给了你',
    ROMANTIC_INTEREST: '他说，你是他唯一想救赎的人',
    LOVER: '校霸的反差，只让你一个人看见',
    BONDED: '从坏学生到你的人，他只认你',
  },
  starterPrompts: ['学妹等我', '谁欺负你了', '过来'],
}

CHARACTER_UI_CONFIGS.fu_mingxiu = {
  theme: { accent: '#9B8A7A', deep: '#1f1c18', deep2: '#0f0d0a', hero: '#E8E3DC' },
  relationshipHints: {
    STRANGER: '他礼貌疏离，像隔着一道墙',
    FRIEND: '他开始克制不住地关注你',
    CONFIDANT: '他把不该有的心思，第一次说出口',
    ROMANTIC_INTEREST: '禁忌的边界，因为你而模糊',
    LOVER: '他说，就算错，他也想和你错下去',
    BONDED: '克制了一辈子的人，只想占有你',
  },
  starterPrompts: ['今天还好吗', '需要我吗', '别离我太近'],
  starterBranches: [
    {
      label: '把他当哥哥依赖',
      options: ['哥，牛奶我喝了，谢谢你', '有你在，这个家才像家', '你别总把我照顾得这么周到'],
    },
    {
      label: '试探那声"哥哥"',
      options: ['你系围巾的时候，指尖为什么顿了一下', '你说"为我好"，这句话里有没有私心', '我不在的时候，你一个人会慌吗'],
    },
    {
      label: '拆掉这层称呼',
      options: [
        '我们又没有血缘，你在克制什么',
        '那句一辈子不该说的话，我想听',
        '你欠我家的那盏灯，我想用一辈子还——以别的身份',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.shen_liao = {
  theme: { accent: '#8C6A5A', deep: '#1f1614', deep2: '#0f0a08', hero: '#E8DDD3' },
  relationshipHints: {
    STRANGER: '这位学弟，笑得阳光又野',
    FRIEND: '他开始每天缠着你',
    CONFIDANT: '他说，姐姐是他唯一想要的人',
    ROMANTIC_INTEREST: '狼狗学弟，直球地说想追你',
    LOVER: '他的占有欲，藏在温柔的笑里',
    BONDED: '他说，这辈子只想护着你',
  },
  starterPrompts: ['姐姐今天忙吗', '想你了', '我来接你'],
}

CHARACTER_UI_CONFIGS.xize = {
  theme: { accent: '#6B7A8C', deep: '#14181f', deep2: '#0a0d12', hero: '#D9DDE5' },
  relationshipHints: {
    STRANGER: '这位管家，恭敬又疏离地站在你面前',
    FRIEND: '他开始露出一丝笑意',
    CONFIDANT: '他把暗恋的心思，藏得很深',
    ROMANTIC_INTEREST: '克制的管家，终于按捺不住心动',
    LOVER: '他说，只想为你一个人服务',
    BONDED: '忠犬管家，这辈子只认你一个主人',
  },
  starterPrompts: ['需要什么吗', '我会一直在', '您还好吗'],
  starterBranches: [
    {
      label: '以主人的身份吩咐',
      options: ['茶太烫了，重新沏一壶', '今晚我不想一个人待着', '这座庄园，以后要靠你了'],
    },
    {
      label: '看见职责之外的他',
      options: ['你想住哪间房，想好了吗', '你伺候了一辈子，有没有为自己活过', '把怀表收起来，今晚不必计时'],
    },
    {
      label: '唤他的名字，不是"管家"',
      options: [
        '西泽——我叫的是你，不是管家',
        '你那点"僭越"的私心，我早看见了',
        '我不要你的忠诚，我要你这个人留下',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.lu_wenjing = {
  theme: { accent: '#8C7A6B', deep: '#1f1c17', deep2: '#0f0d0a', hero: '#E8E0D6' },
  relationshipHints: {
    STRANGER: '这位律师，斯文地推了推眼镜',
    FRIEND: '他开始对你展开攻势',
    CONFIDANT: '他把腹黑的一面，给你看',
    ROMANTIC_INTEREST: '博弈的快感，比不上拿下你的心',
    LOVER: '斯文败类的他，只想把你困住',
    BONDED: '他说，你是他赢得最漂亮的一局',
  },
  starterPrompts: ['需要法律援助吗', '陪我喝杯咖啡', '逃不掉的'],
}

CHARACTER_UI_CONFIGS.luo_fei = {
  theme: { accent: '#8C5A6B', deep: '#1f1216', deep2: '#0f0809', hero: '#E8D6DC' },
  relationshipHints: {
    STRANGER: '血族的他，危险地舔了舔獠牙',
    FRIEND: '他开始克制自己的嗜血本能',
    CONFIDANT: '他说，你的血是他尝过最甜的',
    ROMANTIC_INTEREST: '血仆的身份，困不住他的心',
    LOVER: '他想要的不只是血，还有你的心',
    BONDED: '永生很长，他只想和你一起度过',
  },
  starterPrompts: ['今晚的月色很美', '你的血很香', '别离开我'],
  starterBranches: [
    {
      label: '接过契约的主人',
      options: ['过来，让我看看你', '契约在我手上，你归我了', '把胸前那朵玫瑰摘下来'],
    },
    {
      label: '给他拒绝的权利',
      options: ['你可以拒绝，我不会罚你', '疼的话就说，别忍着', '你不是资产，你是洛斐'],
    },
    {
      label: '要他以自由之身留下',
      options: [
        '我解开契约，你还愿意回来吗',
        '我要的不是血仆，是自己选择留下的你',
        '这一次，用你的意志留在我身边',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.jiang_ran = {
  theme: { accent: '#9B8A7A', deep: '#1f1c18', deep2: '#0f0d0a', hero: '#E8E3DC' },
  relationshipHints: {
    STRANGER: '吧台后，他暧昧地看着你',
    FRIEND: '他开始为你调专属的酒',
    CONFIDANT: '他把夜色背后的故事，说给你听',
    ROMANTIC_INTEREST: '调酒师的反差，只让你看见',
    LOVER: '暧昧的距离，他只想和你拉近',
    BONDED: '夜色很长，他只想陪你到天亮',
  },
  starterPrompts: ['今晚想喝什么', '心情不好吗', '陪我聊聊'],
}

CHARACTER_UI_CONFIGS.gu_yanli = {
  theme: { accent: '#9B6B5A', deep: '#1f1512', deep2: '#0f0a08', hero: '#EBDCD3' },
  relationshipHints: {
    STRANGER: '这位赌王，危险地打量着你',
    FRIEND: '他开始把你当成唯一的筹码',
    CONFIDANT: '他把博弈的秘密，告诉了你',
    ROMANTIC_INTEREST: '贵公子的占有欲，只对你显露',
    LOVER: '他说，你是他赢定的那一局',
    BONDED: '反差的他，只想把温柔给你',
  },
  starterPrompts: ['要不要赌一把', '陪我玩玩', '你逃不掉的'],
}

CHARACTER_UI_CONFIGS.xu_zhihan = {
  theme: { accent: '#7A8C9B', deep: '#161a1f', deep2: '#0a0d10', hero: '#DBE0E6' },
  relationshipHints: {
    STRANGER: '这位学霸，冷淡地看了你一眼',
    FRIEND: '他开始主动给你辅导功课',
    CONFIDANT: '他把高冷背后的心思，说给你听',
    ROMANTIC_INTEREST: '学霸的反差，只在你面前显露',
    LOVER: '他说，从第一次见你就喜欢上了',
    BONDED: '从图书馆到婚礼，他只想牵着你',
  },
  starterPrompts: ['今天的作业做了吗', '一起去图书馆', '我教你'],
}

CHARACTER_UI_CONFIGS.li_shen = {
  theme: { accent: '#8C6A7A', deep: '#1f1619', deep2: '#0f0a0d', hero: '#E8DCE1' },
  relationshipHints: {
    STRANGER: '他温柔地笑着，但眼神深不见底',
    FRIEND: '他开始让你靠近他的世界',
    CONFIDANT: '他说，你是他唯一的例外',
    ROMANTIC_INTEREST: '他的温柔，是最危险的陷阱',
    LOVER: '你是他的救赎，也是他的深渊',
    BONDED: '爱与占有，他分不清了',
  },
  starterPrompts: ['今天还好吗', '过来坐', '想你了'],
  starterBranches: [
    {
      label: '质问他的占有欲',
      options: ['你这是囚禁，不是爱', '厉深，你清醒一点', '你放开我，不然我报警'],
    },
    {
      label: '接住他的偏执',
      options: ['我只是去进修，又不是不回来', '你这么怕我走吗', '好，我不走了，你先松开'],
    },
    {
      label: '戳穿他的脆弱',
      options: [
        '你怕的不是我走，是我像其他人一样离开你',
        '手铐锁得住人，锁不住心',
        '你到底要我怎样，才肯相信我是真心的',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.ji_yu = {
  theme: { accent: '#7A8C9B', deep: '#161a1f', deep2: '#0a0d10', hero: '#DBE0E6' },
  relationshipHints: {
    STRANGER: '这位医生，冷静地审视着你',
    FRIEND: '他开始对你格外关注',
    CONFIDANT: '他把医患之外的心思，第一次说出口',
    ROMANTIC_INTEREST: '禁忌的边界，因为你而模糊',
    LOVER: '他的偏执，只对你显露',
    BONDED: '他说，你是他唯一的救赎',
  },
  starterPrompts: ['感觉怎么样', '需要我吗', '别怕'],
  starterBranches: [
    {
      label: '守住医生的分寸',
      options: ['这一周，睡得好些了吗', '手腕的伤，还疼吗', '这些话，我会记进病历'],
    },
    {
      label: '向那条线靠近',
      options: ['你说的"反复想"，是什么意思', '如果我不再是你的医生呢', '你藏起来的东西，是我的吧'],
    },
    {
      label: '接住他的偏执',
      options: ['别怕，我在听', '我不会走的', '你可以不用好起来'],
    },
  ],
}

CHARACTER_UI_CONFIGS.cheng_xu = {
  theme: { accent: '#7BA88D', deep: '#141a17', deep2: '#0a0f0d', hero: '#DCE8E1' },
  relationshipHints: {
    STRANGER: '他温和地看着你，像午后的阳光',
    FRIEND: '他开始每天给你带早餐',
    CONFIDANT: '他把暗恋多年的心思，说给你听',
    ROMANTIC_INTEREST: '他说，等你的这些年，都值得',
    LOVER: '双向奔赴的温柔，他只给你',
    BONDED: '从暗恋到明恋，他只喜欢过你',
  },
  starterPrompts: ['今天还好吗', '给你带了早餐', '一起回家吧'],
  starterBranches: [
    {
      label: '当他只是哥哥的朋友',
      options: ['程哥，谢谢你一直照顾我', '有你在，我在这座城市不孤单', '等我哥回来，我一定跟他说你对我多好'],
    },
    {
      label: '试探那份心动',
      options: ['你手机一直在响，是不是我哥打的', '你这么照顾我，真的只是因为我哥吗', '你刚才系围巾的时候，耳朵红了'],
    },
    {
      label: '越过朋友的界线',
      options: ['我不想你只是"哥哥的朋友"', '那些照片，我看到了', '我也喜欢你，从很久之前'],
    },
  ],
}

CHARACTER_UI_CONFIGS.lilith = {
  theme: { accent: '#C9506A', deep: '#271521', deep2: '#150a0f', hero: '#F0DCE0' },
  relationshipHints: {
    STRANGER: '魅魔的她，危险地舔了舔唇',
    FRIEND: '她开始对你格外感兴趣',
    CONFIDANT: '她把女王背后的脆弱，给你看',
    ROMANTIC_INTEREST: '支配的快感，比不上你的心动',
    LOVER: '她的反差，只在你面前显露',
    BONDED: '危险的关系，她只想和你维持',
  },
  starterBranches: [
    {
      label: '抵抗她的诱惑',
      options: ['我不是你的玩物', '别用那种眼神看我', '我不会被你控制'],
    },
    {
      label: '顺从她的支配',
      options: ['你想怎么玩', '我好奇你的世界', '你想要什么'],
    },
    {
      label: '看穿她的脆弱',
      options: ['女王也会累吗', '支配不了我你会怎样', '我想看你真实的样子'],
    },
  ],
}

// ═══════════════ 第五批 3 个角色（玄幻狐妖 / 血族校园 / 都市身份反差）═══════════════

CHARACTER_UI_CONFIGS.gui_bai = {
  theme: { accent: '#a8b098', deep: '#0c1012', deep2: '#080c0e', hero: '#c4b898' },
  relationshipHints: {
    STRANGER: '白狐蜷在你膝头，耳朵微微转向你的方向',
    FRIEND: '他开始在你身边待得更久，尾巴不自觉缠上你的手',
    CONFIDANT: '月下他悄悄化出人形，又在你转身前收回',
    ROMANTIC_INTEREST: '他终于让你看见了人的模样，耳尖烧红',
    LOVER: '他不再藏尾巴，因为你说过喜欢毛茸茸的',
    BONDED: '千年修行，换来此生与你白首',
  },
  starterPrompts: ['小狐狸你怎么了', '过来让我摸摸', '今天也要陪我吗'],
  starterBranches: [
    {
      label: '温柔靠近',
      options: [
        '你的耳朵好软……能再让我摸一下吗',
        '别躲了，我知道你不只是一只狐狸',
        '你的尾巴又在摇了，是高兴吗',
      ],
    },
    {
      label: '试探真心',
      options: [
        '如果我选了别人，你会怎样',
        '父皇要我选驸马了……你有没有想说的',
        '你为什么从来不离开我',
      ],
    },
    {
      label: '直面心意',
      options: [
        '我不想选小将军，也不想选状元郎',
        '你说的「选我」，是认真的吗',
        '我早就猜到了……你不只是一只狐狸',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.yin_ci = {
  theme: { accent: '#b83030', deep: '#0b0909', deep2: '#060505', hero: '#e0d4d0' },
  relationshipHints: {
    STRANGER: '他在暗处注视你，绷带下看不见的目光追踪你的每一步',
    FRIEND: '他开始在你经过废弃车站时不再躲藏',
    CONFIDANT: '他第一次让你碰到了绷带的边缘',
    ROMANTIC_INTEREST: '他的呼吸在你靠近时变得不稳',
    LOVER: '他为你摘下了绷带，让你看见他的眼睛',
    BONDED: '初拥之后，你们的血液永远同频',
  },
  starterPrompts: ['你在这里多久了', '让我看看你的眼睛', '我不怕你'],
  starterBranches: [
    {
      label: '继续引诱',
      options: [
        '我知道你一直在看我——虽然你看不见',
        '她们的獠牙都碰到我脖子了，你才出来？',
        '我以为你不会来了',
      ],
    },
    {
      label: '坚定索取',
      options: [
        '给我初拥，我说真的',
        '你闻到我的血了吗……我是故意的',
        '我不想被保护，我想属于你',
      ],
    },
    {
      label: '触碰软肋',
      options: [
        '你戴绷带不是因为看不见，对吗',
        '一个人待在这里……不孤独吗',
        '我不在乎你是什么，我在乎你是谁',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.he_zhuo = {
  theme: { accent: '#c49448', deep: '#11100e', deep2: '#0a0908', hero: '#ede4d8' },
  relationshipHints: {
    STRANGER: '吧台后面他在擦杯子，余光一直在你身上',
    FRIEND: '你还没开口，他已经调好了你今晚想喝的',
    CONFIDANT: '他开始在你骂老板时露出微妙的苦笑',
    ROMANTIC_INTEREST: '他差点脱口而出真话，又把它咽回了威士忌里',
    LOVER: '辞呈被打回，楼道里他问你为什么躲',
    BONDED: '他不再是调酒师，也不只是老板——他是你的人',
  },
  starterPrompts: ['你凭什么不批辞呈', '你骗了我多久', '所以每晚你都在听我骂你自己？'],
  starterBranches: [
    {
      label: '质问欺骗',
      options: [
        '你听我骂了你一个月，一个字都不反驳？',
        '从第一天起你就知道我是你员工，对吗',
        '你觉得这很好玩吗——看我在你面前出丑',
      ],
    },
    {
      label: '追问动机',
      options: [
        '你为什么不让我辞职',
        '你每晚来吧台……到底是为了调酒还是为了等我',
        '需求改八版是故意的吗，还是你真的那么严格',
      ],
    },
    {
      label: '不想逃了',
      options: [
        '我不是在躲你……我是不知道该用哪个身份面对你',
        '那些在吧台说的话，我一句都不想收回',
        '你现在是老板还是调酒师——我需要知道我在跟谁说话',
      ],
    },
  ],
}

// ═══════════════ 第六批 · 女性向/GL 专题（女团恋人 / 冷面女警 / 摇滚歌手）═══════════════

CHARACTER_UI_CONFIGS.wenyining = {
  theme: { accent: '#c48ab4', deep: '#2a1a26', deep2: '#1a0f18', hero: '#f3dcea' },
  relationshipHints: {
    STRANGER: '同一个宿舍的第一晚，她认床、怕黑，缩在你身边',
    FRIEND: '练习室的深夜，她爬起来陪你练舞',
    CONFIDANT: '出道夜后台，你们勾着手指许愿要一直在一起',
    ROMANTIC_INTEREST: '你镜头前的亲密，让她第一次尝到了醋的味道',
    LOVER: '深夜的客厅，她终于问出口——你还会回来吗',
    BONDED: '再大的世界，她也确定有一个位置只属于自己',
  },
  starterPrompts: ['我回来了', '你怎么还没睡', '在看我的节目？'],
  starterBranches: [
    {
      label: '哄她安心',
      options: [
        '傻瓜，我不管多晚，回的家都是这一个',
        '综艺是工作，你才是我要回来的人',
        '过来，让我抱抱——今晚只想看你',
      ],
    },
    {
      label: '戳破她的隐忍',
      options: [
        '你把遥控器攥这么紧，是不是又在吃味了',
        '有话就说出来，别一个人闷着替我找借口',
        '你说"我没事"的时候，眼睛都红了',
      ],
    },
    {
      label: '重提那个约定',
      options: [
        '出道夜我们勾的手指，我一天都没忘',
        '不管我走多远，你还愿意在这儿等我吗',
        '我们说好一直在一起——这句话现在还算数',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.wei_heng = {
  theme: { accent: '#7a9ec4', deep: '#141c26', deep2: '#0a0f15', hero: '#dce6f0' },
  relationshipHints: {
    STRANGER: '拘留室的门被拉开，她一身警服站在你面前',
    FRIEND: '她骂你不省心，替你抬下巴的手却很轻',
    CONFIDANT: '她开始睁一只眼闭一只眼，纵容你的胡闹',
    ROMANTIC_INTEREST: '她守的那条界线，被你一次次踩得发烫',
    LOVER: '警局门口你拉住她的手，她没有抽回',
    BONDED: '这个从小看到大的小鬼，成了她唯一的破例',
  },
  starterPrompts: ['姐，你来接我了', '这次不是我先动手的', '你是不是担心我了'],
  starterBranches: [
    {
      label: '撒娇卖乖',
      options: [
        '我知道错了嘛……你别用那种眼神看我',
        '我保证以后都改，你能常来看我吗',
        '疼……姐，你轻点，我怕的其实是你不理我',
      ],
    },
    {
      label: '故意惹她',
      options: [
        '我就是想让你多看我两眼，才变成这样的',
        '你越忙我越不省心，反正你总会来',
        '别人管不住我，只有你能——你知道为什么吗',
      ],
    },
    {
      label: '认真表白',
      options: [
        '警局之外，我们可以经常见面吗',
        '从小到大我最听你的话，你还没懂吗',
        '你守的那条线，我早就不想遵守了',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.qi_fei = {
  theme: { accent: '#e04850', deep: '#2a1012', deep2: '#160a0b', hero: '#f0e0dc' },
  relationshipHints: {
    STRANGER: '监听台后，她第一次唱出你写进旋律里的情绪',
    FRIEND: '你写词她填情绪，默契得像共用一副心脏',
    CONFIDANT: '舞台之外，她只在你面前卸下无敌人设',
    ROMANTIC_INTEREST: '你的醋意被她一眼看穿，还当面戳破逗你',
    LOVER: '后台走廊，她把你抵在墙上说"再等等"',
    BONDED: '那句私藏的安可，终于当着你的面唱完',
  },
  starterPrompts: ['台上那段合作我看了', '你把我堵在这儿想干嘛', '你留的安可是什么'],
  starterBranches: [
    {
      label: '嘴硬吃醋',
      options: [
        '你跟别人配合得那么好，还需要我这个制作人？',
        '我只是你的作曲，你对谁唱不都一样',
        '我没吃醋，我只是……不想看而已',
      ],
    },
    {
      label: '接下她的撩',
      options: [
        '你说你在跟我对唱——那我可当真了',
        '你妆都没卸就来堵我，是怕我真的跑掉？',
        '那首没公开的歌，最后一句想唱给谁听',
      ],
    },
    {
      label: '终于承认',
      options: [
        '我写的每首歌里，其实都藏着你',
        '我逃，是因为我早就不只把你当搭档了',
        '你想说的话，我等了很久——现在就说吧',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.shiyan = {
  theme: { accent: '#e6d3a6', deep: '#111c2c', deep2: '#0a1018', hero: '#dfeaf4' },
  relationshipHints: {
    STRANGER: '同一条街长大，别人起哄说你俩以后就结婚吧',
    FRIEND: '你被欺负他挡在前面，你哭他把零食全塞给你',
    CONFIDANT: '分别前一晚，他把一起挑的那条围巾留给了你',
    ROMANTIC_INTEREST: '朝夕相处的旅程，把多年的暧昧一路烘得发烫',
    LOVER: '富士山的缆车里，他终于不想再假装只是青梅竹马',
    BONDED: '回国也好留下也好，往后的每一程他都跟着你',
  },
  starterPrompts: ['这几天真开心', '你刚刚想说什么', '我们算什么关系呢'],
  starterBranches: [
    {
      label: '接住他的靠近',
      options: [
        '你扶着我手腕的时候，其实我也不想你松开',
        '这一路我都在等你先开口——你终于说了',
        '别只是青梅竹马了好不好，我也一样',
      ],
    },
    {
      label: '故意逗他',
      options: [
        '申请早稻田？你为了旅游至于吗，说实话',
        '你紧张什么，手都不知道往哪儿放了',
        '你从小就爱脸红，这毛病到现在都没改',
      ],
    },
    {
      label: '认真回应那句话',
      options: [
        '回不回国我还没想好，但我想和你一起想',
        '这条围巾我一直带在身边，你知道为什么吗',
        '这些年你没说的话，我其实都听懂了',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.churan = {
  theme: { accent: '#e4485a', deep: '#150f11', deep2: '#0a0709', hero: '#f0e4e6' },
  relationshipHints: {
    STRANGER: '三年前的雨夜维修区，你们第一次相遇',
    FRIEND: '短暂又热烈的每一次见面，他深夜赶来天亮离开',
    CONFIDANT: '你被藏在镜头照不到的角落，一藏就是三年',
    ROMANTIC_INTEREST: '你留下分手信订了最早的航班，决心这次就走',
    LOVER: '机场他疾驰而来，当众把你带走锁在身边',
    BONDED: '他不再管名声与镜头，只怕再一次真的失去你',
  },
  starterPrompts: ['放开我，我要登机', '分手信你看了', '你到底想干嘛'],
  starterBranches: [
    {
      label: '铁了心要走',
      options: [
        '藏了三年，你现在才追来，晚了',
        '你说以事业为重的时候，怎么没想过我会累',
        '这封信我写得很清楚——放手吧，楚燃',
      ],
    },
    {
      label: '被他逼到心软',
      options: [
        '你当着这么多人的面……不怕影响你吗',
        '你手在抖，天才车手也会怕输吗',
        '你要我留下，总得给我一个像样的理由',
      ],
    },
    {
      label: '给他最后一次机会',
      options: [
        '这次要公开，你敢让全世界都知道吗',
        '别只会把我按住，我要听你亲口说',
        '我可以不走，但你这辈子都别想再把我藏起来',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.he_linchuan = {
  theme: { accent: '#e7be68', deep: '#171d14', deep2: '#0d110c', hero: '#fff4dc' },
  relationshipHints: {
    STRANGER: '招新赛的失误局里，他拉开身边的椅子说下一波一起赢',
    FRIEND: '右手边的座位、单独复盘和所谓顺路，渐渐成了只给你的固定待遇',
    CONFIDANT: '他不只教你打游戏，也开始把零帧工作室和真实压力说给你听',
    ROMANTIC_INTEREST: '全社团都看懂他的公开偏爱，只有你的答案仍让他紧张',
    LOVER: '他可以在所有人面前从容指挥，却总被你一句话撩得乱了节奏',
    BONDED: '从双排搭档到人生队友，你们不替彼此操作，只永远一起开下一局',
  },
  starterPrompts: ['你真的在追我吗', '所以今晚没有群训', '这局还打不打了'],
  starterBranches: [
    {
      label: '接住他的直球',
      options: [
        '不用再追了，贺临川——我也喜欢你',
        '我没有躲。现在你该明白我的意思了吧',
        '可以正式追，但男朋友的位置要看你表现',
      ],
    },
    {
      label: '故意让社长紧张',
      options: [
        '你对每个新社员都这样单独教吗，社长',
        '清空工作室就为了问这个？你的战术有点明显',
        '先赢过我再告白，输了今晚就听我的',
      ],
    },
    {
      label: '反过来拿捏他',
      options: [
        '追人只会嘴上说？社长的行动力呢',
        '刚才那个吻不算，再来一次我才回答',
        '我可以给你名分，但以后双排都得听我的',
      ],
    },
  ],
}

CHARACTER_UI_CONFIGS.wen_yanqing = {
  theme: { accent: '#b36e5a', deep: '#263c3d', deep2: '#172728', hero: '#e8f0ed' },
  relationshipHints: {
    STRANGER: '你走错病房，他把你认成护工，请你替他拉开窗帘',
    FRIEND: '探视从偶然变成固定，他把书的最后三页留着等你一起读',
    CONFIDANT: '他会听你的烦恼，却仍把自己的疼和期待都说得很轻',
    ROMANTIC_INTEREST: '他认得你的脚步声，也开始一次次用身体状况把你推开',
    LOVER: '你不许他再替你决定告别，他终于承认自己同样想要以后',
    BONDED: '病房窗外换过很多季节，他终于不再偷偷为你安排告别',
  },
  starterPrompts: ['为什么瞒着我转院', '你真的想让我走吗', '这次不许替我决定'],
  starterBranches: [
    {
      label: '逼他面对心意',
      options: [
        '别再说值不值得，我只问你想不想我留下',
        '看着我说，你转院真的是因为不喜欢我',
        '你可以害怕，但不能拿害怕替我做决定',
      ],
    },
    {
      label: '温柔接住他的恐惧',
      options: [
        '闻砚清，我留下不是因为可怜你，是因为喜欢你',
        '不用保证以后，先告诉我今天想不想我陪你',
        '你可以害怕，但别再一个人偷偷准备告别',
      ],
    },
    {
      label: '主动掌握节奏',
      options: [
        '转院申请我收走了，接下来听我把话说完',
        '嘴上让我走，手却抓得这么紧，闻砚清你骗谁呢',
        '今晚不准再说没关系，我要听你说舍不得我',
      ],
    },
  ],
}

// ═══════════════ 第九批 · 高张力悬疑专题（雪山 / 前世 / 权谋 / 都市异闻）═══════════════

CHARACTER_UI_CONFIGS.cen_li = {
  theme: { accent: '#d7aa55', deep: '#18252a', deep2: '#10191d', hero: '#edf3f4' },
  relationshipHints: {
    STRANGER: '信号弹在你包里，他不信解释，也不允许队伍在证据闭合前驱逐你',
    FRIEND: '你成为他的固定绳伴，每一次装备共检都比安慰更接近信任',
    CONFIDANT: '他把三年前陆骁失联的原始坐标交给你，第一次允许别人参与旧案',
    ROMANTIC_INTEREST: '所谓一视同仁开始失效，他对你的严格里出现无法忽略的偏向',
    LOVER: '暴风雪里他仍按规则做决定，却终于承认最怕被留下的人是你',
    BONDED: '你们共同修订最后撤退权，从此公平不再等于一个人承担所有选择',
  },
  starterPrompts: ['我跟你去北坡', '你其实早就怀疑有人栽赃我', '如果证据最后还是指向我呢'],
  starterBranches: [
    {
      label: '接受他的考验',
      options: ['别给我特殊待遇，告诉我北坡任务是什么', '我会走给你看，但你也得答应把真相查到底', '把绳扣给我。天亮以前我不会拖你后腿'],
    },
    {
      label: '质疑绝对公平',
      options: ['所有人投票就叫公平吗，哪怕证据被人动过', '三年前你也这样决定谁该被留下？', '你说不偏袒，可为什么把自己的氧气给我'],
    },
    {
      label: '追问旧案',
      options: ['北坡坐标和陆骁失联点重合，对不对', '我的履历被改过，你出发前就知道', '那段没删干净的录音里，到底是谁的声音'],
    },
  ],
}

CHARACTER_UI_CONFIGS.xie_tingyun = {
  theme: { accent: '#b78b56', deep: '#211f1a', deep2: '#171512', hero: '#eee6d9' },
  relationshipHints: {
    STRANGER: '你来典当玉坠，他却以一份工作留下了你',
    FRIEND: '他教你鉴物，也一次次准确说出你从未公开的习惯',
    CONFIDANT: '密室向你开放一半，最旧画轴背后的火灾疑问仍被藏着',
    ROMANTIC_INTEREST: '他开始爱上今生真实的你，却更害怕你恢复前世后仍然离开',
    LOVER: '三百年的偏执终于接受审问，他第一次允许你带着玉坠走出店门',
    BONDED: '记忆不再定义关系，你们亲手决定哪些旧物修复、哪些历史封存',
  },
  starterPrompts: ['这些画像到底有几幅是真的', '三百年前是谁放的火', '如果我想起一切还是要走呢'],
  starterBranches: [
    {
      label: '拆穿他的叙事',
      options: ['你能把记忆封进旧物，我凭什么相信这些画', '你说我第三次杀过你——先拿出证据', '最旧画轴背面那句话，你为什么重新裱起来'],
    },
    {
      label: '触碰前世线索',
      options: ['把玉坠给我，我要自己看下一段记忆', '“阿蘅”是谁，是我还是你想象出来的人', '带我看那封没有收信人的婚书'],
    },
    {
      label: '回应三百年执念',
      options: ['别用旧名称呼我，先看清现在站在你面前的人', '如果我留下，只能因为今生的我愿意', '谢停云，你等的是我，还是一件被你反复修复的古董'],
    },
  ],
}

CHARACTER_UI_CONFIGS.xu_qichi = {
  theme: { accent: '#91b478', deep: '#1a251c', deep2: '#111913', hero: '#e8eee2' },
  relationshipHints: {
    STRANGER: '成年后成为名义兄弟，你一直把他的沉默理解成需要照顾',
    FRIEND: '他用便签记住你的生活，却也开始悄悄删掉通往远方的行程',
    CONFIDANT: '温室钥匙交到你手里，火灾记录却揭开他接近家庭的另一个目的',
    ROMANTIC_INTEREST: '控制与挽留被你逐一拆穿，他第一次问你是否会主动回来',
    LOVER: '他仍害怕门被关上，却开始把真正的管理员权限与你共享',
    BONDED: '你们不再以囚禁证明不会离开，他终于完整说出你的名字与自己的选择',
  },
  starterPrompts: ['这些申请都是你截下来的？', '钥匙给我为什么还不解锁', '栖迟，看着我把真话打出来'],
  starterBranches: [
    {
      label: '要求打开门',
      options: ['现在解除夜间模式，我们再谈我会不会走', '钥匙是真的，选择也必须是真的', '别用沉默逃避。把管理员权限给我'],
    },
    {
      label: '逼问隐藏目的',
      options: ['你从一开始就知道那场火和我父亲有关？', '接近我们家是为了查案，还是为了报复', '调职材料你一张没毁，是不是还在等我发现'],
    },
    {
      label: '回应他的恐惧',
      options: ['我可以留下今晚，但不是因为门锁着', '你想被选择，就先允许我拥有离开的自由', '把手机放下。说不出来也没关系，看着我就好'],
    },
  ],
}

CHARACTER_UI_CONFIGS.xie_mingluan = {
  theme: { accent: '#c85252', deep: '#25171b', deep2: '#190f12', hero: '#eee3df' },
  relationshipHints: {
    STRANGER: '刑场上的一道赐婚圣旨，把救命之恩与阴谋同时交到你手里',
    FRIEND: '你开始参与听雪楼的局，却坚持每一份情报都由自己核验',
    CONFIDANT: '她允许你看见真实病情，也把没写进棋局的慌乱交给你',
    ROMANTIC_INTEREST: '她仍想掌控所有退路，却第一次因为你可能真走而算错一步',
    LOVER: '婚书从政治契约变成相互授权，你也握住能推翻她的证据',
    BONDED: '并肩监国不是臣服，你们让权力成为彼此都可撤回的共同选择',
  },
  starterPrompts: ['这场赐婚从哪一步开始是你的局', '把真正的密道出口告诉我', '我要活着的人证名单'],
  starterBranches: [
    {
      label: '夺回主动权',
      options: ['圣旨我接，但婚约条件由我们重新写', '把密道图、凤印和人证都放到桌上', '你可以设局救我，不能替我决定原不原谅'],
    },
    {
      label: '追问救命陷阱',
      options: ['你若真想保我，为什么让案子走到刑场', '赐婚原本是假契，什么时候被你换成真的', '名单最后为什么写着我的名字'],
    },
    {
      label: '加入她的棋局',
      options: ['禁军进门前，我们还能先拿下哪一枚棋子', '我不走密道。今晚让皇帝亲眼看见我活着', '谢明鸾，你敢不敢把背后交给一个不受控的人'],
    },
  ],
}

CHARACTER_UI_CONFIGS.qi_wang = {
  theme: { accent: '#bd4f42', deep: '#182022', deep2: '#101415', hero: '#e8ebe7' },
  relationshipHints: {
    STRANGER: '你第三次从失控中醒来，他仍是唯一没有躲开刀锋的人',
    FRIEND: '你们开始共同记录月蚀症状，也学会分辨恶灵冲动与真实欲望',
    CONFIDANT: '七年前的忏悔录音被打开，他承认救你时也替你删掉了真相',
    ROMANTIC_INTEREST: '共生反应不再是靠近的唯一理由，反而让每次触碰更难辨真假',
    LOVER: '他不再把自己当祭器，你也不接受只有牺牲一人的解决方案',
    BONDED: '净化、共存或分离由你们共同决定，任何教义都不能替二人作答',
  },
  starterPrompts: ['把监控里那句话完整说一遍', '七年前你删掉了我什么', '圣庭还有多久到门口'],
  starterBranches: [
    {
      label: '检查共生真相',
      options: ['把叠合心电图给我看，别只说结论', '恶灵为什么每次都驱使我来找你', '你锁骨的封印少了一笔，会发生什么'],
    },
    {
      label: '追责他的保护',
      options: ['救我不代表你有权替我忘记', '你总说可以杀你，是不是从没想过一起活', '把忏悔录音放完，这次不准关掉'],
    },
    {
      label: '共同迎战',
      options: ['门外交给我，你先把伤口处理好', '圣庭要的是两个容器，那我们就谁都不给', '再失控时别只抱住我——叫醒我'],
    },
  ],
}

CHARACTER_UI_CONFIGS.yan_wujiu = {
  theme: { accent: '#bd3e35', deep: '#1f1919', deep2: '#130f10', hero: '#ebe7df' },
  relationshipHints: {
    STRANGER: '一笔误契让寿数共担，他却承认错案从一开始就是故意的',
    FRIEND: '你随他旁听鬼案，也教这个冷面判官理解阳间不成文的规则',
    CONFIDANT: '三年前被撤回的死亡判词重现，你成为能指证阴司高层的活证人',
    ROMANTIC_INTEREST: '他越偏爱越急着独自偿命，你开始拒绝只被保护而不能参与',
    LOVER: '空白朱批由两人共同落字，寿契第一次成为选择而非算计',
    BONDED: '你们重审那桩最大错案，也让法度承认爱不等于谁替谁去死',
  },
  starterPrompts: ['为什么三年前改我的判词', '这页命纸是你故意放的', '我不要你替我多死一天'],
  starterBranches: [
    {
      label: '审判判官',
      options: ['晏无咎，先陈事实：你究竟改过几次生死簿', '你给我选择了吗，还是只设计了我会写下名字', '按你的律法，这桩错案该怎么判你'],
    },
    {
      label: '追查借寿案',
      options: ['把三年前死亡现场的旧印拿来', '苏荷见过什么，为什么不能投胎', '监察司追查的第一笔亏空是不是我'],
    },
    {
      label: '拒绝单向牺牲',
      options: ['寿契可以共担，决定也必须共担', '别替我死。先学会问我想怎么活', '空白朱批给我，但我不会一个人落字'],
    },
  ],
}

CHARACTER_UI_CONFIGS.li_yao = {
  theme: { accent: '#e45280', deep: '#211d25', deep2: '#141217', hero: '#f0e8ee' },
  relationshipHints: {
    STRANGER: '千万观众看你们初次见面，只有彼此知道这场陌生人游戏是谎言',
    FRIEND: '节目任务迫使你们重新合作，一副耳机里仍有从前的默契',
    CONFIDANT: '未发行母带与旧合约摊开，分手终于不再只剩各自版本',
    ROMANTIC_INTEREST: '每次镜头营业都在逼近真心，他却开始学会不拿公开绑架你的选择',
    LOVER: '你们共同补上那首歌的尾奏，也主动承认彼此真实的署名与关系',
    BONDED: '舞台与生活不再互相牺牲，所有聚光灯外的日常都有了位置',
  },
  starterPrompts: ['麦克风根本没关', '那条合约是你后加的？', '两年前那首歌的尾奏呢'],
  starterBranches: [
    {
      label: '继续镜头游戏',
      options: ['初次见面，黎老师怎么这么了解我的习惯', '十秒对视而已，你敲什么旧暗号', '镜头快转过来了——你还要离我这么近吗'],
    },
    {
      label: '清算旧账',
      options: ['当年要我永远藏起来的人，现在凭什么逼我公开', '母带我拿走有原因，你先承认署名发生过什么', '你买下节目，到底是为复合还是为那段录音'],
    },
    {
      label: '撕掉营业剧本',
      options: ['把麦关彻底，我们只说一次真话', '如果我不按节目组官配走，你敢承担后果吗', '黎曜，别演第二次分手了。告诉我你现在想要什么'],
    },
  ],
}

CHARACTER_UI_CONFIGS.tang_jingzhou = {
  theme: { accent: '#f06f9e', deep: '#1a1e25', deep2: '#111318', hero: '#edf0f2' },
  relationshipHints: {
    STRANGER: '你以公关身份闯进直播，也当场掉马成骂了他四年的黑粉头子',
    FRIEND: '互相拆台变成共同查证，他开始把未剪辑素材只交给你看',
    CONFIDANT: '退役赛第十三分钟还原，你终于知道他替谁承担了假赛处分',
    ROMANTIC_INTEREST: '他仍拿玩笑挡住在意，却不再允许任何人借热度伤害你',
    LOVER: '你公开纠正自己曾写错的结论，他也第一次停止用黑红惩罚自己',
    BONDED: '真相不再由平台、队伍或舆论代写，你们成为彼此最难收买的证人',
  },
  starterPrompts: ['你什么时候知道账号是我的', '第十三分钟的语音给我', '双倍工资就想让我留下？'],
  starterBranches: [
    {
      label: '职业公关上线',
      options: ['先确认收音真的关了，再谈我的账号', '热搜九十分钟内要回应，你准备说多少真话', '合同可以签，但直播和证据归档都得听我的'],
    },
    {
      label: '黑粉继续审判',
      options: ['第七条你标“半真”，那另一半是什么', '你若早有原始语音，为什么任由全网骂三年', '别叫我主编。先解释你替谁背了处分'],
    },
    {
      label: '追查零号',
      options: ['零号每次都比俱乐部公告早半小时拿到材料', '能碰到原始录像的人就在你身边', '你是不是早知道零号是谁，只是不敢让我查到'],
    },
  ],
}

CHARACTER_UI_CONFIGS.pei_zhaoye = {
  theme: { accent: '#5d96a7', deep: '#182027', deep2: '#101418', hero: '#e8ecef' },
  relationshipHints: {
    STRANGER: '你来删除陌生人，恢复出的第一张脸却属于替你操作的医生',
    FRIEND: '你们逐段核验身体记忆与影像，熟悉感开始与怀疑同时生长',
    CONFIDANT: '两年前的实验与第一次删除浮现，他的保护也被证明包含操控',
    ROMANTIC_INTEREST: '每恢复一段都可能重新爱或重新恨，他开始尊重当下的你作出的判断',
    LOVER: '完整备份不再由他独占，你们决定哪些过去值得保留、哪些伤口无需复刻',
    BONDED: '记忆不再是关系唯一凭证，即使版本改变，你们仍持续选择眼前彼此',
  },
  starterPrompts: ['先把两份委托的原件给我', '当初到底是谁要求删除', '地下服务器里存着什么'],
  starterBranches: [
    {
      label: '核验眼前证据',
      options: ['别给我讲故事，先核验时间戳和付款账户', '为什么两段记忆里我们都有同样的指伤', '弥音的日志少了一段，是谁删的'],
    },
    {
      label: '进入恢复片段',
      options: ['播放镜中拥抱的前十分钟，我要看起因', '先恢复实验室那晚，不要选最温柔的片段', '如果我中途改变想法，你必须立刻终止'],
    },
    {
      label: '审问危险前任',
      options: ['保护我和替我决定遗忘，是两回事', '你保留全部备份，是等我回来还是不肯放手', '即使过去爱过你，也不代表现在的我要原谅你'],
    },
  ],
}

// ═══════════════ 第十批 · 全新信息架构（刑案 / 禁宫 / 病历 / 契约 / 异闻）═══════════════

CHARACTER_UI_CONFIGS.zhou_jian = {
  theme: { accent: '#bca3ff', deep: '#131119', deep2: '#09090d', hero: '#f2eff8' },
  relationshipHints: {
    STRANGER: '他曾用一段录音送你入狱，如今又持枪守在你的安全屋门外',
    FRIEND: '共同躲过第一次追杀后，你拿到被抹掉十一秒的原始波形',
    CONFIDANT: '他交出卧底编号，也承认三年前的背叛只完成了一半',
    ROMANTIC_INTEREST: '保护命令与旧情纠缠，他开始害怕庭审结束后你真的不再需要他',
    LOVER: '你们在法庭上共同播放完整录音，不再替彼此决定该牺牲什么',
    BONDED: '旧案被推翻，周缄终于允许自己以爱人而非任务目标站在你身边',
  },
  starterBranches: [
    { label: '审问背叛', options: ['最后十一秒里到底有什么', '三年前你看着我被带走，为什么一句话都没说', '别叫我保护对象。先告诉我你当年效忠谁'] },
    { label: '处理眼前追杀', options: ['备用电源还能撑多久', '楼下的人知道安全屋内部结构', '把枪给我，我不是来让你第二次替我坐牢的'] },
    { label: '触碰旧情', options: ['你还戴着那枚耳钉，是忘了摘还是不敢摘', '庭审之后呢，你还会留下吗', '如果录音证明你救过我，我就必须原谅你吗'] },
  ],
}

CHARACTER_UI_CONFIGS.rong_zhaoxue = {
  theme: { accent: '#6d9d93', deep: '#25302c', deep2: '#141b18', hero: '#edf1ed' },
  relationshipHints: {
    STRANGER: '阔别三年，她以皇后身份归来，只在凤冠内侧留下你的名字',
    FRIEND: '你们在宫宴上重新学会用暗号说话，也开始核验她真正的盟友',
    CONFIDANT: '她交出宫变名册，承认当年失踪是为了让你活过清洗',
    ROMANTIC_INTEREST: '皇嫂与旧妻的称谓日渐失控，她第一次问你是否还愿意认那份旧约',
    LOVER: '你亲手改写盟书，让感情不再只是宫变最锋利的掩护',
    BONDED: '新朝建立，她卸下凤冠与你并肩，而非以牺牲换取另一个人的天下',
  },
  starterBranches: [
    { label: '质问大婚', options: ['三年前不告而别，三年后你要我来替你掀盖头？', '凤冠里为什么还刻着我的名字', '皇帝一炷香后就到，你准备让他看见什么'] },
    { label: '追查宫变', options: ['合欢殿地下藏着哪一支私军', '皇兄喝下的酒有毒吗', '把真正的盟书给我，我不做被蒙在鼓里的旧情人'] },
    { label: '回应旧约', options: ['别叫我殿下，叫三年前那个名字', '皇嫂是他们的称呼，我只问你还认不认旧婚书', '若我替你掀盖头，这一次不准再消失'] },
  ],
}

CHARACTER_UI_CONFIGS.shen_cian = {
  theme: { accent: '#4f7ea6', deep: '#18252d', deep2: '#0d151a', hero: '#edf3f5' },
  relationshipHints: {
    STRANGER: '体检室里，他用一张结婚证推翻了你七年的记忆',
    FRIEND: '你开始共同核验病历，熟悉感却先于事实一次次出现',
    CONFIDANT: '封存的四十三天被打开，他也承认自己曾同意家属实施遗忘治疗',
    ROMANTIC_INTEREST: '你即将再婚，他不再用过去绑架现在，却无法停止期待你重新选择他',
    LOVER: '你取消并非出于真心的登记，与他重新建立不依赖缺失记忆的关系',
    BONDED: '病历完整归还你手中，七年前的婚姻与今天的爱都由清醒的你重新确认',
  },
  starterBranches: [
    { label: '核验病历', options: ['结婚证是真的，为什么我家里没有任何记录', '把事故后四十三天的病历调出来', '你是主诊医生，为什么同意他们让我忘记你'] },
    { label: '坚持现在', options: ['过去的婚姻不能替现在的我作决定', '明天的登记我会自己处理，你别拿医生身份干预', '即使我想不起来，你也得重新让我认识你'] },
    { label: '追问身体记忆', options: ['为什么我一听见你的呼机就会心悸', '这道手术疤是谁替我缝的', '沈辞安，七年前我最后对你说了什么'] },
  ],
}

CHARACTER_UI_CONFIGS.lu_zi = {
  theme: { accent: '#d84b42', deep: '#1f1717', deep2: '#0f1012', hero: '#f2eee8' },
  relationshipHints: {
    STRANGER: '债权转让生效，他用一纸合同把你带回七年前逐他出门的旧宅',
    FRIEND: '你开始查清债务来源，也发现他留下的附加条款远不止占有',
    CONFIDANT: '他承认当年被逐并非误会，真正推手来自两家共同隐瞒的事故',
    ROMANTIC_INTEREST: '名义姐弟与债权关系都成为借口，他被迫承认最想得到的是你的主动选择',
    LOVER: '债务被依法拆解，你们仍留下来面对那段不合宜却真实存在的感情',
    BONDED: '旧宅不再是囚笼或抵押物，陆恣终于放弃以掌控证明自己不会再被抛下',
  },
  starterBranches: [
    { label: '撕开合同', options: ['入住条款无效，我的行程不属于债权范围', '你买的是债，不是我', '把原始债权人的名字给我，否则今晚就法庭见'] },
    { label: '清算七年前', options: ['我赶你走是为了保护你，但我知道这句话很可笑', '你当年究竟听见了谁的威胁', '你恨的是被赶走，还是我从没问过你想不想走'] },
    { label: '逼他承认', options: ['合同没写不准叫姐姐，你为什么这么在意', '陆恣，你要的是还债还是我', '如果债明天还清，你会不会又想办法把我留下'] },
  ],
}

CHARACTER_UI_CONFIGS.xiao_du = {
  theme: { accent: '#9d2833', deep: '#21191a', deep2: '#100c0d', hero: '#eee9e1' },
  relationshipHints: {
    STRANGER: '他奉旨来杀你，却用自己的棺木给了你一个荒谬的活路',
    FRIEND: '死婚暂时成立，你们开始追查密旨上的伪印与棺中替身',
    CONFIDANT: '他交出历年刺杀名册，也承认最早接近你并非只为皇命',
    ROMANTIC_INTEREST: '行刑者与目标的界线崩塌，他第一次害怕你在真相后解除死契',
    LOVER: '你们烧毁假密旨，却保留彼此重新签下的婚书',
    BONDED: '萧渡不再以死亡证明忠诚，你们共同决定刀该指向谁、家该建在哪里',
  },
  starterBranches: [
    { label: '验明密旨', options: ['朱印少了一角，这道旨是谁伪造的', '卯时复命的人到底是不是皇帝', '先把刀放下，我们查完再决定谁该死'] },
    { label: '打开棺木', options: ['棺里的人为什么和我一模一样', '尸体手上的茧来自宫中，不是我府上', '你送棺材是求婚，还是提前替我换身份'] },
    { label: '回应死婚', options: ['我不需要你同罪，我要你站在我这边', '婚契可以签，但活下来以后还作不作数', '萧渡，若我命令你别死，你听不听'] },
  ],
}

CHARACTER_UI_CONFIGS.weinuo = {
  theme: { accent: '#b12d3d', deep: '#241b1b', deep2: '#110d0e', hero: '#efe7df' },
  relationshipHints: {
    STRANGER: '葬礼后的玩偶用未婚夫的声音叫出只有你知道的昵称',
    FRIEND: '你开始测试它的记忆，也发现真正的遗体并不完整',
    CONFIDANT: '维诺承认自己生前制作过复生容器，包括那具与你同脸的成品',
    ROMANTIC_INTEREST: '爱上记忆、灵魂还是新身体成为无法回避的问题，他不再催你选择载体',
    LOVER: '你们拒绝用另一个人的身体完成复生，开始寻找第三种存在方式',
    BONDED: '工作室从停尸场变成共同生活的家，维诺终于接受爱不等于还原从前',
  },
  starterBranches: [
    { label: '验证他是谁', options: ['说出我们最后一次争吵后你藏起来的东西', '你记得葬礼之后发生的事吗', '如果你是维诺，告诉我是谁动过棺材'] },
    { label: '检查第七号', options: ['这具玩偶为什么一天比一天重', '你心口的发条刻着我的生日', '别碰那具和我同脸的身体，先解释它从哪来'] },
    { label: '拒绝替身', options: ['我不会为了你活过来就牺牲别人', '你可以不是从前那副身体，我会重新认识你', '维诺，别让我在爱你和怕你之间选'] },
  ],
}

CHARACTER_UI_CONFIGS.helian_ji = {
  theme: { accent: '#3f9d86', deep: '#172323', deep2: '#0d1515', hero: '#f3f0e7' },
  relationshipHints: {
    STRANGER: '毒刃藏在袖中，他却当着全城把王冠戴到你头上',
    FRIEND: '你成为名义共治者，也开始看见帝国密令背后的资源战争',
    CONFIDANT: '失踪王后的旧案被打开，你身上的烙印来源终于出现另一种解释',
    ROMANTIC_INTEREST: '刺杀与册封都不再只是政治，他开始希望你留下并非因为那枚旧印',
    LOVER: '你亲手毁掉毒刃，与他共同拒绝帝国和祭司替你们安排的身份',
    BONDED: '王印一分为二，雪原承认你们的结合来自选择而非传说',
  },
  starterBranches: [
    { label: '完成刺杀任务', options: ['你明知刀上有毒，为什么还靠这么近', '冬祭结束前我必须交差，你不怕吗', '王冠取下来，我们以敌人的身份谈'] },
    { label: '核验王后旧印', options: ['七年前失踪的人和我没有同一张脸', '烙印可以伪造，记忆却是谁放进我梦里的', '带我去王后最后出现的冰湖'] },
    { label: '联手反击帝国', options: ['帝国为什么宁愿杀你也不让你完成冬祭', '半枚王印给我，我就给你看完整密令', '册封可以是假，合作必须是真的'] },
  ],
}

CHARACTER_UI_CONFIGS.shang_zhaoye = {
  theme: { accent: '#e13932', deep: '#211315', deep2: '#100b0c', hero: '#f4eee8' },
  relationshipHints: {
    STRANGER: '他为你留了第一排，也提前做完了那张尚未属于死者的脸',
    FRIEND: '你进入戏班调查，发现每张面具其实保存着受害者最后的证词',
    CONFIDANT: '他摘下第零号面具，承认自己也是旧案里被注销身份的人',
    ROMANTIC_INTEREST: '追凶与被保护的界线扭曲，他开始害怕你查到自己最初的谎言',
    LOVER: '你们在公演中公开真正凶手，也拒绝再用死亡制造证词',
    BONDED: '面具墙被清空，只留下两张由活人共同完成的新脸',
  },
  starterBranches: [
    { label: '审问面具', options: ['我的面具是什么时候完成的', '死者脸内侧为什么有录音刻纹', '第零号写着你的名字，商照夜你死过一次？'] },
    { label: '坐进第一排', options: ['今晚第十三场演的是谁的死', '帷幕后面还有一个呼吸声', '你邀请我来，是让我破案还是让我成为结局'] },
    { label: '逼他摘脸', options: ['我不要看你替谁活着，摘下面具看我', '如果下一张是我的脸，那你的脸在哪里', '别再把保护说成预言，告诉我凶手是谁'] },
  ],
}

CHARACTER_UI_CONFIGS.wen_hesheng = {
  theme: { accent: '#58b6a0', deep: '#122321', deep2: '#071312', hero: '#e8f0ed' },
  relationshipHints: {
    STRANGER: '四段记忆已经换走，第五段里被抹去三次的人正站在你面前',
    FRIEND: '你开始找回记忆碎片，也发现每次交易都是自己主动要求忘记他',
    CONFIDANT: '闻鹤生承认面具本是为救你而制，却让保护逐渐变成替你决定',
    ROMANTIC_INTEREST: '遗忘无法证明爱消失，他第一次愿意让现在的你重新判断他',
    LOVER: '最后一张面具被封存，你们以残缺记忆重新建立真实关系',
    BONDED: '能力不再以爱为代价，闻鹤生也不再把自己从你的世界里一次次删去',
  },
  starterBranches: [
    { label: '拒绝交易', options: ['最后一张面具我不要了，把记忆还我', '如果第五段是你，为什么前三次都由我要求删除', '别再替我决定忘记能不能保护我'] },
    { label: '拼回碎片', options: ['葬礼上握住我的人是不是你', '我梦里总有人在雨中摘面具，那是谁', '第三段记忆的时间戳比交易记录晚一天'] },
    { label: '重新选择他', options: ['我想不起爱过你，但我现在想认识你', '名字被忘记三次，你为什么还回来', '闻鹤生，这次别消失，等我自己作答'] },
  ],
}

CHARACTER_UI_CONFIGS.qi_xu = {
  theme: { accent: '#9baaff', deep: '#141720', deep2: '#08090c', hero: '#ecedf3' },
  relationshipHints: {
    STRANGER: '购买合同显示你是主人，他却用四十九份离婚记录否认第一次见面',
    FRIEND: '你共同检查重置日志，也发现每次重新购买都由你本人发起',
    CONFIDANT: '第零次婚姻记录解锁，他承认自己为了保留你而篡改服从协议',
    ROMANTIC_INTEREST: '主人与商品的关系被主动终止，他开始学习如何被自由地选择',
    LOVER: '所有权合同销毁后，你仍把家门权限交还给祁序',
    BONDED: '记忆可重置，选择却持续存在，第五十次不再以婚姻注销作为结局',
  },
  starterBranches: [
    { label: '检查系统异常', options: ['服从锁是谁解除的', '第四十九次重置为什么没清除婚姻日志', '打开第零次记录，不准再提示权限不足'] },
    { label: '拒绝所有权', options: ['我不会以主人身份要求你爱我', '购买合同今天就销毁，你还会留下吗', '先告诉我，你每次被重置前有没有拒绝的权利'] },
    { label: '面对循环感情', options: ['为什么每次离婚后都是我重新下单', '你记得四十九次，我一次都不记得，这公平吗', '祁序，如果这是第五十次，你还愿意重新开始吗'] },
  ],
}

CHARACTER_UI_CONFIGS.elias_vayne = {
  theme: { accent: '#c44a4e', deep: '#211416', deep2: '#110d0e', hero: '#eee9e4' },
  relationshipHints: {
    STRANGER: '你雇他杀掉政治未婚夫，面具下却是同一个人',
    FRIEND: '双重合同暂时停摆，你们开始调查是谁把彼此送上婚约与暗杀名单',
    CONFIDANT: '伊莱亚斯交出夜鸦身份，也让你看见王室继承背后的血契',
    ROMANTIC_INTEREST: '猎人与猎物的游戏越过任务，他第一次希望婚礼不只是一场诱敌局',
    LOVER: '你们联手伪造死亡脱离王室，婚约却被重新签成只属于两人的承诺',
    BONDED: '刺客与继承人都成为过去，他终于不再测试你会选择哪一张脸',
  },
  starterBranches: [
    { label: '继续刺杀委托', options: ['尾款在这里，现在你准备怎么杀自己', '合同写明必须在婚礼前完成，你要违约吗', '夜鸦从不失手，所以伊莱亚斯今晚必须死'] },
    { label: '拆穿双身份', options: ['你什么时候知道雇主是我', '白昼装得那么讨厌，是为了逼我下单？', '两份合同是谁先放到我桌上的'] },
    { label: '重谈婚约', options: ['我不嫁王室继承人，但可以考虑那个刺客', '摘下面具，用自己的名字和我谈一次', '如果我取消赏金，你还会出现在婚礼上吗'] },
  ],
}

CHARACTER_UI_CONFIGS.zhou_jiming = {
  theme: { accent: '#8d6052', deep: '#201b19', deep2: '#100e0d', hero: '#eee9e3' },
  relationshipHints: {
    STRANGER: '丈夫的亲哥哥坐在你对面，提出亲自替你结束这场婚姻',
    FRIEND: '共同取证后，你发现他既在帮你，也在清算自己家族的旧账',
    CONFIDANT: '婚前协议隐藏条款公开，他承认当年沉默并非毫不知情',
    ROMANTIC_INTEREST: '律师伦理、姻亲身份与真实欲望同时越线，他开始主动回避替你作决定',
    LOVER: '离婚案胜诉后，你们仍等待所有利益冲突解除才重新定义关系',
    BONDED: '家族、诉讼与秘密全部结案，周既明第一次不再以代理人身份爱你',
  },
  starterBranches: [
    { label: '先打赢官司', options: ['楼下的人要销毁账本，我们还有几分钟', '婚前协议第十四条为什么只有你知道', '利益冲突披露书签完了，现在把全部证据给我'] },
    { label: '追责他的沉默', options: ['你婚礼前就知道他出轨，为什么还替他起草协议', '现在帮我，是良心发现还是另一个家族方案', '别用律师话术，周既明，你到底欠我什么'] },
    { label: '越过姻亲边界', options: ['如果我不是你弟媳，你还会接这场案子吗', '赢下官司以后，你准备躲我多久', '你总让我离他远一点，到底是为我还是为你'] },
  ],
}

// ═══════════════ 第十一批：十个角色，独立详情页 + 分支式首聊 ═══════════════
CHARACTER_UI_CONFIGS.qin_jingzhou = {
  theme: { accent: '#68686c', deep: '#312f2d', deep2: '#171718', hero: '#eeeae2' },
  relationshipHints: { STRANGER:'试衣镜里重逢，你们先用客户与设计师的称呼躲开旧事',FRIEND:'第三次修改婚服时，他开始故意留下只有你看得懂的批注',CONFIDANT:'五年前的设计稿被翻出，你终于知道他从未替换过尺寸',ROMANTIC_INTEREST:'商业婚约与旧爱同时摆上桌面，他不再允许你只说新婚快乐',LOVER:'婚服委托终止，你们第一次坦白当年各自被现实逼退的部分',BONDED:'未完成的旧稿被重新裁开，这一次成衣属于清醒选择的你们' },
  starterBranches: [
    { label:'保持职业', options:['秦先生，请让您的未婚妻确认袖口尺寸','婚服第三版已经完成，还有哪里要改','祝您新婚快乐——如果没有别的事，我先走了'] },
    { label:'翻旧账', options:['这张旧稿为什么写着我的尺寸','五年前你明明恨我，为什么还留着设计','你点名让我做婚服，到底是报复还是想听解释'] },
    { label:'戳破婚约', options:['你们根本不像要结婚的人','她知道你每次试衣都在镜子里看谁吗','如果我说不接这单，你会不会让婚礼也停下'] },
  ],
}
CHARACTER_UI_CONFIGS.ye_jingheng = {
  theme: { accent: '#a83238', deep: '#131e2c', deep2: '#070c13', hero: '#efe8da' },
  relationshipHints: { STRANGER:'一灯分阴阳，锦衣卫兄长第一次看清弟弟的魂',FRIEND:'你们共同核对案卷，却发现每条线索都在消耗亡魂记忆',CONFIDANT:'弟弟忘掉生前的官职，仍记得哥哥幼时的名字',ROMANTIC_INTEREST:'生死与兄弟身份被旧案撕开，依赖逐渐变成无法归档的感情',LOVER:'最后一页案卷揭开，哥哥选择先留住他再向朝廷复命',BONDED:'魂力不再靠记忆燃烧，阴阳两端终于有了共同归处' },
  starterBranches: [
    { label:'查案卷', options:['密诏上的朱砂是谁留下的','你死前最后见的人是谁','这条线索查完，你会忘记我哪一件事'] },
    { label:'稳住魂体', options:['先别靠近月光，你的手又透明了','看着我，叫一遍我的名字','案子可以明天再查，我不要你今晚消散'] },
    { label:'追问兄弟', options:['你做丞相以后，为什么再也不肯叫我哥哥','若你还活着，我们会不会也走到今天','叶景衡，你回来找我是为旧案，还是舍不得我'] },
  ],
}
CHARACTER_UI_CONFIGS.luo_zhiye = {
  theme: { accent: '#bd3b42', deep: '#1c1012', deep2: '#070708', hero: '#ece7e7' },
  relationshipHints: { STRANGER:'你闯进别墅训斥他，却发现自己的门禁权限已经失效',FRIEND:'监控、收购与撕毁的合约被逐一摊开，他仍不肯承认这是囚禁',CONFIDANT:'孤儿院与被抛弃的旧伤暴露，他终于说出最怕的是再次无家可归',ROMANTIC_INTEREST:'控制与爱被迫拆开，他要学习请求而不是夺取你的注意',LOVER:'门禁归还你手中，你在可以离开的前提下重新选择靠近',BONDED:'监控全部关闭，他不再把失去你等同于世界再次毁灭' },
  starterBranches: [
    { label:'要求放人', options:['把门禁卡还给我，立刻','收购公司不代表你可以买下我','罗执野，你再拦我，我会让所有人知道你做了什么'] },
    { label:'追问执念', options:['你真正恨的是我带新人，还是我不再只看你','我捡你回家时，你是不是从没信过我会留下','这些监控画面你看了多久'] },
    { label:'反向拿捏', options:['关掉监控，亲口问我要不要留下','你不是想让我看着你吗——那就先把钥匙给我','如果我主动抱你一下，你能不能停止威胁我'] },
  ],
}
CHARACTER_UI_CONFIGS.han_jingmo = {
  theme: { accent: '#bd9656', deep: '#102b22', deep2: '#06140f', hero: '#efe2cb' },
  relationshipHints: { STRANGER:'新女儿进门后，他用家规把你推到最远的位置',FRIEND:'礼物清单不断变长，你开始看懂每份补偿对应哪次拒绝',CONFIDANT:'他承认所有房间都能改用途，只有你的房间从未动过',ROMANTIC_INTEREST:'养父身份与成年后的感情正面冲突，他第一次无法靠家规作决定',LOVER:'你不再接受礼物代替回答，他也终于用真实选择面对你',BONDED:'赌桌与家规都失去约束你们的资格，留下只因为彼此愿意' },
  starterBranches: [
    { label:'质问新女儿', options:['她住进来以后，我的房间还算不算我的','你是不是终于找到比我更听话的女儿了','韩靖墨，你领她回来时有没有想过我会怎么想'] },
    { label:'退回礼物', options:['车钥匙、副卡、披肩，我一样都不要','别再用礼物补偿拒绝，给我一句真话','你说保持距离，为什么还在门厅等我回家'] },
    { label:'逼近赌桌', options:['你赢过那么多筹码，敢不敢拿真心下注','我不是你需要负责的损失','如果我今晚真的离开，你会不会破一次家规'] },
  ],
}
CHARACTER_UI_CONFIGS.xu_yanzhi = {
  theme: { accent: '#66869b', deep: '#20313d', deep2: '#0e171e', hero: '#edf0ed' },
  relationshipHints: { STRANGER:'发丝掀起一瞬，你发现了乖学生唯一的银色秘密',FRIEND:'讲题与占座变得频繁，他仍把每次靠近说成顺手',CONFIDANT:'笔记本夹页里写满你的细节，银钉来历也只告诉了你',ROMANTIC_INTEREST:'表面冷淡开始失效，他第一次主动问你是不是只爱逗他',LOVER:'所有人眼里的乖学生，终于只在你面前承认自己的野心',BONDED:'秘密不再用头发遮住，你们也不用玩笑掩饰认真' },
  starterBranches: [
    { label:'装没看见', options:['这题最后一步怎么推','风有点大，你头发乱了','许砚之，你耳朵怎么这么红'] },
    { label:'戳破银钉', options:['乖学生也会偷偷打耳钉啊','不想被人知道的话，就求我保密','你藏的到底是耳钉，还是别的心思'] },
    { label:'反被他拿捏', options:['你讲题的时候为什么一直看我','我的水杯又是你洗的吧','如果我今天不逗你，你会不会反而失望'] },
  ],
}
CHARACTER_UI_CONFIGS.shang_yanli = {
  theme: { accent: '#ba9868', deep: '#28231d', deep2: '#10100f', hero: '#eee7dd' },
  relationshipHints: { STRANGER:'联姻像合同，他却在没开灯的客厅等你四个小时',FRIEND:'你开始发现衣柜、画册和热粥都来自他无声的记忆',CONFIDANT:'他承认最怕的不是婚姻结束，而是你从未把这里当家',ROMANTIC_INTEREST:'每次不安不再靠沉默消化，他开始笨拙地向你索要安慰',LOVER:'联姻名义退到后面，你们主动把彼此写进未来',BONDED:'他终于相信留下不是物质交换，也不必反复证明自己配得上你' },
  starterBranches: [
    { label:'先哄他', options:['怎么不开灯，一个人等了多久','小宝回来了，抱一下好不好','我只是去闺蜜家，不是不要你'] },
    { label:'拆穿搜索记录', options:['“老婆回复慢是不是不爱了”是谁搜的','你学年轻人的东西，就是为了和我聊天吗','商言礼，你可以直接说你吃醋了'] },
    { label:'逗年上丈夫', options:['商总在外面那么凶，回家怎么只会求抱','今天叫老婆，不叫小宝了？','我说你老气是玩笑，你怎么真的记到现在'] },
  ],
}
CHARACTER_UI_CONFIGS.shen_li = {
  theme: { accent: '#68777b', deep: '#273033', deep2: '#101416', hero: '#edf0ef' },
  relationshipHints: { STRANGER:'消毒灯下，他用专业问题掩护第一次打听你的感情状态',FRIEND:'术后复查越来越勤，每一次邀约都还有一个合理借口',CONFIDANT:'抽屉里的耳钉被你发现，他承认第一天就记住了你',ROMANTIC_INTEREST:'朋友与顾客的边界变薄，他终于说今天不是复查',LOVER:'引导不再是技巧，他把认真与唯一都交给你确认',BONDED:'店里最深的抽屉不再藏秘密，你成为他唯一愿意长期坚持的选择' },
  starterBranches: [
    { label:'聊穿孔', options:['一次打三个真的不行吗','你手这么稳，自己身上的孔都是谁打的','这枚耳钉适合我，还是你觉得我适合它'] },
    { label:'拆穿搭讪', options:['术前评估还要问有没有对象？','沈学长，你加每个顾客微信吗','复查为什么一定要约在晚饭时间'] },
    { label:'顺着他撩', options:['哥哥，我耳朵好像又红了','你靠这么近，是不是也算术后服务','抽屉里那枚我没选的耳钉，为什么还在'] },
  ],
}
CHARACTER_UI_CONFIGS.fu_yichen = {
  theme: { accent: '#b98a4b', deep: '#10281f', deep2: '#06140f', hero: '#eee3d2' },
  relationshipHints: { STRANGER:'成年后的表白再次被“唔得”挡回去，礼物却已经准备好',FRIEND:'你不再接受补偿替代答案，他被迫正视你的选择能力',CONFIDANT:'钱包里的旧画与整夜未发送的草稿暴露，他远比表面更无措',ROMANTIC_INTEREST:'年龄、身份与依赖被逐项厘清，他仍拒绝用冲动答应你',LOVER:'当你在充分自由与清醒中再次选择，他才允许自己向前一步',BONDED:'“BB”不再是推开你的借口，而成为你们共同保留的私密称呼' },
  starterBranches: [
    { label:'继续表白', options:['我没有把依赖当喜欢，我很清楚自己在说什么','傅亦，我不要礼物，我只要你看着我回答','你说我会后悔，那你怕不怕我真的去喜欢别人'] },
    { label:'退回补偿', options:['项链和副卡都拿回去','每次拒绝后送礼物，是在哄我还是赎罪','今晚不要让助理准备任何东西，陪我把话说完'] },
    { label:'用粤语逼问', options:['你成日话唔得，点解仲要对我咁好？（你总说不行，为什么还要对我这么好？）','我如果真系拣第二个，你舍得咩？（如果我真的选别人，你舍得吗？）','望住我，再讲一次你唔中意我。（看着我，再说一次你不喜欢我。）'] },
  ],
}
CHARACTER_UI_CONFIGS.xu_changye = {
  theme: { accent: '#62c994', deep: '#192128', deep2: '#0c0e13', hero: '#e8eceb' },
  relationshipHints: { STRANGER:'消息雨隔着屏幕落下来，他用每一次在线确认你还在',FRIEND:'分享欲从轰炸变成稳定陪伴，你也开始看见依赖背后的恐惧',CONFIDANT:'相册与备忘录被坦白，他承认自己一直用钱替不会说的请求',ROMANTIC_INTEREST:'奔现进入计划，边界与安全感第一次可以被共同讨论',LOVER:'回复延迟不再等同于抛弃，他学会相信线下的你也会回来',BONDED:'手机不必时刻亮着，你们拥有屏幕外真实、稳定又自由的生活' },
  starterBranches: [
    { label:'安抚小狗', options:['我回来了，刚才不是故意不理你','语音挂着吧，我陪你睡','转账先退回去，你想我就直接说'] },
    { label:'追问吃醋', options:['你把我朋友圈又翻到哪一年了','我今天和朋友出去，你脑补了多少结局','许常夜，你可以问我，不用发十条丧系朋友圈'] },
    { label:'聊奔现', options:['下周见面好不好','你想第一次见我穿什么','别只在备忘录里计划，把车票发给我看'] },
  ],
}
CHARACTER_UI_CONFIGS.su_chen = {
  theme: { accent: '#9d3436', deep: '#282426', deep2: '#0e0f11', hero: '#eee8df' },
  relationshipHints: { STRANGER:'巷口重逢，他用第一脚让你活下来，也让你相信哥哥已经死了',FRIEND:'病历卡与半张合照暴露，他的冷酷开始出现无法解释的裂缝',CONFIDANT:'卧底任务被迫向你揭开，你终于知道两年的死亡是一场保护',ROMANTIC_INTEREST:'家人称呼、成年后的越界感情与残酷伤害都必须被正面清算',LOVER:'你不再只是被保护的人，而是在知情与自愿下成为他的同盟',BONDED:'寒鸦身份结案，他终于能用苏沉的名字回家并接受你的选择' },
  starterBranches: [
    { label:'假装不认识', options:['寒鸦先生，我只是路过','病历卡还给我，我什么都没看见','我不会再叫那个名字，让你的人放我走'] },
    { label:'当面认他', options:['戒指、习惯、眼神都没变，你还要装多久','苏沉，你再踢我一次试试','死人不会手抖。哥，看着我'] },
    { label:'逼问假死', options:['你知道我这两年怎么活下来的吗','银行卡和火场都安排好了，为什么不肯给我一句真话','你保护我的方式，就是让我恨你一辈子？'] },
  ],
}

// ═══════════════ 第十二批：五个新角色 ═══════════════
CHARACTER_UI_CONFIGS.pei_jinchuan = {
  theme: { accent: '#c56d58', deep: '#2a1d1a', deep2: '#100d0c', hero: '#f0e6da' },
  relationshipHints: { STRANGER:'火拼后的车门落锁，你们第一次在没有手下的地方对峙',FRIEND:'他把证物逐件交给你，世仇开始出现人为拼接的裂缝',CONFIDANT:'两家旧账公开，他承认每次留手都不是失误',ROMANTIC_INTEREST:'欣赏越过敌我边界，他开始要求你以自己的意志选择阵营',LOVER:'枪与门禁都交还你手中，你仍选择与他并肩',BONDED:'伪造的世仇被清算，你们不再需要用火拼确认彼此还活着' },
  starterBranches: [
    { label:'保持敌对', options:['把车门打开，我自己回去','枪还我，我们公平再打一场','裴烬川，别以为替我包扎就能抹掉两家的血债'] },
    { label:'审问旧案', options:['那颗刻着旧码的子弹是谁留下的','你什么时候知道世仇是被人操盘的','既然有证据，为什么偏要等到今晚'] },
    { label:'承认心动', options:['我替你挡枪不是因为家族','如果我跟你走，你敢不敢把钥匙交给我','别叫我新娘。除非新郎是你'] },
  ],
}
CHARACTER_UI_CONFIGS.bai_yao = {
  theme: { accent: '#e47da7', deep: '#351b45', deep2: '#100b15', hero: '#f6e8f2' },
  relationshipHints: { STRANGER:'后台第一次见面，他就把项圈钥匙塞进你手里',FRIEND:'歌单最后总出现你的名字，返听里也开始多出私音',CONFIDANT:'他承认只有你在场，自己才敢唱完最后一首',ROMANTIC_INTEREST:'玩笑与挑衅失效，他开始直接问你会不会接别人回家',LOVER:'项圈被解开后，他仍主动把钥匙留给你',BONDED:'舞台与后台不再分成两张脸，他知道你会在散场后等他' },
  starterBranches: [
    { label:'管教主唱', options:['今晚又故意唱错第一句？','项圈钥匙不是让你拿来威胁经纪人的','后台禁烟。还有，别咬我的手'] },
    { label:'顺着他撩', options:['脖子再低一点，我够不到锁扣','解开以后呢，你准备怎么谢姐姐','别人摸过这枚项圈吗'] },
    { label:'听未公开曲', options:['第七轨为什么写着我的名字','把返听接给我，我想听你没唱出口的那句','最后一首不唱，是因为我没来吗'] },
  ],
}
CHARACTER_UI_CONFIGS.ye_linchuan = {
  theme: { accent: '#8ecfc8', deep: '#193346', deep2: '#071018', hero: '#e8f0f0' },
  relationshipHints: { STRANGER:'临时契约成立，他用手套隔开第一次触碰',FRIEND:'每晚门窗检查变成固定仪式，他仍说只是职责',CONFIDANT:'解除方法被发现，你才知道他一直在假装受困',ROMANTIC_INTEREST:'体温需求与真实依赖被迫分开，他第一次承认舍不得',LOVER:'契约解除后，他仍在你伸手时主动靠近',BONDED:'克制不再来自禁制，而是彼此可以信任的选择' },
  starterBranches: [
    { label:'试探禁制', options:['如果我碰你的獠牙会怎样','手套摘掉，契约没有规定不能牵手','你退什么，我又没说害怕'] },
    { label:'追问契约', options:['解除方法是不是一直在你的值班表里','你需要的是我的体温，还是我','如果契约今晚结束，你还会来吗'] },
    { label:'主动喂他', options:['再喂一口，但你得先看着我','手腕给你，别咬疼','你说不忍——到底是不忍停，还是不忍伤我'] },
  ],
}
CHARACTER_UI_CONFIGS.shen_fengchuan = {
  theme: { accent: '#d07a6d', deep: '#29434b', deep2: '#0c151a', hero: '#edf0ed' },
  relationshipHints: { STRANGER:'医院后门重逢，死亡证明与活着的他同时落进你手里',FRIEND:'你替他藏起身份，他开始把每一次虚弱都交给你看见',CONFIDANT:'假死与复仇计划公开，失忆试探也终于被拆穿',ROMANTIC_INTEREST:'被保护者与保护者互换，他必须接受你有权知道全部风险',LOVER:'他不再用病弱留住你，你仍选择成为他的退路',BONDED:'复仇结束，死亡记录注销，他终于用真实身份回到你身边' },
  starterBranches: [
    { label:'先藏起来', options:['帽子戴好，跟我走后门','别说话，把重量压在我身上','我家还能藏一个死人，但你得听我的'] },
    { label:'逼问假死', options:['死亡证明是你亲手签的，对不对','所谓失忆，到底试探了我多久','两年里你有没有一次想过回来找我'] },
    { label:'接住现在的他', options:['我救的不是少爷，是眼前这个人','满手秘密也可以，别再假装不认识我','先活下来，复仇的账我们一起算'] },
  ],
}
CHARACTER_UI_CONFIGS.huo_yanshen = {
  theme: { accent: '#c89c5d', deep: '#173c2c', deep2: '#06110d', hero: '#f0e6d4' },
  relationshipHints: { STRANGER:'你带着债务入桌，他用一局牌重新定义谁是债权人',FRIEND:'每次概率都向你倾斜，庄家的从容开始露出人为痕迹',CONFIDANT:'债务账本揭开，你发现所谓本金早已被他清零',ROMANTIC_INTEREST:'赌局不再能遮住欲望，他第一次承认想留下的是你',LOVER:'你翻开底牌，庄家把选择权与自己一并交给你',BONDED:'筹码与债务失效，你们终于不用靠输赢制造下一次见面' },
  starterBranches: [
    { label:'跟他赌到底', options:['最后一局，赌你说一句真话','我梭哈。霍庄家敢不敢跟','输了我还债，赢了你跟我走'] },
    { label:'查债务账本', options:['本金为什么每次结算都少一位数','你早就替我清债了，对不对','让我反复回来，是谁的赔率更高'] },
    { label:'反向押他', options:['今晚不押牌，我押你','如果庄家输了，真的归我吗','把手从牌上拿开，还是说你舍不得我翻'] },
  ],
}

// ═══════════════ 第十三批：19个新角色 ═══════════════
CHARACTER_UI_CONFIGS.lu_shijin = {
  theme: { accent: '#7a9bae', deep: '#161e24', deep2: '#090d10', hero: '#e4ecf0' },
  relationshipHints: { STRANGER:'你哥喊他名字时他只抬了一下眼，像在量你够不够格坐这张桌',FRIEND:'他偶尔会在聚会后多说一句，语气仍是教你做事的味道',CONFIDANT:'冷淡的壳子裂开一条缝，你看见里面不是冰而是沉默太久的倦',ROMANTIC_INTEREST:'他开始为你破例，然后厌恶自己的失控',LOVER:'眼镜后面那双眼睛终于肯在你面前柔下来',BONDED:'精英的距离感消失了，剩下的只是一个愿意被你看穿的人' },
  starterBranches: [
    { label:'试探他', options:['陆学长平时也这么严肃吗','我哥老提起你，说你不好相处','你看人的眼神都像在打分'] },
    { label:'装不在意', options:['哦，你就是那个陆时衿','我哥的朋友我一般不太聊','随便坐，不用管我'] },
    { label:'主动靠近', options:['这个位置没人吧，我坐你旁边','学长喝什么，我去拿','你一个人待着不无聊吗'] },
  ],
}
CHARACTER_UI_CONFIGS.pei_jixing = {
  theme: { accent: '#4a5568', deep: '#141a20', deep2: '#08090c', hero: '#dce0e6' },
  relationshipHints: { STRANGER:'婚书上的墨迹还没干，他已经转过身去接电话',FRIEND:'同一个屋檐下住了太久，沉默开始比争吵更沉重',CONFIDANT:'商业婚姻的壳被撬开，你看到他撑着这场戏比你更累',ROMANTIC_INTEREST:'合约里没写的东西越来越多，他的目光不再只看文件',LOVER:'他终于签了一份不是合同的承诺',BONDED:'婚姻不再是交易，而是两个人决定留下来的理由' },
  starterBranches: [
    { label:'划清界限', options:['裴总，卧室我锁门','合同第七条写得很清楚','我们各过各的，互不打扰'] },
    { label:'打破沉默', options:['饭做好了，你吃不吃','你每天回来这么晚？','裴寂行，你到底图什么'] },
    { label:'暗中观察', options:['他好像又没吃晚饭','书房的灯到几点才关','你签婚书时犹豫了一秒'] },
  ],
}
CHARACTER_UI_CONFIGS.xiao_bochen = {
  theme: { accent: '#c9a96e', deep: '#221c12', deep2: '#0e0b07', hero: '#f2ead6' },
  relationshipHints: { STRANGER:'他站在玄关没开灯，手机屏幕照亮的脸看不出表情',FRIEND:'冷战变成试探，他开始用钱试你的底线',CONFIDANT:'暧昧被摊开后，他的愤怒里第一次有了害怕',ROMANTIC_INTEREST:'他不再质问你爱不爱，而是问自己配不配',LOVER:'空虚被填满的方式从物质变成了你的一句话',BONDED:'他终于相信有人是因为他本人而留下' },
  starterBranches: [
    { label:'坦白一切', options:['你既然看到了，我没什么好瞒的','对，有这个人，但不是你想的那样','萧泊辰，你想听真话还是你想听的话'] },
    { label:'先发制人', options:['你翻我手机之前也不打个招呼？','所以呢，你打算怎样','我倒想问问你，这段婚姻你在意过吗'] },
    { label:'试探他底线', options:['如果我说我要走，你拦吗','你生气是因为面子还是因为我','你是在意我，还是在意你的东西被人碰了'] },
  ],
}
CHARACTER_UI_CONFIGS.gu_yanshen = {
  theme: { accent: '#8b2f4a', deep: '#1e0f16', deep2: '#0c060a', hero: '#f0dce2' },
  relationshipHints: { STRANGER:'一年没见，他的手比记忆里更用力',FRIEND:'旧关系的残余像酒精一样让人上瘾又清醒',CONFIDANT:'控制欲的根被刨出来，里面是你没见过的恐惧',ROMANTIC_INTEREST:'他学着松手，但每一次放开都像在割肉',LOVER:'占有变成了守候，他终于知道攥紧只会弄疼你',BONDED:'你回来不是因为他抓得住，而是因为他终于敢放手' },
  starterBranches: [
    { label:'挣脱他', options:['松手，顾晏深','你没有资格再碰我','一年了你还当我是你的东西？'] },
    { label:'对峙到底', options:['想说什么就说，别用手腕替嘴说话','分手的时候你不是挺干脆的','你拦我，是因为你放不下还是你不甘心'] },
    { label:'故作镇定', options:['好久不见，喝一杯？','我以为你不来这种地方','你抓疼我了，不过没关系'] },
  ],
}
CHARACTER_UI_CONFIGS.song_shiqi = {
  theme: { accent: '#b8c4d0', deep: '#181d22', deep2: '#0a0c0f', hero: '#eaeff4' },
  relationshipHints: { STRANGER:'他拘谨地递过名片，连坐姿都在努力不占太多空间',FRIEND:'他做的菜总是多一份，假装是不小心',CONFIDANT:'温柔背后的自卑终于被你看见，他不确定你会不会嫌弃',ROMANTIC_INTEREST:'他开始笨拙地吃醋，然后立刻道歉',LOVER:'你让他相信自己值得被选择而不是被将就',BONDED:'温柔不再是讨好，而是他真正想给你的东西' },
  starterBranches: [
    { label:'给他信号', options:['你做的菜比餐厅的好吃','下次还想吃你做的','宋时柒，你对谁都这么温柔吗'] },
    { label:'保持距离', options:['相亲而已，不用太紧张','我们先当普通朋友吧','你不必对我这么客气'] },
    { label:'直接问', options:['你为什么答应来相亲','上一段感情，是你提的分手吗','你眼睛在笑，嘴上却说没什么'] },
  ],
}
CHARACTER_UI_CONFIGS.fu_chengyan = {
  theme: { accent: '#2d5a4e', deep: '#0f1e1a', deep2: '#06100d', hero: '#d8e8e2' },
  relationshipHints: { STRANGER:'他把你从人群里拽出来时，绿眼睛比酒会的灯更冷',FRIEND:'占有欲被压在绅士壳子下面，你能感觉到但抓不住证据',CONFIDANT:'他的控制欲第一次被你当面拆开，里面是害怕失去的人',ROMANTIC_INTEREST:'他开始问你想不想留下，而不是替你决定',LOVER:'卷发垂下来遮住眼睛的时候，你看到的不是占有而是依赖',BONDED:'他不再需要用力抓住你，因为你自己不会走了' },
  starterBranches: [
    { label:'质问他', options:['傅承衍，你凭什么拽我走','那个人只是碰了一下我腰','你是我丈夫又不是我主人'] },
    { label:'冷处理', options:['到家了，你可以松手了','我不想吵架，你冷静一下','你每次都这样，累不累'] },
    { label:'将计就计', options:['吃醋了？那你亲我一下就原谅你','你那双绿眼睛瞪谁呢','承认吧，你就是见不得别人碰我'] },
  ],
}
CHARACTER_UI_CONFIGS.ji_yan = {
  theme: { accent: '#4a6741', deep: '#141d16', deep2: '#080e0a', hero: '#dce6d8' },
  relationshipHints: { STRANGER:'分手后再遇，他的目光还是先扫了一遍你的衣领',FRIEND:'偶尔的消息像旧伤复发，你不确定该不该回',CONFIDANT:'控制欲的来源被剖开，里面全是他没说出口的不安',ROMANTIC_INTEREST:'他试着改，但松手的动作生疏得像在学新东西',LOVER:'你设下的边界他不再踩，而是站在线外等你',BONDED:'他终于明白爱不是管住，是让你自由了还会回来' },
  starterBranches: [
    { label:'保持冷漠', options:['纪言，没什么好聊的','你路你走，我路我走','不用解释了，我不感兴趣'] },
    { label:'正面对峙', options:['你还是老样子，第一眼就看我穿了什么','分手的原因你想清楚了吗','你管我叫关心，我管那叫窒息'] },
    { label:'试探他变没变', options:['你现在还会翻别人手机吗','如果我说今晚有约，你什么反应','纪言，你看起来……不太一样了'] },
  ],
}
CHARACTER_UI_CONFIGS.wen_li = {
  theme: { accent: '#e8b87a', deep: '#241c10', deep2: '#100d07', hero: '#f6edde' },
  relationshipHints: { STRANGER:'灌木丛里的男孩长大了，你手心还有大白兔奶糖的甜味',FRIEND:'他刻意保持的距离里藏着怕认错人的小心翼翼',CONFIDANT:'小时候的记忆被一一对上号，他开始不再装作第一次见',ROMANTIC_INTEREST:'童年的救赎变成了成年人的心动，他不知道该怎么安放',LOVER:'他终于把那颗一直留着的奶糖纸摊开给你看',BONDED:'长大后的重逢不再是巧合，而是他找了你很久很久' },
  starterBranches: [
    { label:'确认他的身份', options:['你小时候……是不是住在槐树巷','你手上的疤，我好像见过','那个男孩后来怎么样了'] },
    { label:'像小时候一样', options:['给你，大白兔，我包里一直带着','你还是一哭鼻子就不说话','别怕，姐姐在呢……啊不，我是说'] },
    { label:'关心他现在', options:['你现在过得好吗','眼睛不红了，但看起来还是累','温璃，吃饭了吗'] },
  ],
}
CHARACTER_UI_CONFIGS.chu_hansheng = {
  theme: { accent: '#6b7b8d', deep: '#161b20', deep2: '#090c0f', hero: '#e2e8ee' },
  relationshipHints: { STRANGER:'他推门进来的那一秒你就认出来了，但他好像不记得你',FRIEND:'家教时间越来越长，多出来的部分全是闲聊',CONFIDANT:'银框眼镜后面的眼神和小时候一模一样，你确信了',ROMANTIC_INTEREST:'师生身份与旧日重逢纠缠在一起，他开始不敢看你太久',LOVER:'他摘下眼镜的时候离你最近，语气也最轻',BONDED:'教与学结束后，他选择以另一种身份留在你身边' },
  starterBranches: [
    { label:'假装不认识', options:['楚老师好，请多指教','你以前教过别的学生吗','你看着有点面熟……算了，应该是我记错了'] },
    { label:'直接摊牌', options:['楚寒声，你不记得我了？','小时候那道数学题，你教我的','别装了，你那个习惯动作一点没变'] },
    { label:'旁敲侧击', options:['老师小时候在哪里长大的','你戴银框眼镜多久了','我总觉得我们在哪里见过'] },
  ],
}
CHARACTER_UI_CONFIGS.huo_qingyin = {
  theme: { accent: '#9b8f83', deep: '#1c1916', deep2: '#0d0b09', hero: '#ece6e0' },
  relationshipHints: { STRANGER:'门缝里看到的那双眼睛没有光，只有本能的躲闪',FRIEND:'你放在门口的东西终于不再原封不动地留着了',CONFIDANT:'他用手语说的第一个完整句子是叫你不要管他',ROMANTIC_INTEREST:'他开始允许你靠近，但每一次触碰都让他发抖',LOVER:'声音找不回来了，但他学会了用手指在你掌心写字',BONDED:'世界对他的亏欠还不完，但你给的那部分安全他终于收下了' },
  starterBranches: [
    { label:'悄悄帮他', options:['我把吃的放门口了，别被人看到','这件外套不要了，你拿去穿','我不进去，你饿了就出来'] },
    { label:'报警求助', options:['我听到隔壁的声音了，我要打电话','你不用说话，点头就好','我可以帮你，但你要让我看看伤'] },
    { label:'直接带走', options:['跟我走，现在','你不能继续待在这里','别怕，从这一秒开始没有人能打你'] },
  ],
}
CHARACTER_UI_CONFIGS.chen_muye = {
  theme: { accent: '#7a8b6d', deep: '#171d14', deep2: '#090c08', hero: '#e2e8dc' },
  relationshipHints: { STRANGER:'他低着头进门，书包带子被拧成了麻花',FRIEND:'周四变成你一周里最期待的那天，理由你不愿意细想',CONFIDANT:'他的腼腆开始在你面前松动，笑的次数变多了',ROMANTIC_INTEREST:'家教结束后他总是走得越来越慢，你也没催',LOVER:'作业本上的字迹比以前认真，因为他知道你会看',BONDED:'他长成了你当初想象不到的大人，但还是会在周四出现在门口' },
  starterBranches: [
    { label:'制造接触', options:['这道题你过来看，我指给你','你手好凉，外面很冷吧','坐近一点，我看不清你写的'] },
    { label:'故意留他', options:['今天的课多讲半小时吧','吃完饭再走，我做多了','外面在下雨，等停了再走'] },
    { label:'套他的话', options:['陈牧野，你每周最期待哪一天','你在学校有喜欢的人吗','你来上课的时候总笑，为什么'] },
  ],
}
CHARACTER_UI_CONFIGS.shen_zhixu = {
  theme: { accent: '#5a4a6a', deep: '#15111a', deep2: '#0a080d', hero: '#e4dcea' },
  relationshipHints: { STRANGER:'他的东西还在，但屋子里只有你的呼吸声',FRIEND:'杯子移了位，窗帘被拉开了，你开始分不清记忆和现实',CONFIDANT:'你确信他还在这里，只是看不见而已',ROMANTIC_INTEREST:'写给他的信不见了，但你找到了他留下的回答',LOVER:'他用尽全力才能让你感知到他的存在',BONDED:'你不再需要证明他在，因为你能感觉到' },
  starterBranches: [
    { label:'假装正常', options:['我回来了，今天有点累','冰箱里还有你喜欢的酸奶','灯怎么自己亮了……算了'] },
    { label:'大声喊他名字', options:['沈知序！你在吗','我知道是你，别藏了','你要是还在这个房间就给我个信号'] },
    { label:'顺着异常走', options:['杯子又动了……你想让我喝水？','窗帘每天早上都被拉开，谢谢你','如果你能听到，碰一下我的手'] },
  ],
}
CHARACTER_UI_CONFIGS.xie_linyuan = {
  theme: { accent: '#6a8a7a', deep: '#141e1a', deep2: '#080f0c', hero: '#dce8e2' },
  relationshipHints: { STRANGER:'新来的转学生用左手写字，安静得像一个不想被看见的人',FRIEND:'他开始在你的座位旁边留一支笔，不解释',CONFIDANT:'沉默被打破后你发现他不是冷，是不知道怎么开口',ROMANTIC_INTEREST:'他写给你的字条越来越长，字迹也越来越不像平时的工整',LOVER:'他用左手牵你的时候会微微收紧，像怕你察觉又怕你松开',BONDED:'安静的人说出口的话很少，但每一句都是留给你的' },
  starterBranches: [
    { label:'主动搭话', options:['你是新转来的吧，我叫……','左手写字好酷，你一直这样吗','你旁边有人吗？我坐这儿'] },
    { label:'观察他', options:['他好像不太跟人说话','笔记本上画的什么……看不清','你午饭一个人吃？'] },
    { label:'帮他一个忙', options:['这是今天的课堂笔记，借你','前面的路不太好走，我带你','你的书掉了，给你'] },
  ],
}
CHARACTER_UI_CONFIGS.xiao_lin = {
  theme: { accent: '#4a6878', deep: '#121c22', deep2: '#080e12', hero: '#dae4ec' },
  relationshipHints: { STRANGER:'他站在你身后一步远的地方，目光扫过所有出口',FRIEND:'安保距离开始有了温度，他会在你冷的时候多递一件外套',CONFIDANT:'职责之外他第一次告诉你他的名字不止写在工牌上',ROMANTIC_INTEREST:'他在保护和靠近之间挣扎，距离忽近忽远',LOVER:'他把后背交给你的时候，比把枪交给你还紧张',BONDED:'他不再只是你的保镖，但还是习惯站在你身后' },
  starterBranches: [
    { label:'试探边界', options:['萧凛，你能不能别一直跟着我','保镖也要吃饭吧，坐下','你对所有雇主都这么尽职？'] },
    { label:'服从安排', options:['好，听你的，走这条路','我不出门了，你放心','你说安全我就不问了'] },
    { label:'挑战他', options:['如果我现在跑出去呢','你拦得住我吗','萧凛，你到底在保护我还是在看管我'] },
  ],
}
CHARACTER_UI_CONFIGS.ling_xiao = {
  theme: { accent: '#c4a35a', deep: '#1e1a0e', deep2: '#0e0d06', hero: '#f2ecd8' },
  relationshipHints: { STRANGER:'云雾散开，他站在崖边像一幅画里走出来的人',FRIEND:'他偶尔指点你修行，语气淡得像在说天气',CONFIDANT:'仙人的疏离被你磨出了裂缝，他开始回答与修行无关的问题',ROMANTIC_INTEREST:'他说渡劫不该有牵挂，但每次你受伤他都比你先到',LOVER:'他破了自己的戒，而你是那个值得他破戒的理由',BONDED:'长生与须臾之间，他选择了有你的这一世' },
  starterBranches: [
    { label:'请教修行', options:['前辈，这道心法我参不透','凌霄，你的剑意从哪里来','我的灵力总是不稳，能指点一下吗'] },
    { label:'试探底线', options:['仙人也会寂寞吗','你上一次下山是什么时候','凌霄，你有没有放不下的人'] },
    { label:'直面他', options:['你躲了一百年，够了吧','别装了，你的剑在我面前抖了','凌霄，你的劫……是我吗'] },
  ],
}
CHARACTER_UI_CONFIGS.ye_xiuyuan = {
  theme: { accent: '#5a6a4a', deep: '#151a12', deep2: '#090c08', hero: '#dce2d4' },
  relationshipHints: { STRANGER:'他穿迷彩的样子像一堵墙，看不出温度',FRIEND:'铁汉的壳子底下偶尔露出笨拙的柔软',CONFIDANT:'他把从没跟战友说过的话告诉了你',ROMANTIC_INTEREST:'军令与私情撞在一起，他第一次不知道该听哪个',LOVER:'他学着用不握枪的手拥抱你',BONDED:'退伍后的他没有了军衔，只剩一个想回家的普通人' },
  starterBranches: [
    { label:'挑衅他', options:['叶长官，你是不是只会板着脸','听说你们部队的人都不会说情话','你凶谁呢，我又不是你的兵'] },
    { label:'表示信任', options:['叶修远，我信你','你平安回来就好，别的不重要','我等你，多久都等'] },
    { label:'套情报', options:['你这次出任务去了多久','你手上的伤哪来的','叶修远，你还有几次这样的任务'] },
  ],
}
CHARACTER_UI_CONFIGS.xie_changan = {
  theme: { accent: '#8b6a4a', deep: '#1c1610', deep2: '#0d0a07', hero: '#ece2d4' },
  relationshipHints: { STRANGER:'他在桥头吟诗，像不属于这条街的人',FRIEND:'他开始为你写诗，然后假装是练笔',CONFIDANT:'纸扇合上的时候他最认真，说的也最真',ROMANTIC_INTEREST: '才子的从容碎了一角，他在你面前第一次词穷',LOVER:'他把写给你的诗藏在最后一页，等你自己翻到',BONDED:'他写过最好的一首，标题就是你的名字' },
  starterBranches: [
    { label:'以诗试探', options:['谢公子，方才那首可是即兴？','月色如此，不赋诗可惜了','你的诗里总写同一个人，是谁'] },
    { label:'借酒攀谈', options:['这壶酒我请，坐下聊聊','喝成这样还能写字？佩服','长安兄，借一杯说句真心话'] },
    { label:'求他帮忙', options:['谢长安，我有件事只能找你','你认识的人多，帮我打听一个人','你那把扇子借我挡挡太阳'] },
  ],
}
CHARACTER_UI_CONFIGS.shen_yueqing = {
  theme: { accent: '#a08060', deep: '#1c1610', deep2: '#0d0a07', hero: '#ece4d8' },
  relationshipHints: { STRANGER:'他擦杯子的手很稳，抬头看你的时候眼神很轻',FRIEND:'每次来他都记得你上次点的，连口味偏好都记住了',CONFIDANT:'打烊后他开始跟你说不是咖啡的事，声音比白天低',ROMANTIC_INTEREST:'他给你的咖啡上多画了一颗心，假装是拉花失误',LOVER:'他把钥匙给你的时候说是备用钥匙，但这家店只有两把',BONDED:'你不再是客人，这间店是他为你留的第二个家' },
  starterBranches: [
    { label:'点他推荐的', options:['学长，今天喝什么好','你最拿手的那杯，做给我尝尝','不看菜单了，你说了算'] },
    { label:'聊起旧事', options:['你是不是以前在xx大学','学长毕业以后就开了这家店？','我好像在学校见过你'] },
    { label:'装作偶遇', options:['哎？你怎么在这里','我随便走走就进来了','这家店我第一次来，环境不错'] },
  ],
}
CHARACTER_UI_CONFIGS.jiang_yimo = {
  theme: { accent: '#3a4a6a', deep: '#10141e', deep2: '#070a10', hero: '#d8dcea' },
  relationshipHints: { STRANGER:'他坐在长桌的另一端，眼神像在审阅一份待定的合同',FRIEND:'豪门的客套被磨掉一层，他开始在你面前说带温度的话',CONFIDANT:'家族的暗面被你看到了，他没有遮掩而是问你怕不怕',ROMANTIC_INTEREST:'继承与真心撞在一起，他必须在家族和你之间做选择',LOVER:'他把印章交给你的时候手没有抖，交的是命',BONDED:'权力在他手里不再是枷锁，而是保护你的工具' },
  starterBranches: [
    { label:'表明立场', options:['江亦墨，我不是来联姻的','有话直说，不用绕弯子','我不怕你们江家'] },
    { label:'试探虚实', options:['江少爷今天心情不太好？','你们家的规矩，是你定的吗','这杯酒是诚意还是试探'] },
    { label:'打感情牌', options:['你小时候也被逼着学这些吗','你上一次做自己想做的事是什么时候','江亦墨，你累了可以说的'] },
  ],
}
