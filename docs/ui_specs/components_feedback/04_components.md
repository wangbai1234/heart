# 04 Components — 逐组件规范

## 组件总览

本资产包含以下可复用组件：

1. `Toast` — 顶部通知气泡
2. `ModalCard` — 居中确认弹窗
3. `BottomSheet` — 底部选项表单
4. `RadioOption` — 单选选项行（Sheet 内子组件）
5. `PrimaryButton` — 主操作按钮（共用）
6. `SecondaryButton` — 次操作按钮（Modal 专用）
7. `ScrimOverlay` — 遮罩层（Modal/Sheet 共用）
8. `ChatNavBar` — 聊天页导航栏（背景宿主）
9. `ChatInputBar` — 底部输入栏（背景宿主）
10. `DragHandle` — Sheet 拖动条

---

## 1. Toast — 顶部通知气泡

### 基本信息
- **名称**: `Toast`
- **作用**: 轻量、短暂的操作成功/失败/信息通知，不打断用户主流程
- **层级**: z-index 最高（300），位于所有覆盖层之上

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 宽度 | ≈330px（水平居中，边距各约 22px，估算值） |
| 高度 | ≈44px（估算值） |
| 圆角 | `22px`（胶囊形全圆角） |
| 内部 padding | `0 16px`（估算值） |
| 图标与文字间距 | `≈10px`（估算值） |
| 图标尺寸 | `≈20px × 20px`（估算值） |

### 视觉样式
| 属性 | 值 |
|------|-----|
| 背景色 | `#FFFFFF` |
| 阴影 | `0 4px 16px rgba(0,0,0,0.10)` |
| 左侧图标 | 圆形粉色背景（`#FFB7C5`）内白色勾选（✓） |
| 文字颜色 | `#3A3A4A` |
| 文字内容 | "兑换成功，会员已激活。" |
| 文字字号 | `14px` |
| 文字粗细 | `Regular（400）` |

### 位置
- 水平居中于屏幕
- 顶部：导航栏底部 + `16px` 间距（估算值）
- 不使用 safe-area offset（悬浮于内容区之上）

### 所有状态
| 状态 | 描述 |
|------|------|
| `success` | 粉色勾选图标（当前设计稿显示） |
| `error` | 红色/警告图标（设计稿未展示，需扩展） |
| `info` | 信息图标（设计稿未展示，需扩展） |
| `loading` | 加载旋转图标（设计稿未展示，需扩展） |

### 交互
- 出现：从顶部滑入 + 渐显，持续 `300ms`
- 停留：`2500ms`
- 退出：向上滑出 + 渐隐，持续 `200ms`
- 用户可上滑提前关闭（推荐，设计稿未标注但为惯例）

---

## 2. ModalCard — 居中确认弹窗

### 基本信息
- **名称**: `ModalCard`
- **作用**: 破坏性或需要二次确认的操作，强制用户明确选择（确认/取消）
- **层级**: z-index 200，ScrimOverlay 之上

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 宽度 | ≈306px（估算值） |
| 高度 | ≈280px（估算值，自适应内容） |
| 圆角 | `20px` |
| 内部 padding | `24px`（四周，估算值） |
| 位置 | 屏幕水平居中、垂直居中（距 NavBar 底部偏上） |

### 视觉样式
| 属性 | 值 |
|------|-----|
| 背景色 | `#FFFFFF` |
| 阴影 | `0 8px 32px rgba(0,0,0,0.18)` |
| 描边 | 无（纯白卡片） |

### 内部结构（从上到下）
```
ModalCard
│
├── IllustrationArea（高≈64px，居中）
│   └── 云朵插图（含粉色爱心光效，≈48×48px，估算值）
│
├── Title（margin-top ≈16px）
│   └── Text: "确认退出登录？"
│       font: 20px SemiBold, #3A3A4A, text-align: center
│
├── Body（margin-top ≈8px）
│   └── Text: "退出后需要重新通过邮箱链接登录。"
│       font: 13px Regular, #888888, text-align: center, line-height: 1.5
│
├── PrimaryButton（margin-top ≈20px）
│   └── "确认退出"（粉色渐变，白字）
│
└── SecondaryButton（margin-top ≈12px）
    └── "取消"（白色背景，深色描边，深色字）
```

