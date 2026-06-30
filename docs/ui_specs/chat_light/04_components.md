# 04 Components — 聊天页 Chat（浅色模式）

## 组件清单（按层级从上到下）

---

### 1. StatusBar（系统状态栏）

| 属性 | 值 |
|------|-----|
| 组件名称 | StatusBar |
| 作用 | 显示系统时间、信号、WiFi、电池状态 |
| 层级 | Z1，固定在屏幕顶部 |
| 尺寸 | 390 × 47 pt（估算值） |
| 布局 | Flex Row，space-between |

**内容：**
- 左侧：时间 "9:41"，字号约 15 pt，font-weight 600，颜色 #3A3A4A
- 右侧：信号格图标 + WiFi 图标 + 电池图标，均为系统原生图标，颜色 #3A3A4A

**状态：**
- Default：如图所示
- Dark Mode：本规范不涉及（当前为浅色模式）

**样式细节：**
- 背景透明，继承页面背景渐变
- 系统原生组件，不应由 App 自定义

**交互说明：** 系统控制，App 不干预。

---

### 2. Header / NavigationBar（角色信息导航栏）

| 属性 | 值 |
|------|-----|
| 组件名称 | ChatHeader |
| 作用 | 显示 AI 角色信息（头像/名字/在线状态），提供返回和更多操作入口 |
| 层级 | Z2，固定，覆盖在消息列表之上 |
| 尺寸 | 390 × 80 pt（估算值） |
| 布局 | Flex Row，align-items: center，space-between，padding 20 pt 水平 |
| 背景 | rgba(255,255,255,0.55)，backdrop-filter: blur(20px)（估算值） |
| 圆角 | 底部左右 radius-xl（约 24 pt，估算值） |
| 阴影 | shadow-header |

**子组件：**

#### 2a. BackButton（返回按钮）
- 图标："<"（Chevron Left）
- 触摸区域：44 × 44 pt
- 图标尺寸：约 12 × 20 pt（估算值）
- 颜色：#3A3A4A
- 状态：Default / Pressed（opacity 60%，估算值）

#### 2b. CharacterAvatar（角色头像）
- 尺寸：48 × 48 pt（估算值）
- 形状：圆形裁切（border-radius: 50%）
- 内容：二次元风格紫发少女插画（角色"小屿"）
- 边框：无明显边框（估算值）

#### 2c. CharacterInfo（角色名称+状态）
- 布局：Flex Column，gap 2 pt（估算值）
- 角色名"小屿"：font-size 17 pt，font-weight 600，颜色 #3A3A4A
- 在线状态行：Flex Row，align-items: center，gap 4 pt
  - 状态圆点：6 × 6 pt 圆形，颜色 #5FC8E8（蓝色，估算值）
  - 状态文字"温柔在线"：font-size 13 pt，font-weight 400，颜色 #888888（估算值）

#### 2d. MoreButton（更多操作按钮）
- 图标："···"（三点省略）
- 触摸区域：44 × 44 pt
- 颜色：#3A3A4A
- 状态：Default / Pressed（opacity 60%，估算值）

**状态：**
- Default：如图
- Scrolling：Header 毛玻璃效果可随滚动加深（⚠️ 设计稿未定义，建议参考 Motion Storyboard）

---

### 3. DateSeparator（日期分隔符）

| 属性 | 值 |
|------|-----|
| 组件名称 | DateSeparator |
| 作用 | 标注消息时间节点，分隔不同日期/时间段的消息 |
| 层级 | Z3，在消息列表内 |
| 尺寸 | 宽度自适应（约 140 pt，估算值），高度约 28 pt |
| 布局 | 水平居中，文字居中 |
| 背景 | 无背景（透明） |

**样式细节：**
- 文字"今天 · 上午 9:41"
- 字号约 12 pt（估算值）
- 颜色 #999999
- 无背景胶囊、无分隔线（与 WeChat 不同，更简洁）

**状态：** 仅 Default（静态展示）

---

### 4. AITextBubble（AI 文字消息气泡）

| 属性 | 值 |
|------|-----|
| 组件名称 | AITextBubble |
| 作用 | 展示 AI 角色发送的文字消息 |
| 层级 | Z3，消息列表内 |
| 最大宽度 | 约 260 pt（估算值） |
| 高度 | 自适应文字内容 |
| 布局 | 左对齐，Flex Row 容器，align-self: flex-start |
| Padding | 14 pt 垂直 × 16 pt 水平（估算值） |
| 圆角 | 右上 20 pt，右下 20 pt，左上 20 pt，左下 6 pt（估算值，气泡尾部） |
| 背景 | rgba(255,255,255,0.75)，毛玻璃效果 |
| 阴影 | shadow-bubble（估算值） |

**文字样式：**
- 字号：约 16 pt（估算值）
- 字重：400
- 颜色：#3A3A4A
- 行高：约 1.6（估算值）

**状态：**
- Default：如图
- Pressed：轻微 scale(0.98)，背景略深（⚠️ 设计稿未定义，建议参考 Motion Storyboard）
- Long Press：触发上下文菜单（复制/收藏等）（⚠️ 设计稿未定义）

