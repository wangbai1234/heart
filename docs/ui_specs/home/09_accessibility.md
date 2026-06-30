# 09 Accessibility — 首页 Home

---

## 触摸目标尺寸（iOS HIG 标准：最小 44×44 pt）

| 元素 | 估算尺寸 | 是否达标 | 备注 |
|------|---------|---------|------|
| UserAvatarButton（右上角头像） | ~40×40 pt | ⚠️ 偏小 | 建议将可点击区域扩大至 44×44 pt（padding 扩大，不改变视觉） |
| StartChatButton（开始聊天） | ~120×38 pt | ⚠️ 高度偏小 | 建议高度增至 44 pt，视觉可保持 38 pt 但 hitbox 扩大 |
| QuickActionTile（每格） | ~111×90 pt | ✅ 达标 | 宽高均超 44 pt |
| ViewAllLink（查看全部） | 文字级别 ~60×24 pt | ❌ 不达标 | 建议 padding 增大使可点击区域 ≥ 44×44 pt |
| ConversationListItem（整行） | ~390×80 pt | ✅ 达标 | 全宽行，高度充足 |
| BottomTabItem（每格） | ~97.5×49 pt | ✅ 达标 | Tab 区域高度 49 pt，宽度充足 |
| HeroCard 整体 | 不可点击整体 | N/A | 仅内部按钮响应交互 |

**总结**：用户头像、开始聊天按钮、查看全部链接三处需扩大 hitbox，视觉无需改变。

---

## 颜色对比度（WCAG AA 最低要求：普通文字 4.5:1，大文字/粗体 3:1）

| 前景色 | 背景色 | 估算对比度 | 文字大小 | WCAG 等级 | 评估 |
|--------|--------|-----------|---------|-----------|------|
| #3A3A4A（yuoyuo App名） | #FFF0F3（页面背景） | ~11:1 | 26pt Bold | AAA ✅ | 高对比，优秀 |
| #3A3A4A（角色名"神无月凛"） | 卡片玻璃层 rgba白60% | ~8:1（估算） | 22pt SemiBold | AAA ✅ | 达标 |
| #8E8E9A（状态文字） | 卡片玻璃层 rgba白60% | ~3.5:1（估算） | 13pt Regular | AA ⚠️（大文字） | 边界，建议验证实际值 |
| #3A3A4A（对话行角色名） | #FFF0F3 | ~11:1 | 16pt SemiBold | AAA ✅ | 优秀 |
| #8E8E9A（对话预览文字） | #FFF0F3 | ~3.9:1（估算） | 14pt Regular | ⚠️ 未达 AA（4.5:1） | 建议加深至 #6E6E80 |
| #8E8E9A（时间戳） | #FFF0F3 | ~3.9:1（估算） | 13pt Regular | ⚠️ 未达 AA | 同上，建议加深 |
| #FF7A9A（"开始聊天"按钮文字） | rgba白 85% | ~3.2:1（估算） | 15pt Medium | ⚠️ 边界 | 建议验证，考虑加深文字或按钮背景 |
| #FFB7C5（Tab Active 文字） | rgba白92% Tab背景 | ~2.8:1（估算） | 10pt Regular | ❌ 不达标 | 偏小字号+低对比，建议加深 Active 色至 #FF7A9A |
| #ADADB8（Tab Inactive 文字） | rgba白92% Tab背景 | ~2.5:1（估算） | 10pt Regular | ❌ 不达标 | 10pt 字号过小且对比不足，建议字号≥11pt + 加深色值 |

> 注：所有对比度值为基于色值估算，需用工具（如 Figma A11y Annotation / WebAIM Contrast Checker）验证实际值。

---

## 焦点状态（Keyboard Focus）

| 场景 | 当前设计稿状态 | 建议 |
|------|-------------|------|
| 所有可点击元素 | ⚠️ 设计稿未定义焦点状态 | 添加 2pt 实线焦点环，颜色 #FFB7C5，offset 2pt |
| 底部 Tab | ⚠️ 未定义 | 为 Active Tab 图标添加明显焦点环 |
| StartChatButton | ⚠️ 未定义 | 同上 |

**Tab 顺序建议（键盘导航顺序）**：
1. AppBar - UserAvatarButton
2. HeroCard - StartChatButton
3. QuickActionTile - 兑换会员
4. QuickActionTile - 切换角色
5. QuickActionTile - 设置
6. SectionHeader - ViewAllLink
7. ConversationListItem 1（神无月凛）
8. ConversationListItem 2（桃乐丝）
9. BottomTabBar - 首页
10. BottomTabBar - 聊天
11. BottomTabBar - 角色
12. BottomTabBar - 设置

---

## 文本可读性

| 文字元素 | 字号（估算） | 行高（估算） | 是否达标 |
|---------|-----------|-----------|---------|
| App 名"yuoyuo" | 26 pt | 1.0（单行，无需行高） | ✅ 字号 ≥12pt |
| 角色名（Hero Card） | 22 pt | 1.3 | ✅ |
| 状态文字 | 13 pt | 1.4 | ✅ 字号 ≥12pt，行高 ≥1.4 |
| 对话角色名 | 16 pt | 1.4 | ✅ |
| 对话预览文字 | 14 pt | 1.5（估算） | ✅ |
| 时间戳 | 13 pt | 1.4（估算） | ✅ |
| 瓷砖标签 | 13 pt | 1.4 | ✅ |
| Tab 标签 | 10 pt | 1.2 | ⚠️ 字号略小，建议 ≥11pt；行高偏低，但单行可接受 |
| "开始聊天"按钮 | 15 pt | 1.0（按钮内单行） | ✅ |
| "最近的......" | 16 pt | 1.3 | ✅ |
| "查看全部 >" | 13 pt | 1.0（单行） | ✅ |

