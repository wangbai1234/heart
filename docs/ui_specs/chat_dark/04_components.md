# 04 Components — 聊天页 Chat（深色模式）

## 组件清单概览
1. StatusBar（系统状态栏）
2. ChatHeader（聊天顶部导航栏）
3. BackButton（返回按钮）
4. AvatarWithGlow（AI 角色头像）
5. AgentNameStatus（角色名称与在线状态）
6. MoreButton（更多操作按钮）
7. TimestampDivider（时间戳分隔）
8. AITextBubble（AI 文字消息气泡）
9. UserTextBubble（用户文字消息气泡）
10. AIVoiceBubble（AI 语音消息气泡）
11. PlayButton（语音播放按钮）
12. WaveformVisualizer（语音波形可视化）
13. DurationLabel（语音时长标签）
14. AIReadingHint（AI 朗读提示文字）
15. TypingIndicatorBubble（AI 输入中气泡）
16. TypingDots（三点动效）
17. ChatInputBar（底部输入栏）
18. PlusButton（附加功能按钮）
19. TextInput（文字输入框）
20. SendButton（发送按钮）
21. HomeIndicator（系统底部指示条）
22. StarDecorations（背景星星装饰）
23. NebulaBackground（星云背景）

---

## 1. StatusBar 系统状态栏

- **作用**：展示系统时间、信号强度、WiFi、电量
- **层级**：Z-index 20（最顶层）
- **尺寸**：1024 × ~88 px（估算值）
- **布局**：Flex Row，Space-between
- **状态**：仅有 Default
- **样式细节**：
  - 背景透明，透出页面背景
  - 左侧"9:41"：SF Pro Rounded，~24 px（估算值），SemiBold，#FFFFFF
  - 右侧图标组：信号格（4格满格），WiFi（满格），电池（约3/4电量）均为白色
  - 图标尺寸：约 20-24 px（估算值）
- **交互**：系统接管，无自定义交互
- **可复用**：否（系统组件）

---

## 2. ChatHeader 聊天顶部导航栏

- **作用**：展示返回按钮、AI 角色信息、更多按钮；提供导航功能
- **层级**：Z-index 10，固定于顶部
- **尺寸**：1024 × ~140 px（估算值）
- **布局**：Flex Row，AlignItems: center，Space-between，Padding: ~20 px 上下，~40 px 左右（估算值）
- **背景**：毛玻璃 `rgba(30,27,40,0.75)`，backdrop-filter: blur(20px)
- **边框**：无明显上/左/右边框；底部有约 32 px 圆角
- **状态**：Default（透明感导航栏），Scroll-active（用户滚动后可能加深背景透明度）
- **样式细节**：
  - 整体有微弱底部阴影 `rgba(0,0,0,0.20)` blur 12 px
  - 子组件从左到右：BackButton + AvatarWithGlow + AgentNameStatus + MoreButton

---

## 3. BackButton 返回按钮

- **作用**：返回上一页（对话列表/主页）
- **层级**：在 ChatHeader 内
- **尺寸**：触摸区域约 60 × 60 px（估算值），图标约 24 px 高
- **布局**：Flex，Center，圆形热区
- **状态**：
  - Default："<"白色箭头，透明背景
  - Pressed：背景出现 `rgba(255,255,255,0.12)` 圆形，缩放 0.92
  - Hover（iPad）：背景圆形加深
- **样式细节**：
  - 图标"<"为 Chevron Left，颜色 #FFFFFF，线条宽度约 2.5 px（估算值）
  - 无文字标签
- **交互**：点击触发 Pop 导航动画返回
- **可复用**：是（通用 NavigationBackButton 组件）

---

## 4. AvatarWithGlow AI 角色头像

- **作用**：展示 AI 角色小屿的头像，视觉识别角色
- **层级**：在 ChatHeader 内
- **尺寸**：约 100 × 100 px（估算值），圆形裁剪
- **布局**：圆形 clip，overflow: hidden
- **状态**：
  - Default：展示静态头像图
  - Pressed：轻微缩放 0.95（推测）