**可见实例：**
1. "早上好，昨晚睡得怎么样？"
2. "讲给我听呀～我陪着你。"

---

### 5. UserTextBubble（用户文字消息气泡）

| 属性 | 值 |
|------|-----|
| 组件名称 | UserTextBubble |
| 作用 | 展示用户发送的文字消息 |
| 层级 | Z3，消息列表内 |
| 最大宽度 | 约 260 pt（估算值） |
| 高度 | 自适应文字内容 |
| 布局 | 右对齐，Flex Row 容器，align-self: flex-end |
| Padding | 14 pt 垂直 × 16 pt 水平（估算值） |
| 圆角 | 左上 20 pt，左下 20 pt，右下 20 pt，右上 6 pt（估算值，气泡尾部） |
| 背景 | #A7C7E7（天蓝色实色） |
| 阴影 | 无明显阴影（估算值） |

**文字样式：**
- 字号：约 16 pt（估算值）
- 字重：400
- 颜色：#FFFFFF
- 行高：约 1.6（估算值）

**状态：**
- Default：如图
- Pressed：轻微 scale(0.98)（⚠️ 设计稿未定义，建议参考 Motion Storyboard）
- Long Press：触发上下文菜单（⚠️ 设计稿未定义）

**可见实例：**
1. "做了个奇怪的梦。"
2. "好。"

---

### 6. AIVoiceBubble（AI 语音播放气泡）

| 属性 | 值 |
|------|-----|
| 组件名称 | AIVoiceBubble |
| 作用 | 展示 AI TTS 语音消息，支持点击播放 |
| 层级 | Z3，消息列表内 |
| 宽度 | 约 300 pt（估算值，固定宽度） |
| 高度 | 约 90 pt（估算值） |
| 布局 | Flex Column，内含两行 |
| Padding | 16 pt 四周（估算值） |
| 圆角 | 与 AITextBubble 相同（估算值） |
| 背景 | rgba(255,255,255,0.75) |
| 阴影 | shadow-bubble（估算值） |

**第一行布局（Flex Row，align-items: center，gap 10 pt）：**

#### 6a. PlayButton（播放按钮）
- 容器尺寸：约 32 × 32 pt（圆形，估算值）
- 图标：三角形（右箭头），大小约 14 pt（估算值）
- 图标颜色：#FFB7C5（樱花粉）
- 背景：无填充，仅图标（估算值）
- 状态：Default（暂停）/ Playing（显示暂停图标）（⚠️ 设计稿未定义播放中状态）

#### 6b. WaveformVisualizer（波形可视化）
- 宽度：约 170 pt（估算值）
- 高度：约 32 pt（估算值）
- 内容：多条不等高竖线（约 20-25 条，估算值）
- 颜色：渐变，从 #FFB7C5（左侧）→ #C8B6FF（右侧）（估算值）
- 线条宽度：约 2-3 pt（估算值）
- 线条间距：约 3 pt（估算值）

#### 6c. DurationLabel（时长标签）
- 文字："0:18"
- 字号：约 13 pt（估算值）
- 颜色：#999999
- 对齐：右端

**第二行：**
- 文字："AI朗读 · 可点击播放"
- 字号：约 12 pt（估算值）
- 颜色：#AAAAAA
- 对齐：水平居中（在气泡内）

**状态：**
- Default（未播放）：如图，播放按钮显示三角形
- Playing：播放按钮变为暂停图标，波形动态扫描动画（⚠️ 设计稿未定义，建议参考 Motion Storyboard）
- Pressed：播放按钮 scale(0.9)（⚠️ 设计稿未定义）

---

### 7. TypingIndicator（AI 打字中指示器）

| 属性 | 值 |
|------|-----|
| 组件名称 | TypingIndicator |
| 作用 | 表示 AI 正在生成回复，提供可爱的视觉反馈 |
| 层级 | Z3，消息列表底部 |
| 宽度 | 约 72 pt（估算值） |
| 高度 | 约 48 pt（估算值） |
| 布局 | 左对齐，Flex Row 内部 3 圆点居中 |
| Padding | 约 16 pt 水平，12 pt 垂直（估算值） |
| 圆角 | 与 AITextBubble 相同（估算值） |
| 背景 | rgba(255,255,255,0.75) |

**圆点规格：**
- 数量：3 个
- 直径：约 10 pt（估算值）
- 颜色：#FFB7C5（樱花粉）
- 间距：约 6 pt（估算值）

**动画（⚠️ 设计稿未定义具体时序，建议参考 Motion Storyboard）：**
- 呼吸缩放：每个圆点交替 scale 0.6 → 1.0 → 0.6
- 错开延迟：dot1: 0ms, dot2: +150ms, dot3: +300ms（推荐值）
- 循环：infinite
- 动画时长：600ms per cycle（推荐值）

**状态：**
- Visible：AI 正在生成回复时显示（动画进行中）
- Hidden：AI 回复完成后淡出（⚠️ 设计稿未定义）