---

## ARIA 建议

| 元素 | 建议 ARIA 属性 | 说明 |
|------|-------------|------|
| Page 根节点 | `role="main"` | 标识主内容区 |
| BottomTabBar | `role="navigation"`, `aria-label="主导航"` | Tab 导航区 |
| Tab 每项 | `role="tab"`, `aria-selected="true/false"`, `aria-label="首页"` 等 | 当前 Tab 状态 |
| UserAvatarButton | `role="button"`, `aria-label="个人中心"` | 头像按钮无文字 |
| HeroCard | `role="region"`, `aria-label="当前AI伴侣神无月凛"` | 内容区 region |
| HeartOrb | `role="img"`, `aria-label="情绪宝珠，当前心情：温柔"` | 装饰性但有语义 |
| StartChatButton | `role="button"`, `aria-label="开始和神无月凛聊天"` | 按钮含义明确 |
| QuickActionTile_Member | `role="button"`, `aria-label="兑换会员"` | — |
| QuickActionTile_Character | `role="button"`, `aria-label="切换角色"` | — |
| QuickActionTile_Settings | `role="button"`, `aria-label="设置"` | — |
| SectionHeader | `role="heading"`, `aria-level="2"` | 内容区标题层级 |
| ViewAllLink | `role="link"`, `aria-label="查看全部最近对话"` | 补充上下文 |
| ConversationListItem | `role="button"` 或 `role="listitem"` within `role="list"` | 建议列表容器加 `role="list"`, `aria-label="最近对话"` |
| CharacterAvatar（列表头像） | `role="img"`, `aria-label="角色头像：神无月凛"` | — |
| UnreadDot（未读点） | `aria-label="有新消息"` | 视觉指示需文字替代 |
| 时间戳 | `aria-label="最后消息时间：22时18分"` 或 "昨天" | 朗读更友好 |

---

## Keyboard Navigation

| 操作 | 建议行为 |
|------|---------|
| `Tab` | 按上述顺序移动焦点 |
| `Enter` / `Space` | 激活当前焦点元素（按钮/链接/Tab） |
| `Escape` | 无全局 Escape 行为（本页面无 Modal/Overlay） |
| `Arrow Keys` | 在 BottomTabBar 内左右切换 Tab（`role="tablist"` 语义下）|
| 滑动返回 | 移动端 iOS Back Gesture，无键盘替代；Web 版使用浏览器返回 |

---

## Screen Reader（朗读文本建议，中文）

| 元素 | 建议朗读文本 |
|------|------------|
| 页面进入 | "yuoyuo，首页" |
| UserAvatarButton | "个人中心" |
| HeartOrb | "情绪宝珠，神无月凛，当前心情：温柔" |
| CompanionName | "当前AI伴侣：神无月凛" |
| CompanionStatus | "刚刚和你聊过，心情：温柔" |
| StartChatButton | "开始和神无月凛聊天" |
| QuickActionTile_Member | "兑换会员" |
| QuickActionTile_Character | "切换角色" |
| QuickActionTile_Settings | "设置" |
| SectionHeader | "最近对话" |
| ViewAllLink | "查看全部最近对话" |
| ConversationListItem 1 | "神无月凛，今天过得怎么样呀？有没有遇到什么开心的事～，22时18分，有新消息" |
| ConversationListItem 2 | "桃乐丝，晚安呀，记得多喝水，明天见～我会在这里等你哦。，昨天，有新消息" |
| Tab 首页 Active | "首页，当前所在，共4个标签" |
| Tab 聊天 | "聊天，共4个标签" |
| Tab 角色 | "角色，共4个标签" |
| Tab 设置 | "设置，共4个标签" |

---

## 移动端操作友好度（单手操作 / 拇指区域分析）

基于 iPhone 14（390×844 pt）右手单手操作分析：

| 区域 | Y 范围 | 拇指可达性 | 建议 |
|------|--------|-----------|------|
| BottomTabBar | 761~844 pt | ✅ 最优（拇指自然落点） | 核心导航放置正确 |
| StartChatButton（卡片右下角） | 约 380~420 pt | ✅ 良好（中部偏上，右侧） | 位置合理，右下角符合右手习惯 |
| QuickActionTiles | 约 440~530 pt | ✅ 良好 | 中部区域，双手/单手均可 |
| ConversationListItem 行 | 约 560~720 pt | ✅ 良好（偏下） | 位置友好，拇指易到达 |
| UserAvatarButton（右上角） | 47~103 pt | ⚠️ 难以单手到达 | 属常规位置，可接受；或加大按钮区域 |
| ViewAllLink（Section右上） | 约 565~600 pt | ✅ 良好（偏下区域） | — |
| AppBar（yuoyuo名称） | 47~103 pt | ⚠️ 纯展示，无需操作 | — |

**总体单手评分：✅ 良好** — 核心操作（开始聊天、Tab 导航、对话列表）均落在拇指舒适区（Y > 350 pt），符合 iOS 人机交互指南。
