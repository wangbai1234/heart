# 04 Components — 首页 Home

---

## 1. AppBar（顶部应用栏）

| 属性 | 值 |
|------|---|
| 组件名称 | AppBar / HomeHeader |
| 作用 | 展示 App 名称与用户入口 |
| 层级 | Header，固定在 Safe Area Top 以下 |
| 尺寸 | 宽度 390 pt，高度约 56 pt（估算值） |
| 布局 | Flex Row，justify-content: space-between，align-items: center |
| 内边距 | 左 20 pt，右 16 pt |

### 子元素

#### 1.1 App Name Label
| 属性 | 值 |
|------|---|
| 文字 | "yuoyuo"（全小写，固定） |
| 字体 | SF Pro Rounded，约 26 pt，Bold |
| 颜色 | #3A3A4A |

#### 1.2 User Avatar（右上角头像）
| 属性 | 值 |
|------|---|
| 形状 | 圆形 |
| 直径 | 约 40 pt（估算值） |
| 内容 | 用户或角色的动漫风格头像插图 |
| 边框 | 无明显描边，有轻微发光阴影（粉色 glow） |
| 状态 | Default / Pressed（跳转个人中心） |
| 交互 | 点击 → 进入个人中心页 |

### 状态
| 状态 | 说明 |
|------|------|
| Default | 如上描述 |
| Pressed | 透明度降至 0.75，轻微缩放 scale(0.95) |

---

## 2. HeroCard（情绪宝珠英雄卡片）

| 属性 | 值 |
|------|---|
| 组件名称 | HeroCard / CompanionCard |
| 作用 | 展示当前 AI 伴侣的情绪状态，提供进入对话的主 CTA |
| 层级 | 主内容区最上方 |
| 尺寸 | 宽约 358 pt，高约 280 pt（估算值） |
| 外边距 | 左右各 16 pt |
| 圆角 | 24 pt |
| 背景 | 梦幻云彩渐变图（详见 05_assets.md），底部信息区叠加半透明白色玻璃层 |
| 阴影 | 粉色柔和阴影，blur 约 20 pt，y offset 4 pt（估算值） |
| overflow | hidden（圆角裁剪背景图） |

### 子元素

#### 2.1 CloudBackground（云彩背景图）
- 充满卡片，粉紫暖黄渐变天空 + 白色云朵插图
- 详见 05_assets.md

#### 2.2 HeartOrb（心形情绪宝珠）
| 属性 | 值 |
|------|---|
| 形状 | 心形（SVG 路径，非 CSS 圆角） |
| 尺寸 | 约 120 × 130 pt（估算值） |
| 位置 | 卡片水平居中，距卡片顶部约 28 pt（估算值） |
| 材质 | 玻璃质感：粉→蓝紫渐变，高光反射白色，外发光淡紫色 |
| 效果 | 外发光 glow（紫色，模糊半径约 40 pt），内部高光点 |
| 状态 | 静态设计稿，动效参见 06_interactions.md |

#### 2.3 CompanionName（角色名称）
| 属性 | 值 |
|------|---|
| 文字 | "神无月凛" |
| 字体 | PingFang SC，约 22 pt，SemiBold |
| 颜色 | #3A3A4A（深炭） |
| 位置 | 宝珠正下方，水平居中，距宝珠约 16 pt（估算值） |

#### 2.4 CompanionStatus（伴侣状态文字）
| 属性 | 值 |
|------|---|
| 文字 | "刚刚和你聊过 · 心情：温柔" |
| 字体 | PingFang SC，约 13 pt，Regular |
| 颜色 | #8E8E9A（次级灰） |
| 位置 | 名称下方约 6 pt，水平居中（估算值） |

#### 2.5 StartChatButton（"开始聊天 →"CTA 按钮）
| 属性 | 值 |
|------|---|
| 文字 | "开始聊天 →" |
| 字体 | PingFang SC，约 15 pt，Medium |
| 文字颜色 | #FF7A9A（深粉，估算值） |
| 背景 | 白色或极浅粉白，约 rgba(255,255,255,0.85) |
| 圆角 | 16 pt（估算值） |
| 尺寸 | 约 120 × 38 pt（估算值） |
| 位置 | 卡片右下角，距右 16 pt，距底 16 pt |
| 阴影 | 无或极轻微 |

