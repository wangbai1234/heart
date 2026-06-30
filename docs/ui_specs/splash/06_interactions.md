# 06 交互规范 — Splash Screen（启动屏）

> 启动屏为全自动展示界面，无用户主动交互。本文档覆盖所有系统驱动的进入/退出动画及推荐的持续动画行为。所有「设计稿未定义」的交互均明确标注。

---

## 交互类型概览

| 交互类型 | 是否适用 | 说明 |
|----------|----------|------|
| 进入动画 | 是 | 启动屏首次显示时的出场动画 |
| 退出动画 | 是 | 系统初始化完成后的消失动画 |
| 持续（Idle）动画 | 是（推荐）| 显示期间的宝石浮动 + 三点呼吸 |
| Hover | 否 | 移动端无 hover 概念 |
| Pressed | 否 | 启动屏不响应用户触摸（全屏透明 block） |
| Selected | 否 | N/A |
| Disabled | 否 | N/A |
| Loading | 是（内联）| 底部三点呼吸点即为 loading 状态表现 |
| Error | 是（降级）| 见「异常处理」章节 |
| Empty | 否 | N/A |
| Skeleton | 否 | N/A |
| Scroll | 否 | 启动屏禁止滚动 |
| Card Selection | 否 | N/A |
| Bottom Button | 否 | N/A |
| Transition（页面跳转）| 是 | 退出后到主界面的过渡 |

---

## 进入动画（Entrance Animation）

### 触发时机
Capacitor `@capacitor/splash-screen` 插件控制，原生层显示后，WebView 加载完毕即开始执行 JS 动画序列。

### 动画序列（推荐时间轴）

```
T = 0ms    背景渐变：opacity 0 → 1（duration: 300ms, ease-out）
T = 0ms    云朵层：opacity 0 → 1（duration: 500ms, ease-out）
T = 200ms  宝石图标：
              scale: 0.75 → 1.0（duration: 600ms, spring easing）
              opacity: 0 → 1（duration: 400ms, ease-out）
T = 400ms  yuoyuo 字标：
              opacity: 0 → 1（duration: 400ms, ease-out）
              translateY: +16px → 0（duration: 400ms, ease-out）
T = 550ms  陪你聊聊吧 tagline：
              opacity: 0 → 1（duration: 400ms, ease-out）
              translateY: +10px → 0（duration: 400ms, ease-out）
T = 700ms  底部三点开始呼吸循环动画
```

> **注意**：以上时间轴为设计推荐值，设计稿中未定义动画时序，需开发与设计对齐确认。

### 宝石进入动画详细参数

| 参数 | 值 |
|------|-----|
| 初始 scale | 0.75 |
| 目标 scale | 1.0 |
| Duration | 600ms |
| Easing | `cubic-bezier(0.34, 1.56, 0.64, 1)`（轻微弹性过冲）|
| 初始 opacity | 0 |
| 目标 opacity | 1 |
| opacity Duration | 400ms |

---

## 退出动画（Exit Animation）

### 触发条件
1. JS 应用初始化完成（`app.ready` 事件触发）
2. 超时兜底：若初始化超过 3000ms，强制执行退出

### 退出动画参数

| 参数 | 值 |
|------|-----|
| 类型 | Fade Out（全屏整体淡出）|
| duration | 300ms |
| easing | `ease-in` |
| 起始 opacity | 1.0 |
| 结束 opacity | 0 |
| 退出完成后 | 移除 Splash 层，展示主界面（主界面已在后台就绪）|

### 主界面进场衔接

| 参数 | 值 |
|------|-----|
| 主界面 Fade In Duration | 200ms（可选，与 Splash Fade Out 并行末段）|
| 避免闪白 | Splash 退出时，主界面背景色应与 Splash 底色接近（使用 `#F5C0CF` 等）|

---

## 持续动画（Idle / Loop Animations）

### 宝石浮动动画（GemFloatAnimation）

**设计稿未定义，以下为推荐规格**：