- **样式细节**：
  - 内容：二次元风格少女，紫色长发，白色花饰，紫色眼睛，淡色背景（头像本身带背景）
  - 边框：轻微粉色/白色光晕效果 `box-shadow: 0 0 12px rgba(255,183,197,0.50)`（估算值）
  - 无明显边框线条，依靠光晕与背景区分
- **交互**：点击可能进入角色详情页（推测）
- **可复用**：是（Avatar 组件，支持 src/size/glow 属性）

---

## 5. AgentNameStatus 角色名称与在线状态

- **作用**：展示 AI 角色名"小屿"及当前状态"温柔在线"
- **层级**：在 ChatHeader 内，头像右侧
- **尺寸**：宽度 flex:1，高度自适应（约 70 px，估算值）
- **布局**：Flex Column，Gap ~6 px，AlignItems: flex-start
- **状态**：在线/离线（dot 颜色变化）
- **样式细节**：
  - 名称"小屿"：PingFang SC，约 32 px（估算值），SemiBold，#FFFFFF
  - 状态行：Flex Row，AlignItems: center，Gap ~6 px
  - 状态圆点：约 10 × 10 px 圆形，颜色 `#7EB8F7`（蓝色在线状态）
  - 状态文字"温柔在线"：PingFang SC，约 22 px（估算值），Regular，`rgba(255,255,255,0.70)`
- **交互**：无直接交互（仅展示）
- **可复用**：是（AgentInfo 组件）

---

## 6. MoreButton 更多操作按钮

- **作用**：展开更多操作菜单（设置/清除聊天/举报等）
- **层级**：在 ChatHeader 内，最右侧
- **尺寸**：触摸区域约 60 × 60 px（估算值）
- **布局**：Flex，Center
- **状态**：
  - Default：三个白色圆点"···"
  - Pressed：背景出现 `rgba(255,255,255,0.12)` 圆形，缩放 0.92
  - Active（菜单展开时）：图标可能高亮
- **样式细节**：
  - 图标："···"三点，水平排列，颜色 #FFFFFF，圆点约 5 px 直径（估算值），间距约 4 px（估算值）
- **交互**：点击展开 Bottom Sheet 或弹出菜单
- **可复用**：是（IconButton 组件，icon 为 more-horizontal）

---

## 7. TimestampDivider 时间戳分隔

- **作用**：将聊天记录按时间分组，提供时间上下文
- **层级**：在消息列表内，消息气泡之间
- **尺寸**：宽度 100%，高度自适应（约 40 px 含上下 margin，估算值）
- **布局**：Flex，Center，水平居中
- **状态**：仅 Default
- **样式细节**：
  - 文字"今天 · 上午 9:41"：PingFang SC，约 22 px（估算值），Regular，`rgba(255,255,255,0.45)`
  - 无背景、无边框
  - 上下 margin：上 ~32 px，下 ~24 px（估算值）
- **交互**：无
- **可复用**：是（TimestampDivider 组件）

---

## 8. AITextBubble AI 文字消息气泡

- **作用**：展示 AI 角色发送的文字消息
- **层级**：在消息列表内，左对齐
- **尺寸**：宽度动态（最大约 680 px，估算值），高度随内容
- **布局**：左对齐，内边距约 24 px 上下，32 px 左右（估算值）
- **状态**：
  - Default：展示消息文字
  - Pressed/Long-press：触发上下文菜单（复制/朗读等）
- **样式细节**：
  - 背景：`rgba(45,40,65,0.90)`（深紫半透明）
  - 圆角：约 32 px，左下角较小约 8-12 px（气泡尾角，估算值）
  - 边框：`1px solid rgba(255,160,190,0.18)`（粉色边缘光边框）
  - 外发光：`box-shadow: 0 0 20px rgba(255,183,197,0.25)`（粉色辉光）
  - 文字：PingFang SC，约 28 px（估算值），Regular，`#F0EEFF`
  - 行高：约 1.5
