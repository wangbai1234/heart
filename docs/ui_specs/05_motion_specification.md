# 05 Motion Specification — 动效规范

本文件覆盖所有页面的默认动效参数。页面级特殊规则以 `06_state_machines.md` 与 `07_navigation_flow.md` 为准。

## 1. 核心时长

| 类型 | 时长 |
|---|---:|
| Instant Press | `100ms` |
| Fast Fade | `180ms` |
| Standard Fade | `240ms` |
| Page Push / Pop | `300ms` |
| Modal / Dialog | `280ms` |
| BottomSheet | `360ms` |
| Toast | `220ms` in / `180ms` out |
| Skeleton Shimmer Cycle | `1200ms` |
| Orb Pulse Cycle | `1200ms` |
| Typing Indicator Cycle | `600ms` |

## 2. Easing

- 标准进入：`cubic-bezier(0.22, 1, 0.36, 1)`
- 标准退出：`cubic-bezier(0.4, 0, 1, 1)`
- 淡入淡出：`ease-out`
- 呼吸 / 脉冲：`ease-in-out`
- BottomSheet / Page Hero 进场：优先使用轻弹簧感实现，但回弹必须克制

## 3. Page Transition

- Splash -> Onboarding / Login：`320ms` fade
- Onboarding 分页：`280ms` horizontal slide
- Login -> Home：`300ms` fade + up `12px`
- Home -> Chat：`300ms` iOS push
- Home -> Character / Settings / Redeem：`300ms` iOS push
- Chat Back：`300ms` iOS pop

## 4. Hero Animation

- Heart / Orb 浮动：Y 轴 `0 -> -6 -> 0`
- 周期：`1200ms`
- Scale：`1.00 -> 1.03 -> 1.00`
- Glow opacity：同步轻微起伏

## 5. Toast Animation

- 进入：opacity `0 -> 1`，translateY `-8px -> 0`
- 退出：opacity `1 -> 0`，translateY `0 -> -8px`
- 停留：默认 `2200ms`

## 6. BottomSheet Animation

- 进入：translateY `100% -> 0`
- 退出：translateY `0 -> 100%`
- 背景遮罩：opacity `0 -> 1`
- 遮罩透明度上限：`0.32`

## 7. Dialog Animation

- 进入：opacity `0 -> 1`，scale `0.96 -> 1`
- 退出：opacity `1 -> 0`，scale `1 -> 0.98`

## 8. Loading / Skeleton

- Skeleton 只允许做浅色 shimmer，不允许强闪烁
- Loading spinner 需轻量、低干扰
- Typing Indicator 采用三点交替起伏

## 9. Reduced Motion

当系统开启减少动态效果：

- 去掉大位移
- 保留淡入淡出
- 停止持续浮动与脉冲
- 用静态状态替代复杂循环动效
