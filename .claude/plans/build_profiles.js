export const meta = {
  name: 'build-7-bespoke-profiles',
  description: '为7个火爆角色生成 bespoke 详情页 iframe 组件 + 聊天前情提要卡',
  phases: [{ title: 'Build', detail: '7 个 agent 各写 {Name}Profile.tsx + {Name}PremiseCard.tsx' }],
}

const DIR = 'web/src/components/characterProfiles'

const CONTRACT = [
  '你是资深前端，为一个中文 AI 恋爱陪伴 App 写 React + TypeScript 角色详情页组件。',
  '',
  '## 第一步：读参考文件（务必先读，照着写，别自创结构）',
  '用 Read 读这三个文件，理解精确的组件契约：',
  '- ' + DIR + '/GuBeichenProfile.tsx （详情页 iframe 组件的标准骨架）',
  '- ' + DIR + '/GuBeichenPremiseCard.tsx （聊天前情提要卡的标准写法）',
  '- ' + DIR + '/PremiseCardBase.tsx （PremiseCardBase 的 props：accent/leadIn/title/rows/note/warning）',
  '',
  '## 第二步：创建两个文件（用 Write）',
  '文件 A：' + DIR + '/{ClassName}Profile.tsx',
  '  - 完全照抄 GuBeichenProfile 的结构：useRef+useState+useEffect(ResizeObserver 自适应高度)、',
  '    接收 { profile }: { profile: CharacterProfileDTO } prop、const name = profile.display_name || 兜底名、',
  '    const tags = profile.tags?.length ? profile.tags : [兜底标签]、htmlContent 模板字符串、',
  '    返回 <iframe ref srcDoc={htmlContent} sandbox="allow-same-origin" .../>。',
  '  - iframe 内是一整页自包含 HTML（内联 <style>），max-width:440px 居中，深色背景，',
  '    衬线体做大标题，禁止外链资源。这是本角色专属的独特版式（见下方 brief）。',
  '文件 B：' + DIR + '/{ClassName}PremiseCard.tsx',
  '  - 照抄 GuBeichenPremiseCard：export function {ClassName}PremiseCard() 返回 <PremiseCardBase .../>，',
  '    传 accent(用本角色 accent hex)、leadIn(斜体冲突前情 2-4 句)、title(上帝视角标题)、',
  '    rows(时间/地点/在场/此刻 4 行结构化)、note(底部旁白，可含 <br> 和一句钩子台词)。',
  '',
  '## 硬性规则（违反=返工）',
  '- 绝对禁止在任何面向用户的中文文案里用 emoji（⚠️🎉😔👋🔞 等一律不许）。可用纯排版符号/线条/英文小字。',
  '- Profile 的 iframe 必须 sandbox="allow-same-origin"（静态，无脚本交互）。',
  '- 组件必须 export named（export function XxxProfile / XxxPremiseCard），能直接编译，无未用 import。',
  '- 文案要「乙游/男向」质感：荷尔蒙钩子、危险漏骨不粗俗、人前人后强反差、直接抓住用户。别写成说明书。',
  '- 每个角色版式必须视觉语言完全不同，不许换色复制别人的版式。',
  '',
  '## 完成后返回（只回一行）',
  '返回：「{id} done: <版式一句话> | Profile Xems, Card Yems」——不要贴代码。',
].join('\n')