- **交互**：长按触发菜单；双击可能触发情感反应（推测）
- **可复用**：是（核心组件，支持 sender/content 属性）

---

## 9. UserTextBubble 用户文字消息气泡

- **作用**：展示用户发送的文字消息
- **层级**：在消息列表内，右对齐
- **尺寸**：宽度动态（最大约 580 px，估算值），高度随内容
- **布局**：右对齐，内边距约 24 px 上下，32 px 左右（估算值）
- **状态**：
  - Default：展示消息文字
  - Pressed/Long-press：触发上下文菜单
- **样式细节**：
  - 背景：Linear Gradient 135deg，`#3B5BDB` → `#2F4AC5`（靛蓝渐变）
  - 圆角：约 32 px，右下角较小约 8-12 px（气泡尾角，估算值）
  - 无明显边框
  - 轻微外发光（蓝色方向）：`box-shadow: 0 4px 16px rgba(59,91,219,0.30)`（估算值）
  - 文字：PingFang SC，约 28 px（估算值），Regular，#FFFFFF
  - 行高：约 1.5
- **可复用**：是（与 AITextBubble 同族，通过 sender 属性区分）

---

## 10. AIVoiceBubble AI 语音消息气泡

- **作用**：展示 AI 语音 TTS 消息，用户可点击播放收听
- **层级**：在消息列表内，左对齐
- **尺寸**：宽度约 640 px（估算值），高度约 160 px（估算值）
- **布局**：
  - 外层：与 AITextBubble 相同样式的气泡容器
  - 内层 Row1：PlayButton + WaveformVisualizer + DurationLabel（Flex Row，AlignItems: center，Gap ~16 px）
  - 内层 Row2：AIReadingHint（文字标签，左对齐）
  - 两行间距约 16 px（估算值）
- **状态**：
  - Default（未播放）：PlayButton 显示三角形，波形为静态彩色
  - Playing：PlayButton 显示暂停符号，波形动态律动
  - Paused：同 Default 状态但进度保留
  - Error：播放失败提示（⚠️ 设计稿未定义，建议参考 Motion Storyboard）
- **样式细节**：
  - 背景、边框、圆角、发光同 AITextBubble
  - 内部布局更复杂
- **可复用**：是（AIVoiceBubble 为独立组件）

---

## 11. PlayButton 语音播放按钮

- **作用**：触发/暂停语音 TTS 播放
- **层级**：在 AIVoiceBubble 内
- **尺寸**：约 72 × 72 px（估算值），圆形
- **布局**：Flex，Center
- **状态**：
  - Default（播放）：三角形播放图标
  - Playing（暂停）：两条竖线图标
- **样式细节**：
  - 背景：`rgba(255,183,197,0.25)`（粉色半透明圆形）
  - 图标颜色：`#FFB7C5`（樱花粉）
  - 图标尺寸：三角形约 24 × 24 px（估算值）
  - 无边框
  - 按压：缩放 0.90，背景加深
- **交互**：点击触发播放/暂停
- **可复用**：是（PlayPauseButton 通用组件）

---

## 12. WaveformVisualizer 语音波形可视化

- **作用**：视觉化展示语音内容的振幅，装饰性 + 功能性（可指示播放进度）
- **层级**：在 AIVoiceBubble 内，PlayButton 右侧
- **尺寸**：宽约 380 px，高约 60 px（估算值）
- **布局**：Flex Row，等间距竖条形（约 24-28 条，估算值）
- **状态**：
  - Default（静态）：所有竖条显示为多彩渐变
  - Playing：已播放部分高亮/亮色，未播放部分略暗
- **样式细节**：
  - 竖条颜色：Linear Gradient，左 `#FFB7C5` 粉 → 中 `#C8B6FF` 紫 → 右 `#A7C7E7` 蓝（估算值）
  - 竖条高度：不等高，模拟真实波形振幅（最高约 52 px，最低约 12 px，估算值）
  - 竖条宽度：约 5-6 px（估算值）
  - 竖条间距：约 3-4 px（估算值）
  - 竖条圆角：约 3 px（估算值）