### 所有状态
| 状态 | 描述 |
|------|------|
| `default` | 如设计稿所示 |
| `loading` | 确认退出按钮显示加载态（设计稿未展示） |
| `disabled` | 按钮禁用（设计稿未展示） |

### 可复用性
- `ModalCard` 为通用容器，内容（图标、标题、说明、按钮文字）通过 props 传入
- 图标区可接受自定义插图或 emoji
- 可扩展为单按钮（仅确认）或三按钮（高优先级/低优先级/取消）布局

---

## 3. BottomSheet — 底部选项表单

### 基本信息
- **名称**: `BottomSheet`
- **作用**: 从底部弹出的操作面板，用于单选/多选配置，不完全遮挡背景内容
- **层级**: z-index 200，ScrimOverlay 之上

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 宽度 | `100%`（全屏宽，贴合设备宽度） |
| 高度 | ≈320px（估算值，约占屏幕高度 40%） |
| 顶部圆角 | `20px` |
| 底部圆角 | `0px`（贴合底部 safe area） |
| 内部 padding | `0 20px 24px 20px`（估算值，底部含 safe-area） |
| 位置 | 吸附屏幕底部 |

### 视觉样式
| 属性 | 值 |
|------|-----|
| 背景色 | `#FFFFFF` |
| 阴影 | `0 -4px 20px rgba(0,0,0,0.10)` |

### 内部结构（从上到下）
```
BottomSheet
│
├── DragHandle（顶部居中，margin-top ≈12px）
│   └── 圆角矩形 ≈36×4px，颜色 #D0D0D0
│
├── SheetTitle（margin-top ≈16px）
│   └── Text: "选择主题"
│       font: 17px SemiBold, #3A3A4A, text-align: left
│
├── RadioGroup（margin-top ≈16px）
│   ├── RadioOption: "浅色"（已选中）
│   ├── RadioOption: "深色"（未选中）
│   └── RadioOption: "跟随系统"（未选中）
│
└── PrimaryButton（margin-top ≈20px）
    └── "完成"（全宽，粉色渐变）
```

---

## 4. RadioOption — 单选选项行

### 基本信息
- **名称**: `RadioOption`
- **作用**: BottomSheet 内的单选列表项
- **层级**: BottomSheet 内子组件

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 高度 | ≈44px（标准触摸目标，估算值） |
| 宽度 | 100%（继承 Sheet padding） |
| 对齐 | 水平行，图标左对齐，文字跟随 |
| 图标尺寸 | ≈20px（估算值） |
| 图标与文字间距 | ≈12px（估算值） |

### 视觉样式（选中态）
| 属性 | 值 |
|------|-----|
| Radio 外圈 | `2px stroke, #FFB7C5` |
| Radio 内点 | 实心圆 `≈10px`，填充 `#FFB7C5` |
| 文字颜色 | `#3A3A4A` |
| 文字字号 | `16px Regular` |

### 视觉样式（未选中态）
| 属性 | 值 |
|------|-----|
| Radio 外圈 | `2px stroke, #CCCCCC` |
| Radio 内点 | 无 |
| 文字颜色 | `#3A3A4A` |

### 当前选项
| 选项文字 | 状态 |
|----------|------|
| 浅色 | 已选中（selected） |
| 深色 | 未选中 |
| 跟随系统 | 未选中 |

---

## 5. PrimaryButton — 主操作按钮

### 基本信息
- **名称**: `PrimaryButton`
- **作用**: 确认、完成等主要正向操作
- **共用**: Modal（"确认退出"）和 BottomSheet（"完成"）均使用此按钮

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 高度 | ≈48px（估算值） |
| 宽度 | `100%`（继承父容器宽度减 padding） |
| 圆角 | ≈24px（接近胶囊形，估算值） |
| 文字对齐 | 居中 |

