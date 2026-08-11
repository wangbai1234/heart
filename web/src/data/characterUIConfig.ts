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
  /** 首聊引导气泡 3 条（替换通用的"你还好吗"） */
  starterPrompts?: [string, string, string]
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