- **交互**：点击波形特定位置可跳转播放进度（推测）
- **可复用**：是（WaveformVisualizer，props: bars/progress）

---

## 13. DurationLabel 语音时长标签

- **作用**：展示语音消息总时长或剩余时长
- **层级**：在 AIVoiceBubble 内，WaveformVisualizer 右侧
- **尺寸**：约 60 × 30 px（估算值）
- **布局**：Flex，Center
- **样式细节**：
  - 文字"0:18"：SF Pro Rounded，约 26 px（估算值），Regular，`rgba(255,255,255,0.60)`
- **可复用**：是（属于 AIVoiceBubble 内部元素）

---

## 14. AIReadingHint AI 朗读提示

- **作用**：说明该消息可以收听，引导用户交互
- **层级**：在 AIVoiceBubble 内，第二行
- **尺寸**：自适应文字宽度
- **样式细节**：
  - 文字"AI朗读 · 可点击播放"：PingFang SC，约 22 px（估算值），Regular，`rgba(255,255,255,0.45)`
- **可复用**：是（AIVoiceBubble 内部标签）

---

## 15. TypingIndicatorBubble AI 输入中气泡

- **作用**：表示 AI 正在"思考/打字"，增加临场感和 AI 生命感
- **层级**：在消息列表底部，左对齐
- **尺寸**：宽约 160 px，高约 80 px（估算值）
- **布局**：与 AITextBubble 相同容器样式，内含 TypingDots
- **状态**：
  - Active（AI 思考中）：三点动效显示
  - Hidden（AI 回复后）：组件消失
- **样式细节**：
  - 背景、边框、圆角、发光同 AITextBubble
  - 内部居中显示三个圆点
- **可复用**：是（TypingIndicator 组件）

---

## 16. TypingDots 三点动效

- **作用**：动态展示 AI 思考中状态
- **层级**：在 TypingIndicatorBubble 内
- **尺寸**：三个圆点，每个约 14 × 14 px，间距约 8 px（估算值）
- **布局**：Flex Row，居中
- **样式细节**：
  - 圆点颜色：`#FFB7C5`（樱花粉）
  - 动效：三点依次上下弹跳（wave animation）
  - 循环时长：约 800ms，各点延迟 120ms（估算值）
- **可复用**：是（TypingDots 独立组件）

---

## 17. ChatInputBar 底部输入栏

- **作用**：用户文字输入区域，含功能扩展和发送操作
- **层级**：Z-index 10，固定于底部
- **尺寸**：1024 × ~120 px（估算值）（不含 Safe Area bottom）
- **布局**：Flex Row，AlignItems: center，Padding: ~16 px 上下，~24 px 左右（估算值），Gap: ~16 px
- **背景**：`rgba(30,27,40,0.80)`，backdrop-filter: blur(20px)
- **状态**：
  - Default（空输入框）：展示占位文字，发送按钮可为禁用态
  - Focus（键盘弹出）：输入栏上移，配合键盘位置
  - Has-content：发送按钮激活为粉色
- **可复用**：是（ChatInputBar 整体可复用，子组件独立）

---

## 18. PlusButton "+"附加功能按钮

- **作用**：展开附加功能面板（图片/表情/更多）
- **层级**：在 ChatInputBar 内，最左侧
- **尺寸**：约 80 × 80 px（估算值），圆形
- **布局**：Flex，Center
- **状态**：
  - Default："+"图标
  - Active（面板展开）："×"图标（推测）
  - Pressed：背景加深，缩放 0.92
- **样式细节**：
  - 背景：`rgba(255,255,255,0.12)`（白色半透明圆形）
  - 图标"+"：约 28 px，#FFFFFF，线条约 2.5 px（估算值）
  - 无边框