| 参数 | 值 |
|------|-----|
| 类型 | 上下平移循环 |
| 振幅 | ±8px（Y轴）|
| 周期 | 3000ms |
| Easing | `ease-in-out`（类正弦波）|
| 延迟（进入动画后）| 600ms（等宝石入场动画完成）|
| 循环 | infinite |

```
宝石 Y 坐标变化曲线：
0ms  → translateY(0)
750ms → translateY(-8px)
1500ms → translateY(0)
2250ms → translateY(+8px)
3000ms → translateY(0)
（以上为一个周期，无限循环）
```

### 底部呼吸点动画（BreathingDotsAnimation）

**设计稿未定义动画参数，以下为推荐规格**：

| 参数 | 值 |
|------|-----|
| 类型 | Scale + Opacity 循环 |
| 每点周期 | 1200ms |
| 左点延迟 | 0ms |
| 中间点延迟 | 200ms |
| 右点延迟 | 400ms |

各阶段动画值：

| 时间点 | Scale | Opacity |
|--------|-------|---------|
| 0% | 1.0 | 0.6 |
| 33% | 1.2（中间点）/ 0.9（两侧）| 1.0 |
| 66% | 0.8 | 0.5 |
| 100% | 1.0 | 0.6 |

Easing：`ease-in-out`（类正弦，产生「呼吸」感）

---

## 错误/异常处理（Error State）

### 超时处理

| 场景 | 处理方式 |
|------|----------|
| JS Bundle 加载失败 | 超时 3s 后强制退出启动屏，跳转错误页 |
| 网络断开（首次启动）| 跳转离线提示页或允许离线模式进入 |
| Capacitor WebView 崩溃 | 原生层兜底（App 闪退，操作系统处理）|

### 启动屏异常降级

**设计稿未定义，以下为推荐规格**：

- 若 WebView 动画无法执行，Capacitor 插件的静态图（1024×1536 PNG）作为兜底展示
- 静态图与动画版视觉保持完全一致（无动画差异）

---

## 用户交互禁止规范

| 交互 | 处理方式 |
|------|----------|
| 点击/触摸 | 不响应（事件 block 或 pointer-events: none）|
| 下拉刷新 | 禁止（overscroll-behavior: none）|
| 返回手势 | 禁止（拦截 back gesture）|
| 截图 | 允许（无敏感信息）|

---

## 转场过渡（Transition to Main）

### 过渡效果

| 属性 | 值 |
|------|-----|
| 类型 | Cross-Fade（交叉淡入淡出）|
| 总时长 | 500ms（Splash Fade Out 300ms + 主界面 Fade In 200ms，末段重叠）|
| 主界面初始背景色 | 与 Splash 背景底色一致（减少颜色跳变）|

### 状态机（简化版）

```
[COLD_START]
    ↓ App 进程启动
[SPLASH_SHOWING]  → 持续动画（宝石浮动 + 三点呼吸）
    ↓ JS Ready 或 超时
[SPLASH_HIDING]   → Fade Out（300ms）
    ↓ 动画完成
[MAIN_SHOWING]    → 根据登录状态路由
```

---

## 无障碍交互（见 09_accessibility.md）

启动屏为纯展示页面，无用户交互元素，无障碍要求较低。具体见第9章。

---

## 动画参数汇总

| 动画名称 | 触发时机 | Duration | Easing | 循环 |
|----------|----------|----------|--------|------|
| 背景淡入 | 启动屏显示 | 300ms | ease-out | 否 |
| 宝石进入 | T+200ms | 600ms | spring | 否 |
| 字标淡入 | T+400ms | 400ms | ease-out | 否 |
| Tagline 淡入 | T+550ms | 400ms | ease-out | 否 |
| 宝石浮动 | T+600ms | 3000ms/周期 | ease-in-out | 无限 |
| 三点呼吸 | T+700ms | 1200ms/周期 | ease-in-out | 无限 |
| 页面淡出 | JS Ready | 300ms | ease-in | 否 |

> **设计稿说明**：设计稿仅定义视觉静态帧（PNG），所有动画时序为设计规范推荐值，最终需设计师与前端工程师共同确认。