### 视觉样式
| 属性 | 值 |
|------|-----|
| 背景 | `linear-gradient(135deg, #FFB7C5 0%, #FF8FA3 100%)` |
| 文字颜色 | `#FFFFFF` |
| 文字字号 | `16px SemiBold` |
| 阴影 | `0 2px 8px rgba(255,143,163,0.35)` |

### 状态
| 状态 | 样式变化 |
|------|----------|
| default | 如上 |
| pressed | 亮度降低约 10%，轻微缩放 scale(0.98) |
| disabled | opacity 0.38，无阴影 |
| loading | 文字替换为旋转 Spinner |

---

## 6. SecondaryButton — 次操作按钮

### 基本信息
- **名称**: `SecondaryButton`
- **作用**: 取消、返回等次要操作（Modal 专用）

### 尺寸与布局
| 属性 | 值 |
|------|-----|
| 高度 | ≈48px（估算值） |
| 宽度 | `100%` |
| 圆角 | ≈24px（估算值） |

### 视觉样式
| 属性 | 值 |
|------|-----|
| 背景色 | `#FFFFFF` |
| 描边 | `1px solid #E8E8E8`（估算值） |
| 文字颜色 | `#3A3A4A` |
| 文字字号 | `16px Regular` |

### 状态
| 状态 | 样式变化 |
|------|----------|
| default | 如上 |
| pressed | 背景色 `#F5F5F5` |

---

## 7. ScrimOverlay — 遮罩层

### 基本信息
- **名称**: `ScrimOverlay`
- **作用**: 遮盖底层内容，将视觉焦点引导至浮层组件
- **共用**: Modal 和 BottomSheet

### 规格
| 属性 | Modal | BottomSheet |
|------|-------|-------------|
| 覆盖范围 | 全屏（含 NavBar） | 全屏（含 NavBar） |
| 背景色 | `rgba(0,0,0,0.45)` | `rgba(0,0,0,0.25)` |
| z-index | 100 | 100 |
| 点击行为 | 关闭 Modal（可配置为禁止） | 关闭 Sheet |

---

## 8. ChatNavBar — 聊天页导航栏（背景宿主）

### 尺寸
- 高度：≈56px（估算值，含内容）
- 位置：status bar 之下

### 内容（从左到右）
| 元素 | 规格 |
|------|------|
| Avatar | 圆形，≈36px，二次元少女插图 |
| 名称 "悠悠" | 16px SemiBold，#3A3A4A |
| 副标 "在线·消息将自动发送" | 11px Regular，#888888 |
| 电话图标 | 线性图标，≈22px，#3A3A4A |
| 更多图标 "···" | 线性图标，≈22px，#3A3A4A |

---

## 9. ChatInputBar — 底部输入栏（背景宿主）

### 尺寸
- 高度：≈56px（估算值）
- 包含 home indicator 安全区

### 内容（从左到右）
| 元素 | 规格 |
|------|------|
| 加号按钮 | 圆形描边，≈32px |
| 输入框 | 圆角，flex-grow，placeholder "想对悠悠说点什么呢..." |
| 语音按钮 | 圆形，粉色 `#FFB7C5` 填充，≈32px，白色麦克风/波形图标 |

---

## 10. DragHandle — 拖动条

### 规格
| 属性 | 值 |
|------|-----|
| 宽度 | ≈36px（估算值） |
| 高度 | ≈4px |
| 圆角 | `2px`（完全圆角） |
| 颜色 | `#D0D0D0`（估算值） |
| 位置 | Sheet 顶部，水平居中，margin-top ≈12px |

---

## 组件复用关系总览

```
PrimaryButton
├── 用于 ModalCard（"确认退出"）
└── 用于 BottomSheet（"完成"）

ScrimOverlay
├── 用于 ModalCard 背景
└── 用于 BottomSheet 背景

ChatNavBar + ChatInputBar
├── 用于 Toast 宿主背景
├── 用于 ModalCard 宿主背景（加 ScrimOverlay）
└── 用于 BottomSheet 宿主背景（加 ScrimOverlay）
```
