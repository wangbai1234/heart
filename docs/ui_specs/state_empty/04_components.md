# 04 Components — 加载 / 空状态

## 组件总览

本页面共包含以下组件（按区域分组）：

**空聊天状态区（上半）：**
1. StatusBar（状态栏）
2. ChatHeader（聊天顶栏）
3. EmptyIllustration（空状态插画区）
4. GuideText（引导文字）
5. SuggestionPillsRow（建议 Pill 行）
6. SuggestionPill（建议 Pill，可复用，共 3 个实例）

**加载/骨架状态区（下半）：**
7. StatusBar（同上，复用）
8. ChatHeader — Loading Variant（顶栏加载变体）
9. SkeletonBubble — Left（左对齐骨架气泡，AI 消息）
10. SkeletonBubble — Right（右对齐骨架气泡，用户消息）
11. SkeletonAvatarPlaceholder（骨架头像占位圆）
12. SkeletonMessageBar（骨架消息矩形条）
13. InputBar（底部输入栏）

---

## 组件 1：StatusBar（状态栏）

| 属性 | 值 |
|------|-----|
| 名称 | StatusBar |
| 作用 | 显示系统时间、网络状态、电量 |
| 层级 | 最顶层，Z-index: 10 |
| 尺寸（设计稿） | 1024 × 60 px（估算） |
| 布局 | 水平 Row，两端对齐（Space Between） |
| 背景 | 透明，继承页面背景 |

**子元素：**
- 左：时间文字"9:41"，字号约 28 px，Semibold，颜色 #3A3A4A
- 右：信号格图标 + Wi-Fi 图标 + 电池图标，颜色 #3A3A4A，间距约 12 px

**状态：**
- 仅一种视觉状态（系统原生渲染）

**可复用性：** 全局复用，上下两个区域均使用相同规格。

---

## 组件 2：ChatHeader（聊天顶栏）

| 属性 | 值 |
|------|-----|
| 名称 | ChatHeader |
| 作用 | 显示角色信息、提供返回/操作入口 |
| 层级 | Z-index: 10 |
| 尺寸（设计稿） | 1024 × 100 px（估算） |
| 布局 | 水平 Row，左侧 Flex+1，右侧固定 |
| Padding Horizontal | 约 40 px |
| Padding Vertical | 约 16 px |
| 背景 | 继承页面背景，无分割线 |

**左侧组合（从左到右）：**

| 子组件 | 类型 | 尺寸 | 颜色 | 交互 |
|--------|------|------|------|------|
| BackButton "<" | Icon Button | 48×48 px | #8A8A9A | Tap → 返回上一页 |
| CharacterAvatar | Image/Avatar | 直径 88 px | — | Tap → 角色详情（可选）|
| CharacterInfo | Column | — | — | — |
| — CharacterName | Text | 字号 ~32 px | #3A3A4A | — |
| — StatusText | Text | 字号 ~22 px | #A07888 | — |

**右侧组合（从右到左）：**

| 子组件 | 类型 | 尺寸 | 颜色 | 交互 |
|--------|------|------|------|------|
| MoreMenuButton "···" | Icon Button | 48×48 px | #8A8A9A | Tap → 展开菜单 |
| PhoneButton | Icon Button | 44×44 px | #8A8A9A | Tap → 触发语音通话 |

**两个状态（Variants）：**

| Variant | StatusText 内容 | StatusText 样式 |
|---------|----------------|----------------|
| `default` | "在线 · 愿意倾听你的一切" | 静态文字，颜色 #A07888 |
| `loading` | "···"（打点动画） | 动画文字或三个点顺序淡入，颜色同上 |

**可复用性：** 全局聊天页 Header 复用，通过 Variant 切换状态显示。

---

## 组件 3：EmptyIllustration（空状态插画区）

| 属性 | 值 |
|------|-----|
| 名称 | EmptyIllustration |
| 作用 | 空聊天状态的视觉焦点，传递温暖治愈的第一印象 |
| 层级 | Z-index: 2 |
| 尺寸（设计稿） | 约 700 × 380 px（估算，含光晕） |
| 布局 | 中心对齐，云朵为背景，心形在前 |

**子元素：**

| 子元素 | 类型 | 尺寸（设计稿） | 描述 |
|--------|------|-------------|------|
| CloudGlow | 渐变/插画背景 | ~600×280 px | 粉紫云朵，放射状渐变，柔化 24px blur |
| GemHeart | 插画图片资产 | ~240×220 px | 二次元宝石心形，多层渐变+高光，粉/紫/蓝 |

**状态：**
- `static`：静态展示（设计稿所示）
- `animated`：心形轻微浮动（pulse 动画，Y 轴 ±6px，周期 2s，设计稿未定义，推荐实现）

**可复用性：** 专用于空聊天状态，不跨页面复用。

---

## 组件 4：GuideText（引导文字）

| 属性 | 值 |
|------|-----|
| 名称 | GuideText |
| 作用 | 引导用户发起第一条消息 |
| 层级 | Z-index: 2 |
| 尺寸 | 自动宽度，高度约 44 px |
| 字体 | PingFang SC Medium |
| 字号（设计稿） | 约 36 px（估算） |
| 颜色 | #3A3A4A |
| 对齐 | 水平居中 |
| 内容 | "我们刚认识，先聊点什么吧？" |

**状态：** 仅一种（静态）

**可复用性：** 可抽象为 `EmptyStateGuideText` 组件，支持 `text` prop 配置内容。

---

## 组件 5：SuggestionPillsRow（建议 Pill 行）

