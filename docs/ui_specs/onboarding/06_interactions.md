# 06 Interactions — 首次引导 FirstVisitGuide

## 页面导航交互

### 进入动画（Onboarding 整体进场）

| 属性 | 值 |
|------|----|
| 触发时机 | Splash 结束后，首次引导首屏进场 |
| 动画类型 | 淡入（Fade In） + 轻微上移（Translate Y: 20px → 0） |
| Duration | 400 ms |
| Easing | `cubic-bezier(0.0, 0.0, 0.2, 1)`（减速，decelerate） |
| 层级顺序 | 背景先淡入 → 插画弹入 → 文字内容错落上移 |
| 背景进场 | Duration: 300ms，单独淡入 |
| 插画进场 | Duration: 500ms，spring弹入（scale: 0.85 → 1.0，Y: 20px → 0），延迟 100ms |
| 标题进场 | Duration: 400ms，淡入+上移，延迟 250ms |
| 副标题进场 | Duration: 400ms，淡入+上移，延迟 330ms |
| 分页点进场 | Duration: 300ms，淡入，延迟 400ms |
| 按钮进场 | Duration: 300ms，淡入+上移，延迟 450ms |

---

### 屏幕切换动画（Step 1 → 2 → 3）

**触发方式：**
- 点击"下一步"按钮
- ⚠️ 左右滑动手势（设计稿未明确定义，建议支持）

**切换动画规格**

| 属性 | 值 |
|------|----|
| 类型 | 水平滑动（Slide）：当前屏左移退出，下一屏右侧进入 |
| 进入屏幕 | 从 X: +390px → X: 0，Duration: 350ms，easing: decelerate |
| 退出屏幕 | 从 X: 0 → X: -390px，Duration: 350ms，easing: accelerate |
| 并行执行 | 是（两屏同时动画） |
| 插画切换 | 独立弹入，带 spring 弹跳（scale: 0.90 → 1.0） |
| 分页点切换 | 活跃点弹跳扩大（scale: 1.0 → 1.3 → 1.0），Duration: 300ms，spring |

---

### 退出动画（离开 Onboarding）

**路径1：点击"开始体验"**

| 属性 | 值 |
|------|----|
| 动画类型 | 整页淡出（Fade Out）+ 轻微下移 |
| Duration | 350 ms |
| 目标页面 | 注册/登录页（淡入进场） |

**路径2：点击"我有兑换码 →"**

| 属性 | 值 |
|------|----|
| 动画类型 | 底部 Sheet 上弹（Modal Bottom Sheet）⚠️ 设计稿未定义 |
| 建议 | 参考 Motion Storyboard 定义兑换码页进场方式 |

---

## 按钮交互

### GhostButton "下一步" — Pressed 状态

| 阶段 | 属性 | 值 |
|------|------|----|
| 按下瞬间 | scale | 0.97 |
| 按下瞬间 | background-opacity | 50%（从70%降低） |
| 按下瞬间 | border-color | `#FF9EB5`（从`#FFB7C5`加深） |
| 按下动画 | Duration | 100ms |
| 松开 | scale | 1.0（回弹） |
| 松开动画 | Duration | 150ms，spring easing |
| 点击后 | 触发屏幕切换 | 延迟50ms后执行 |

⚠️ Hover 状态：设计稿未定义，建议参考 Motion Storyboard。

---

### PrimaryButton "开始体验" — Pressed 状态

| 阶段 | 属性 | 值 |
|------|------|----|
| 按下瞬间 | scale | 0.97 |
| 按下瞬间 | shadow-blur | 降低至 12px（从20px） |
| 按下瞬间 | gradient | 整体加深5%亮度 |
| 按下动画 | Duration | 100ms |
| 松开 | scale | 1.0，投影恢复 |
| 松开动画 | Duration | 200ms，spring |
| 触感反馈 | iOS | UIImpactFeedbackGenerator（light）⚠️ 设计稿未定义，建议添加 |

**Loading 状态：** ⚠️ 设计稿未定义，建议参考 Motion Storyboard。

---

### TextLinkButton "我有兑换码 →" — Pressed 状态

| 属性 | 值 |
|------|----|
| 按下 | opacity: 0.65 |
| Duration | 100ms |
| 松开 | opacity: 1.0，Duration: 150ms |

---

## 分页点交互

| 交互 | 描述 |
|------|------|
| 自动切换 | 随"下一步"操作自动切换激活点 |
| 动画 | 激活点弹跳：scale(1.0) → scale(1.4) → scale(1.0)，Duration: 300ms，spring |
| 非激活→激活 | 渐变（opacity: 0.30 → 1.0），Duration: 200ms |
| 激活→非激活 | 渐变（opacity: 1.0 → 0.30）+ 尺寸缩小（8px → 6px），Duration: 200ms |
| 直接点击跳转 | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |

---

## 插画交互

### 自动浮动动效（Ambient Float）

⚠️ 设计稿未定义静止插画是否有浮动动效。建议：

| 属性 | 值 |
|------|----|
| 类型 | Y轴缓慢正弦浮动 |
| 幅度 | ±6 px |
| 周期 | 4000ms |
| Easing | `ease-in-out`（正弦节奏） |
| 触发 | 进场动画完成后自动开始，循环 |

---

## 手势交互

| 手势 | 触发条件 | 响应 |
|------|----------|------|
| 水平滑动（Swipe Left） | 快速左滑 | 前往下一步（Step 1→2→3） |
| 水平滑动（Swipe Right） | 快速右滑 | 返回上一步（Step 3→2→1）⚠️ 设计稿未定义是否支持 |
| 垂直滑动 | 上/下滑 | 无响应（页面不可滚动） |
| 长按 | 任意元素 | 无响应 |

---

## 状态说明

| 状态 | 说明 |
|------|------|
| Default | 每屏静态展示，等待用户操作 |
| Hover | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Pressed | 按钮按压反馈（见各按钮规格） |
| Selected | 分页点激活态（见分页点规格） |
| Disabled | ⚠️ 设计稿未定义任何禁用状态 |
| Loading | ⚠️ 设计稿未定义，建议参考 Motion Storyboard（主要针对"开始体验"后的网络请求） |
| Error | ⚠️ 设计稿未定义 |
| Empty | 不适用（引导页内容为静态） |
| Skeleton | 不适用（无异步数据加载） |
| Scroll | 不适用（页面不可滚动） |

---

## 页面转场汇总

| 来源 | 去向 | 转场类型 | Duration |
|------|------|---------|---------|
| Splash Screen | Onboarding Step 1 | 淡入 + 上移 | 400ms |
| Step 1 | Step 2 | 水平滑动 | 350ms |
| Step 2 | Step 3 | 水平滑动 | 350ms |
| Step 3 "开始体验" | 注册/登录 | 淡出 + 缩放（选择） | 350ms |
| Step 3 "我有兑换码" | 兑换码页 | ⚠️ 未定义，建议Bottom Sheet上弹 | 300ms |

---

## 无障碍交互补充

- 所有按钮支持 VoiceOver 朗读（见 09_accessibility.md）
- "下一步"按钮：`accessibilityLabel="下一步，前往步骤{n+1}"`
- "开始体验"按钮：`accessibilityLabel="开始体验，进入yuoyuo"`
- "我有兑换码"：`accessibilityLabel="我有兑换码，前往激活页"`
- 分页点：`accessibilityLabel="当前为第{n}步，共3步"`
