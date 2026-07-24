Heart 的 Character 页定位为 「羁绊中心」，不是角色市场，也不是通讯录。Explore 负责找故事；Character 负责“谁在陪我、我们走到哪了”。
一、角色页原型
默认首屏采用 重点角色优先 + 横向角色长廊。
[角色 / 羁绊]                         [我的创造] [+]

今日陪伴
┌────────────────────────────┐
│  大角色卡：最近互动 / 未读 / 主动来找你的角色       │
│  神无月凛                                  未读 2  │
│  「主人，今晚也会来见我吧？」                     │
│                                                  │
│  心动 · 68%  ━━━━━━━━━━━━━━━                  │
│  最近：13:47 主动消息                           │
│                                                  │
│  [继续聊天]   [羁绊档案]   [剧情邀约]              │
└────────────────────────────┘

陪伴长廊
[凛 心动68%] [桃乐丝 熟悉21%] [艾琳 相遇中] [小唐 私密]

羁绊档案预览
┌────────────────────────────┐
│ 当前阶段：心动                                      │
│ 亲密进度：68%                                      │
│ 最近一句：想要亲亲？先跪下叫我主人。                │
│ 未读消息：2                                        │
│ 来源：入驻角色 / 剧情相遇 / 我的创造                 │
└────────────────────────────┘
角色排序规则建议：
有未读 / 主动消息的角色优先。
最近互动角色其次。
亲密度高的长期陪伴角色其次。
新导入但未建立陪伴的角色进入“入驻角色”长廊。
剧情中遇见但未转正的角色显示为“相遇中”。
角色来源只做轻标识：
入驻：你导入的一批非剧情角色
相遇中：剧情中遇见过，尚未正式陪伴
陪伴中：已建立长期关系
原创：用户亲手养成的自创角色
关系阶段
使用带恋爱意味但不太油的阶段名：
初遇 → 靠近 → 心动 → 牵绊 → 相伴 → 共鸣
映射现有后端关系阶段即可，不需要重做 SS04：
STRANGER             → 初遇
ACQUAINTANCE / FRIEND → 靠近
CONFIDANT            → 心动
ROMANTIC_INTEREST    → 牵绊
LOVER                → 相伴
BONDED               → 共鸣
亲密度显示用你选的方案：
心动 · 68%
不显示“Lv.3”，避免太像数值养成工具。
二、角色详情页路线
第一版先做页内展开；后续升级独立“羁绊档案页”。
详情页未来结构：
[返回] 神无月凛                             [设置]

大头像 / 半身视觉
心动 · 68%

最近陪伴
- 最近一句话
- 最近主动消息
- 未读状态

共同回忆
- 第一次相遇
- 她记住的你
- 最近被唤起的记忆

剧情关联
- 已相遇：《人外×饲养指南》
- 可邀约：回到那晚的庭院

声音与陪伴设置
- 当前音色
- 主动消息
- 清空聊天
三、Chat 页面优化原型
保持聊天主体验，但加入克制的游戏陪伴感。
┌──────────────────────────┐
│ ←  凛  心动 · 68%     ⋯  │
│    今晚状态：想见你       │
└──────────────────────────┘

[系统轻事件卡]
凛刚刚来找过你
「主人，今晚也会来见我吧？」
[回应她]

[聊天气泡...]

[羁绊事件卡]
你们的关系进入「心动」
她开始更主动地靠近你。
[查看羁绊]

[剧情邀约卡]
从这一刻起，艾琳的故事线与你相连。
她似乎想带你回到《人外×饲养指南》的某个夜晚。
[进入剧情]
第一版 Chat 事件卡只做三类：
主动消息提示：承接现有 proactive message，不要丢。
关系升阶：当 relationship_states.current_stage 变化时展示。
剧情邀约：不是 AI 即兴生成，而是配置驱动，难度可控。
四、剧情邀约怎么低风险实现
不要做“聊天记忆和剧情记忆全融合”。第一版做 角色剧情 Hook：
character_story_hooks
- character_id
- scenario_id
- trigger_stage_min
- trigger_intimacy_min
- cooldown_hours
- invite_title
- invite_copy
- cta_label
触发条件：
用户和该角色关系达到某阶段，例如「心动」。
该角色有关联剧情。
用户最近没有收到过同一个邀约。
用户有活跃/可解锁剧情入口。
前端只展示事件卡，点击跳转 /explore/:scenarioId 或已有 run。这样剧情邀约只是“被角色邀请去 Explore 玩剧情”，不是把两个记忆系统硬揉在一起。
五、解锁角色流程
采用你选的视觉小说感：
剧情中遇见艾琳
↓
Character 页出现「相遇中」卡
↓
达成关键节点 / 结局
↓
解锁转正
↓
文案：
“从这一刻起，艾琳的故事线与你相连。”
↓
进入长期陪伴
记忆策略：
不导入完整剧情聊天记录。
只写入一条结构化“相遇摘要”。
例如：你们在《人外×饲养指南》中相遇；她选择留下来继续陪你。
这条摘要可进入 L3/L4 或角色初始共同回忆，避免污染长期聊天。
六、架构建议
前端新增展示模型，不直接把 UI 绑死在 CharacterDTO：
CompanionCardVM {
  characterId
  displayName
  avatarUrl
  source: 'built_in' | 'imported' | 'story_encounter' | 'user_created'
  companionStatus: 'locked' | 'encountered' | 'companioned'
  relationshipStageLabel
  intimacyPercent
  latestLine
  unreadCount
  hasProactive
  primaryAction
}
后端建议新增一个聚合接口：
GET /api/companions
它聚合：
characters
relationship_states
chat_messages 最新一句
user_character_read_state 未读
proactive 消息状态
角色来源 / 解锁状态
可用剧情邀约
这样 Character 页不用在前端拼多个 API，未来扩展也稳。
现有文件可演进位置：
[CharacterPage.tsx](/Users/wanglixun/heart/web/src/pages/CharacterPage.tsx)：改为羁绊中心
[ConversationChatPage.tsx](/Users/wanglixun/heart/web/src/components/ConversationChatPage.tsx)：加入顶部关系状态和事件卡
[charactersStore.ts](/Users/wanglixun/heart/web/src/stores/charactersStore.ts)：保留目录职责，新增 companion store 更干净
[routes_characters.py](/Users/wanglixun/heart/backend/heart/api/routes_characters.py)：不要继续塞太多关系逻辑，建议新建 /api/companions
核心原则：Explore 发现故事，Character 沉淀关系，Chat 推进陪伴。