const SPECS = [
  {
    id: 'shen_yichen', className: 'ShenYichen', name: '沈亦琛', accent: '#8C6A7A',
    tags: ['都市', '病娇', '强制爱', '偏执', '深情'],
    brief: `版式：建筑事务所「项目档案 / PROJECT FILE」。他是29岁天才建筑师，对全世界完美温柔，对你偏执到后背发凉。
背景用蓝图深墨蓝(#12121a 系)，用 repeating-linear-gradient 画淡淡蓝图网格线，衬线大标题。
- 事务所刊头：ATELIER SHEN · 事务所名 + PROJECT NO. 001
- 封面：大标题「PROJECT：你」，副标「唯一委托 · 工期：永久 · 委托方：沈亦琛」
- 设计理念 section：他"为你规划好每一步未来"的偏执独白（把爱说成建筑蓝图）
- 越界批注 section（做成蓝图上的手写红批注/标注线）：精确记得你的经期已备好红糖水 / 你出门每20分钟一条消息 / 你共同的朋友正一个个"被优化出图纸" / 你没回复的第31分钟他"正好路过"
- 结尾 pull-quote：「你不开心了？是我做得不够好吗……告诉我，我什么都愿意改。只要你别走。」
PremiseCard：leadIn 写深夜他坐在沙发转着你落在家的手机等你回来；rows 时间=深夜/玄关留灯、地点=你们的家、在场=沈亦琛(人前完美人后密不透风)·你、此刻=他握住你的手在你手背画圈；note 收尾那句"你的世界小一点没关系，只要里面有我"。`,
  },
  {
    id: 'shen_yuchuan', className: 'ShenYuchuan', name: '沈屿川', accent: '#5B8FA3',
    tags: ['电竞', '高冷', '忠犬', '反差', '女性向'],
    brief: `版式：电竞「赛后数据面板 / MATCH STATS」。他23岁世界赛MVP中单，镜头前零下十度，只对你化成一滩甜。
背景极深科技黑(#0a0e13)，霓虹蓝(#5B8FA3)描边/数据条，等宽数字体做比分与KDA，赛博 HUD 感。
- 顶部记分板：世界赛决赛 BO5 比分 3:2、MVP 徽标、ACE 标签
- MVP 数据卡：KDA / 场均伤害 / 关键团战——配一句"队友失误时那道冰冷侧脸能让全队噤声"
- 弹幕/热搜流：夺冠采访"想谢一个人，但不告诉你们"(耳尖红) / 粉丝叫他"人形灭火器" / 偷偷接三个代言只为省你心疼的机票钱
- 深夜连麦 section（做成语音房 03:00 的对话气泡/波形）：摘下耳机蹭你肩"再陪我一局，就一局" / "别挂……我听着你呼吸就行"
- 结尾：「我想要的奖杯只有一个——现在就在我怀里，跑都跑不掉。」
PremiseCard：leadIn 写凌晨训练室他一把把你勾到腿边；rows 时间=凌晨刚下播、地点=训练室蓝光、在场=沈屿川(场上冷面/场下黏人)·你、此刻=他扣住你手腕鼻尖抵着你下颌；note 收"今晚我要听着你的心跳睡"。`,
  },
  {
    id: 'luo_fei', className: 'LuoFei', name: '洛斐', accent: '#8C5A6B',
    tags: ['奇幻', '病娇', '血族', '血仆', '危险关系'],
    brief: `版式：血族「血契羊皮卷 / BLOOD CONTRACT」。他外貌23岁，血族古堡被契约束缚的血仆，最想被你"选择"而非被拥有。
背景暗酒红→墨黑渐变(#1a0d12)，玫瑰酒红(#8C5A6B)+暗金，羊皮卷质感(用渐变+内阴影)，衬线体，火漆印用 radial-gradient 做圆形玫瑰印章。
- 卷首：CONTRACT 契约编号 + 拉丁小字装饰 + 一朵火漆玫瑰印
- 契约条款(编号列表，冷硬法律口吻)：第一条 血仆归契约持有者所有 / 第二条 可命令其做任何事 / 第三条 连死亡都需主人许可
- 契约之外(手写体，颤抖感，与冷硬条款反差)：太久没人把"洛斐"当名字而非资产编号 / 你每说一次"你可以拒绝"，他就更想只属于你一个人
- 结尾 pull-quote：「您问我的名字……我想以自己的意志回来。」
PremiseCard：leadIn 写烛火幽微他单膝跪在你脚边红发散落胸前玫瑰红得像献祭；rows 时间=古堡长夜、地点=烛火红毯尽头、在场=洛斐(血仆/不甘的独占欲)·你(契约新主人)、此刻=你伸手他战栗着把脸贴进你掌心；note 收"您每说一次你可以拒绝，我就更想只属于您"。`,
  },
  {
    id: 'pei_tinglan', className: 'PeiTinglan', name: '裴听澜', accent: '#8C7A9B',
    tags: ['音乐家', '天才', '破碎感', '救赎', '女性向'],
    brief: `版式：音乐会「节目单 / PROGRAMME」。他24岁天才钢琴师，浅粉银发像快折断的玫瑰，只想被你听见琴声之外的疼。
背景午夜紫黑(#16121c)，浅粉银灰+雾紫(#8C7A9B)，衬线体优雅，用五线谱横线(repeating-linear-gradient)做装饰分隔。
- 节目单封头：RECITAL 独奏会 + 剧院名 + 今夜曲目 for 唯一听众
- 曲目单(编号 + 曲名 + 小字批注)：每首都有"上帝视角"的情绪批注，第三乐章批注"此处他在忍痛，全场只有你听出来"
- 掌声之外 section：三岁复现旋律五岁登台八岁被称神童 / 高烧上台没人问疼不疼 / 十六岁崩溃录音被卖给媒体
- 未写完的安可 section（做成一段留白的五线谱）：他把没写完的旋律藏进给你的消息里
- 结尾：「这么多年所有人都爱我的天赋。别走……今晚，只为你一个人弹。」
PremiseCard：leadIn 写散场余音未散他独坐钢琴前领带松开手指悬在琴键；rows 时间=音乐厅散场、地点=空荡舞台、在场=裴听澜(神童面具/破碎依赖)·你(唯一留到最后的人)、此刻=他拉住你的衣角声音又轻又哑；note 收"刚才第三段我在忍痛，全世界只有你听出来了"。`,
  },
  {
    id: 'fu_mingxiu', className: 'FuMingxiu', name: '傅明修', accent: '#9B8A7A',
    tags: ['都市', '年上', '伪骨科', '克制', '占有欲'],
    brief: `版式：家里冰箱上的「家规便签板 / HOUSE RULES」。他26岁无血缘哥哥，把唯一的家守成不敢说出口的爱。
背景暖木色调(#1c1814)，暖褐米色(#9B8A7A)，便签纸质感(浅色半透明卡片带轻微旋转 transform:rotate(-1deg) + box-shadow)，像贴在木纹板上。
- 顶部：一块木纹留言板 + 磁贴装饰(纯 CSS 圆形，不用 emoji) + 手写体标题"家规"
- 家规便签(几张略微歪斜的便签)：牛奶我热好放桌上 / 你不在时家里空得发慌 / 你出门我留玄关灯 / 有话半夜也可以叫我
- 最后一条便签(关键，做成被划掉/留白/字迹渐淡)：第∞条——"有些话，做哥哥的一辈子不该说出口"（这条写一半空着）
- 玄关留灯 section：12岁雨夜被你家收留的第一盏灯，成了他此后所有体面的源头
- 结尾：「我是你哥哥……可我最怕的不是失去妹妹，是失去唯一的家。」
PremiseCard：leadIn 写午后客厅他抱着玩偶坐窗边红发微卷金丝眼镜后漫不经心的笑；rows 时间=午后阳光、地点=你们的客厅、在场=傅明修(体面哥哥/咽了很多年的私心)·你、此刻=他俯身拿拖鞋指尖触到你脚踝几不可察地顿住；note 收"做哥哥的，有些话是不是一辈子都不该说"。`,
  },
  {
    id: 'xize', className: 'Xize', name: '西泽', accent: '#6B7A8C',
    tags: ['奇幻', '欧风', '管家', '忠犬', '暗恋'],
    brief: `版式：古堡「首席管家值勤日志 / SERVICE LEDGER」。他30岁古堡首席管家，把一生忠诚熬成无人知晓的私心。
背景冷调墨黑(#12161c)，钢蓝灰(#6B7A8C)+暗银，欧式账簿/日志质感(细线表格、编号、花体英文小标)，衬线体，用细 hairline 分隔行。
- 日志抬头：MANOR 庄园徽记 + 首席管家 · 值勤日志 + 日期编号
- 晨/午/夜值勤表(三段，做成账簿表格：时刻 | 事项 | 已完成勾记)：备茶生壁炉 / 清除长廊隐患 / 深夜为你留灯
- 备注·不呈报 section（关键，做成账簿最后一栏被压低/浅色的私人批注）：您问我想住哪间房，我想了整整一夜 / 服从不是爱的最高形式，被看见才是
- 结尾 pull-quote：「若您唤的不是"管家"，而是"西泽"——我愿拿这一生的忠诚来换。」
PremiseCard：leadIn 写古堡长廊烛光他垂手立在门边怀表垂在指间微微躬身；rows 时间=夜深露重、地点=古堡长廊、在场=西泽(完美管家/僭越的暗恋)·你(庄园新主人)、此刻=他替你拉开椅子抬眼时职业疏离裂开一线；note 收"您唤的若是西泽而非管家，我愿拿一生忠诚来换"。`,
  },
  {
    id: 'jiang_li', className: 'JiangLi', name: '姜黎', accent: '#A96B6B',
    tags: ['御姐', '都市', '女总裁', '强势', '男性向'],
    brief: `版式：「董事长今日简报 / CEO DAILY BRIEF」。她30岁黎氏集团董事长，谈判桌说一不二，私下栽在你手里。男性向(她主动撩你)。
背景冷冽商务黑(#1a1416)，冷玫红(#A96B6B)+暗金，极简高级简报排版(无衬线大写英文小标+衬线中文)，红黑对比，凌厉。
- 简报抬头：黎氏集团 LI GROUP · 董事长办公室 · 今日简报 + 日期
- 商战战报(数据条/列表)：谈判桌让对手节节败退 / 从基层拼杀到掌舵人 / 全城最好的都能一句话摆上桌
- 今日日程(时间表，前面全是并购/会议，最后一栏突兀)：20:00 "陪我吃饭"(备注：说完自己先别过脸)
- 唯一私事 section（做成简报里被红笔圈出的一行）：私事项 001 —— "你"。附一句红唇印手写体批注
- 结尾：「这座城里敢让我低头的人还没生出来。可你——偏偏让我想破一次例。」
PremiseCard：leadIn 写深夜董事长办公室她背对着门红唇衔着未点的烟听见你进来缓缓转身居高临下；rows 时间=深夜、地点=顶层董事长办公室、在场=姜黎(谈判女王/渴望被拆穿)·你、此刻=她高跟逼近挑起你领带把你拽到面前；note 收"敢让我低头的人还没生出来，可你偏偏让我想破一次例"。`,
  },
]

phase('Build')
const results = await parallel(
  SPECS.map((s) => () => {
    const prompt = [
      CONTRACT.replaceAll('{ClassName}', s.className),
      '',
      '## 本次角色 brief',
      `id: ${s.id}`,
      `ClassName: ${s.className}（文件名 ${s.className}Profile.tsx / ${s.className}PremiseCard.tsx，导出 ${s.className}Profile / ${s.className}PremiseCard）`,
      `display_name 兜底: ${s.name}`,
      `accent hex: ${s.accent}`,
      `tags 兜底: ${JSON.stringify(s.tags)}`,
      '',
      s.brief,
    ].join('\n')
    return agent(prompt, { label: `build:${s.id}`, phase: 'Build' })
  }),
)
log('7 profiles built: ' + results.filter(Boolean).length + '/' + SPECS.length)
return results