---

### 8. Composer（底部浮动输入框）

| 属性 | 值 |
|------|-----|
| 组件名称 | ChatComposer |
| 作用 | 用户输入文字消息、触发附加功能 |
| 层级 | Z4，fixed 定位在屏幕底部 |
| 宽度 | 约 358 pt（估算值，左右各 16 pt 间距） |
| 高度 | 约 64 pt（估算值） |
| 布局 | Flex Row，align-items: center，gap 10 pt，padding 12 pt 水平 |
| 背景 | rgba(255,255,255,0.65)，backdrop-filter: blur(24px)（估算值） |
| 圆角 | radius-2xl（约 32 pt，胶囊形，估算值） |
| 阴影 | shadow-composer |
| 位置 | bottom: 约 46 pt（含 Home Indicator 区域，估算值） |

**子组件：**

#### 8a. AttachButton（附加功能按钮"+"）
- 图标："+"
- 触摸区域：44 × 44 pt（实际圆形容器约 36 × 36 pt，估算值）
- 图标颜色：#BBBBBB（估算值）
- 背景：无填充或极淡灰（估算值）
- 状态：Default / Pressed（scale 0.9，opacity 70%，估算值）
- 功能：点击展开更多附加功能面板（⚠️ 设计稿未定义展开状态）

#### 8b. TextInput（文字输入框）
- 宽度：弹性（flex: 1，占据剩余宽度）
- 高度：约 40 pt（估算值）
- 背景：透明（无独立背景，继承 Composer 背景）
- Placeholder："想和小屿说点什么..."
- Placeholder 字号：约 15 pt（估算值）
- Placeholder 颜色：#BBBBBB
- 输入文字颜色：#3A3A4A
- 字号：约 15 pt（估算值）
- 支持多行输入（Composer 高度随内容增长，⚠️ 设计稿未定义多行状态）

#### 8c. SendButton（发送按钮）
- 尺寸：约 40 × 40 pt 圆形（估算值）
- 背景：#FFB7C5（樱花粉实色）
- 图标：纸飞机（Send Icon），约 18 pt，颜色 #FFFFFF
- 图标方向：向右上方 45° 倾斜
- 阴影：shadow-send-btn
- 状态：
  - Default（输入框为空）：显示发送按钮（⚠️ 设计稿中始终显示发送按钮，未显示空状态区别）
  - Active（有输入内容）：同 Default（估算值）
  - Pressed：scale(0.9)，opacity 80%（估算值）
  - Disabled：opacity 40%（⚠️ 设计稿未定义）

**状态总览：**
- Default（空输入）：如图，Placeholder 可见，发送按钮可见
- Focused（键盘弹出）：Composer 随键盘上移（⚠️ 设计稿未定义键盘弹出状态）
- Has Input：Placeholder 消失，发送按钮激活（⚠️ 设计稿未定义）

---

### 9. HomeIndicator（系统 Home Bar）

| 属性 | 值 |
|------|-----|
| 组件名称 | HomeIndicator |
| 作用 | iOS 系统 Home 区域指示条，提示用户可上滑返回主屏 |
| 层级 | Z5 |
| 尺寸 | 约 134 × 5 pt（估算值） |
| 颜色 | #3A3A4A（深色） |
| 圆角 | radius-full |
| 位置 | 底部居中，距底边约 8 pt（估算值） |
| 背景 | 系统控制，不干预 |

---

### 10. BackgroundLayer（背景层）

| 属性 | 值 |
|------|-----|
| 组件名称 | ChatBackground |
| 作用 | 提供页面视觉氛围基底，营造梦幻治愈氛围 |
| 层级 | Z0 |
| 尺寸 | 满屏 390 × 844 pt |
| 布局 | 绝对定位，pointer-events: none |

**层叠：**
1. 主线性渐变：顶部 #FFF0EC → 底部 #E8D5F5（估算值）
2. 中央椭圆白色光晕：宽约 280 pt，高约 200 pt，opacity 40%（估算值）
3. 右下薰衣草光晕：宽约 200 pt，高约 200 pt，opacity 30%（估算值）

---

## 可复用组件建议

以下组件建议封装为设计系统中的可复用组件：

| 组件 | 复用理由 |
|------|---------|
| `AITextBubble` | 在所有聊天场景（暗色/浅色/其他角色）中复用，仅需换 props |
| `UserTextBubble` | 与 AITextBubble 对称，复用相同基础 Bubble 组件，通过 `align` prop 区分 |
| `AIVoiceBubble` | Voice 功能为 yuoyuo 核心特色，此组件将在多处使用（语音消息列表等） |
| `TypingIndicator` | 任何 AI 回复生成中状态均可复用 |
| `ChatComposer` | 全局 Composer 组件，可复用于所有聊天页（不同角色共用） |
| `ChatHeader` | 与角色名/头像/状态解耦，通过 props 注入角色数据 |
| `DateSeparator` | 通用日期分隔符，可复用于历史消息列表 |
| `WaveformVisualizer` | 波形组件可独立复用于语音录制反馈界面 |