### 状态
| 状态 | 说明 |
|------|------|
| Default | 如上描述 |
| Pressed（按钮） | 背景加深，scale(0.97)，持续 150 ms |
| Loading | 宝珠有呼吸动效（脉冲 glow），按钮不变 |

---

## 3. QuickActionTile（快速操作瓷砖）

| 属性 | 值 |
|------|---|
| 组件名称 | QuickActionTile |
| 作用 | 快速入口按钮（兑换会员 / 切换角色 / 设置） |
| 数量 | 3 个，水平排列 |
| 尺寸 | 每格约 111 × 90 pt（估算值） |
| 布局 | Flex Row，均分，Gap 约 12 pt |
| 外边距 | 左右各 16 pt |
| 圆角 | 16 pt |
| 背景 | 奶油白 #FFF8F3 或 rgba(255,255,255,0.80)，轻微毛玻璃 |
| 边框 | 约 1 pt，rgba(255,183,197,0.20)（估算值） |
| 阴影 | 极轻，blur 约 8 pt，rgba(0,0,0,0.06)（估算值） |

### 子元素（每格）

#### 3.1 Icon（功能图标）
| 属性 | 兑换会员 | 切换角色 | 设置 |
|------|---------|---------|------|
| 图标类型 | 礼品盒 | 人形剪影/头像 | 齿轮 |
| 颜色 | 粉红 #FFB7C5（估算） | 薰衣草紫 #C8B6FF（估算） | 天蓝 #A7C7E7（估算） |
| 尺寸 | 约 32 × 32 pt（估算值） |
| 风格 | 线性图标，stroke 约 2 pt，圆头端点 |

#### 3.2 Label（功能文字）
| 属性 | 值 |
|------|---|
| 字体 | PingFang SC，约 13 pt，Regular |
| 颜色 | #3A3A4A |
| 距图标 | 约 8 pt |

### 状态
| 状态 | 说明 |
|------|------|
| Default | 如上描述 |
| Pressed | 背景加深约 5%，scale(0.96)，150 ms |
| Disabled | 不适用（默认均可点击） |

---

## 4. SectionHeader（区块标题行）

| 属性 | 值 |
|------|---|
| 组件名称 | SectionHeader |
| 作用 | 标题 + "查看全部"入口 |
| 尺寸 | 宽 390 pt，高约 36 pt（估算值） |
| 布局 | Flex Row，justify-content: space-between，align-items: center |
| 内边距 | 左 20 pt，右 16 pt |

### 子元素

#### 4.1 Section Title
| 属性 | 值 |
|------|---|
| 文字 | "最近的......" |
| 字体 | PingFang SC，约 16 pt，Bold |
| 颜色 | #3A3A4A |

#### 4.2 View All Link
| 属性 | 值 |
|------|---|
| 文字 | "查看全部 >" |
| 字体 | PingFang SC，约 13 pt，Regular |
| 颜色 | #8E8E9A |
| 交互 | 点击 → 对话历史列表页 |

---

## 5. ConversationListItem（对话列表行）

| 属性 | 值 |
|------|---|
| 组件名称 | ConversationListItem |
| 作用 | 展示单个 AI 角色的最近对话摘要 |
| 尺寸 | 宽 390 pt，高约 80 pt（估算值） |
| 布局 | Flex Row，align-items: center |
| 内边距 | 左 20 pt，右 16 pt，上下约 12 pt（估算值） |
| 背景 | 透明（继承页面背景） |
| 分隔 | 无分隔线，依靠行间距隔开 |

### 子元素

#### 5.1 CharacterAvatar（角色头像）
| 属性 | 值 |
|------|---|
| 形状 | 圆形 |
| 直径 | 约 56 pt（估算值） |
| 内容 | 角色动漫风格插图（神无月凛：黑紫发，桃乐丝：银灰发） |
| 边框 | 极细粉色边框，约 1.5 pt，粉紫色（估算值） |
| 阴影 | 无或极轻 |