- **可复用**：是（IconCircleButton 组件）

---

## 19. TextInput 文字输入框

- **作用**：接收用户文字输入
- **层级**：在 ChatInputBar 内
- **尺寸**：flex:1，高约 80 px（估算值）
- **布局**：内边距左右 ~24 px（估算值）
- **状态**：
  - Default：显示占位文字
  - Focus：光标闪烁，键盘弹出
  - Has-content：文字替代占位，发送按钮变化
- **样式细节**：
  - 背景：`rgba(255,255,255,0.08)`
  - 圆角：胶囊形（约 40 px，估算值）
  - 占位文字："想和小屿说点什么..."，`rgba(255,255,255,0.40)`
  - 文字颜色：#FFFFFF
  - 字号：约 28 px（估算值）
  - 无明显边框
- **可复用**：是（ChatTextInput 组件）

---

## 20. SendButton 发送按钮

- **作用**：发送用户输入的消息
- **层级**：在 ChatInputBar 内，最右侧
- **尺寸**：约 84 × 84 px（估算值），完整圆形
- **布局**：Flex，Center
- **状态**：
  - Default/Empty：可能为半透明灰色（设计稿未明确显示空态）
  - Has-content：`#FFB7C5` 粉色背景，白色纸飞机图标
  - Pressed：缩放 0.90，背景加深
  - Loading（发送中）：旋转动效（推测）
- **样式细节**：
  - 背景：`#FFB7C5`（樱花粉）
  - 圆形 `border-radius: 50%`
  - 外发光：`box-shadow: 0 4px 16px rgba(255,183,197,0.40)`（粉色辉光）
  - 图标：纸飞机/箭头，#FFFFFF，约 32 px（估算值），向右上方倾斜
- **可复用**：是（SendButton 组件，props: disabled/loading）

---

## 21. HomeIndicator 系统底部指示条

- **作用**：iOS 系统 Home Gesture 指示条
- **尺寸**：约 280 × 5 px（估算值），圆角 3 px
- **样式**：`rgba(255,255,255,0.30)` 白色半透明
- **可复用**：否（系统组件）

---

## 22. StarDecorations 背景星星装饰

- **作用**：增加星夜氛围，装饰性元素
- **层级**：背景层内
- **尺寸**：每个星点约 2-4 px（估算值），散布全屏
- **样式**：白色或淡蓝色小圆点/四角星，`opacity: 0.40-0.80`（估算值）
- **可复用**：是（作为 BackgroundLayer 的子层）

---

## 23. NebulaBackground 星云背景

- **作用**：营造深色星夜氛围，是整个深色模式的视觉基础
- **层级**：Z-index 0（最底层）
- **尺寸**：全屏 1024 × 1536 px
- **样式**：
  - 底色：`#1B1923`（深紫黑）
  - 右下角及中下部：大片紫色云雾纹理，`rgba(80,50,120,0.35)`（估算值），blur ~40 px
  - 星点装饰散布其间
- **可复用**：是（ChatDarkBackground 组件，可接受 intensity 参数）

---

## 可复用组件建议

以下组件应封装为独立可复用组件，原因如下：

| 组件 | 复用原因 |
|------|---------|
| `Avatar` | 全应用多处需要展示角色/用户头像，支持 src/size/shape/glow |
| `AITextBubble` / `UserTextBubble` | 核心聊天组件，所有对话页共享 |
| `AIVoiceBubble` | 语音功能核心，可能复用于多个场景 |
| `TypingIndicator` | 所有 AI 对话页均需要 |
| `ChatInputBar` | 所有聊天页底部固定组件 |
| `SendButton` | 可跨场景复用（表单/聊天） |
| `TimestampDivider` | 所有对话页均需时间分组 |
| `WaveformVisualizer` | 音频相关功能（录音/播放）复用 |
| `NebulaBackground` | 作为深色主题背景组件，可跨页面复用 |
| `PlayPauseButton` | 音频控制复用 |