| 属性 | 值 |
|------|-----|
| 名称 | SuggestionPillsRow |
| 作用 | 承载多个 SuggestionPill 的水平容器 |
| 层级 | Z-index: 2 |
| 布局 | Horizontal Row，Gap 约 16 px，整体居中 |
| 高度 | 约 64 px |

**可复用性：** 可与 SuggestionPill 组合使用，通过数组 prop 动态渲染。

---

## 组件 6：SuggestionPill（建议 Pill）

| 属性 | 值 |
|------|-----|
| 名称 | SuggestionPill |
| 作用 | 点击后自动填入输入框并发送该建议文字 |
| 层级 | Z-index: 2 |
| 布局 | 水平 Row，图标 + 文字，Padding H: ~24px |
| 高度 | 约 64 px（估算） |
| 圆角 | 约 32 px（胶囊形） |
| 背景 | 白色或极浅玫瑰白，约 rgba(255,255,255,0.80)（估算） |
| 边框 | 约 1.5 px 描边，颜色约 rgba(255,183,197,0.40)（估算） |
| 阴影 | 约 0 2px 8px rgba(255,183,197,0.25) |

**子元素：**
- 左：小图标（16–20 px，描边风格）
- 右：文字标签（字号约 26 px，颜色 #3A3A4A 或 #A07888）

**三个实例：**

| 实例 | 图标 | 图标色 | 文字 |
|------|------|-------|------|
| Pill 1 | 笑脸圆圈 | #FFB7C5 | "今天心情如何？" |
| Pill 2 | 对话气泡 | #FFB7C5 | "陪我说话" |
| Pill 3 | 五角星 | #E8C84A | "给我讲个故事" |

**状态（States）：**

| State | 视觉变化 |
|-------|---------|
| `default` | 如上所述 |
| `pressed` | 背景略深，轻微缩放 scale(0.96)，阴影消失 |
| `disabled` | 透明度降至 0.4（如适用） |

**交互：**
- Tap → 将 Pill 文字填入输入框，触发消息发送，进入加载状态
- 动画：轻微弹性缩放（spring easing）

**可复用性：** 高度复用。可在任意"Empty State / Onboarding"页面使用。

---

## 组件 7：SkeletonBubble（骨架气泡，通用）

| 属性 | 值 |
|------|-----|
| 名称 | SkeletonBubble |
| 作用 | 在 AI 响应加载期间，维持聊天界面的结构感 |
| 层级 | Z-index: 2 |

**Variants：**

### SkeletonBubble — Left（AI 发言，左对齐）

| 属性 | 值 |
|------|-----|
| 布局 | Row：[SkeletonAvatar] + [SkeletonMessageBar] |
| 对齐 | 左对齐，Row 顶部对齐 |
| Padding Left | 约 40 px |
| 间距（Avatar → Bar） | 约 16 px |

### SkeletonBubble — Right（用户发言，右对齐）

| 属性 | 值 |
|------|-----|
| 布局 | Row：[SkeletonMessageBar] + [SkeletonAvatar] |
| 对齐 | 右对齐，Row 顶部对齐 |
| Padding Right | 约 40 px |
| 间距（Bar → Avatar） | 约 16 px |

**动画状态：**
- `shimmer`：Shimmer 扫光动画持续循环（linear，1400ms，infinite）
- `revealed`：淡出过渡（fade-out 300ms），由真实气泡替代

---

## 组件 8：SkeletonAvatarPlaceholder（骨架头像占位圆）

| 属性 | 值 |
|------|-----|
| 名称 | SkeletonAvatarPlaceholder |
| 尺寸 | 直径约 72 px（AI）/ 60 px（用户）（估算） |
| 形状 | 完整圆形（border-radius: 50%） |
| 颜色 | #F2C8D0（估算，浅玫瑰） |
| Shimmer | 包含扫光动画层 |

---

## 组件 9：SkeletonMessageBar（骨架消息矩形）

| 属性 | 值 |
|------|-----|
| 名称 | SkeletonMessageBar |
| 尺寸 | 宽度不固定（约 420–480 px），高度约 48–56 px |
| 圆角 | 约 14–16 px |
| 颜色 | #F2D0D8（估算） |
| Shimmer | 包含扫光动画层（内部 pseudo-element 水平扫光） |

**多行变体（SkeletonMessageBar — Multiline）：**
- 垂直堆叠两个 SkeletonMessageBar
- 第二行宽度约为第一行 70%（制造不等宽效果，更自然）
- 两行间距约 12 px

---

## 组件 10：InputBar（底部输入栏）

| 属性 | 值 |
|------|-----|
| 名称 | InputBar |
| 作用 | 用户输入消息的主要入口 |
| 层级 | Z-index: 10 |
| 尺寸 | 全宽 × 约 116 px（含 safe area bottom） |
| 背景 | 与页面背景一致或极浅磨砂 |
| 布局 | Row：[AddButton] + [InputField] + [MicButton] |
| Padding Horizontal | 约 40 px |

**子组件：**

| 子组件 | 类型 | 尺寸 | 样式 |
|--------|------|------|------|
| AddButton "+" | Icon Button | 直径 64 px | 描边圆形，颜色 #A8A8B8（估算）|
| InputField | Text Input | Flex+1，高度约 64 px | 透明背景，占位文字颜色 #C8B6C8 |
| MicButton | Icon Button | 直径 64 px | 描边圆形，图标颜色 #FFB7C5 |

**状态：**

| State | 描述 |
|-------|------|
| `empty` | 展示占位文字，Mic 按钮显示（如图所示） |
| `typing` | 占位文字消失，Mic 按钮切换为发送按钮 |
| `disabled` | 骨架加载期间输入栏是否可交互（设计稿未明确，建议可交互）|

**可复用性：** 全局聊天页底部复用。