#### 5.2 ConversationTextBlock（文字块）
| 属性 | 值 |
|------|---|
| 布局 | Flex Column，flex: 1 |
| 左边距 | 约 14 pt（距头像） |

- **角色名**：PingFang SC，约 16 pt，SemiBold，#3A3A4A，1行
- **对话预览第1行**：PingFang SC，约 14 pt，Regular，#8E8E9A，1行
- **对话预览第2行**：PingFang SC，约 14 pt，Regular，#8E8E9A，1行，末尾截断（ellipsis）

#### 5.3 MetaInfo（时间 + 未读徽章）
| 属性 | 值 |
|------|---|
| 布局 | Flex Column，align-items: flex-end |
| 时间文字 | 约 13 pt，Regular，#8E8E9A（"22:18"/"昨天"） |
| 未读红点 | 直径约 8 pt（估算值），纯色 #FFB7C5，圆形，时间正下方，间距约 4 pt |

### 状态
| 状态 | 说明 |
|------|------|
| Default | 如上 |
| Pressed | 背景变为淡粉色 rgba(255,183,197,0.12)，150 ms |
| 无未读 | 隐藏红点 |
| 有未读数字 | 红点变为角标气泡（含数字），⚠️ 设计稿未定义，建议参考 Motion Storyboard |

---

## 6. BottomTabBar（底部 Tab 栏）

| 属性 | 值 |
|------|---|
| 组件名称 | BottomTabBar |
| 作用 | 全局主导航，4 个 Tab |
| 尺寸 | 宽 390 pt，高 83 pt（含 Safe Area Bottom 34 pt） |
| 内容高度 | 49 pt |
| 布局 | Flex Row，均分 4 格 |
| 背景 | rgba(255,248,243,0.92)，backdrop-filter blur 约 20 pt |
| 顶部边框 | 约 0.5 pt，rgba(0,0,0,0.08)（估算值） |

### Tab Item（每格）
| Tab | 图标类型 | 标签 | Active 颜色 | Inactive 颜色 |
|-----|---------|------|------------|--------------|
| 首页 | 房子形图标 | 首页 | #FFB7C5 | #ADADB8 |
| 聊天 | 对话气泡 | 聊天 | #FFB7C5 | #ADADB8 |
| 角色 | 人形轮廓 | 角色 | #FFB7C5 | #ADADB8 |
| 设置 | 齿轮圆形 | 设置 | #FFB7C5 | #ADADB8 |

#### Tab Item 内部布局
| 属性 | 值 |
|------|---|
| 方向 | Flex Column，align-items: center |
| 图标尺寸 | 约 24 × 24 pt（估算值） |
| 图标与标签间距 | 约 4 pt |
| 标签字号 | 约 10 pt |
| Active 指示器 | 图标正下方圆点，约 4 pt 直径，#FFB7C5 |

### 状态
| 状态 | 说明 |
|------|------|
| Active | 图标+文字 #FFB7C5，有小圆点指示器 |
| Inactive | 图标+文字 #ADADB8，无指示器 |
| Pressed | scale(0.90)，150 ms |

---

## 可复用组件建议

| 组件 | 复用原因 |
|------|---------|
| `AppBar` | 所有主页面顶部均需，左 App 名 + 右头像是固定 pattern |
| `QuickActionTile` | 在其他功能页面可能出现类似三格操作区 |
| `SectionHeader` | 通用 Section 标题 + 查看全部，列表页/历史页均可复用 |
| `ConversationListItem` | 聊天列表页、历史页使用相同结构 |
| `BottomTabBar` | 全局 4 个主页面共用，必须提取 |
| `CharacterAvatar` | 任何显示角色头像处均复用：对话页、角色选择页、列表等 |
| `HeartOrb` | 宝珠作为情绪 Widget 可在多处出现（聊天页 header、角色页等） |
