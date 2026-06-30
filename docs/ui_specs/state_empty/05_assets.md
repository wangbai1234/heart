# 05 Assets — 加载 / 空状态

本模块是状态参考图，不是独立业务路由页面。本文件只定义可复用资源与禁止事项，不再允许生成新的演示插画资源。

## 1. 资源定位

- `state_empty` 用于约束 Chat 页面里的 `Empty` 与 `Loading` 子状态
- 实现时优先复用 Chat Light 页面资源与组件
- 不允许为了做空状态再额外生成一套新背景、新头像、新插画

## 2. 允许复用的既有资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 空状态背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover` |

说明：

- 上半区空聊天状态与下半区加载状态都必须复用 `亮色背景图.png`
- 不允许使用不存在的 `illus_cloud_bg.png`、`illus_gem_heart.png`、`avatar_youyou.png`

## 3. 头像规则

- Header 头像属于运行态角色头像
- 若用户已上传或业务已返回头像，必须使用真实头像
- 若头像缺失，必须显示“空白占位头像组件”
- 不允许使用任何角色资源作为 `state_empty` 的默认头像

## 4. 必须由组件实现的元素

- EmptyState 容器
- Header
- 返回 / 电话 / 更多按钮
- 引导文案
- 三个建议 Pill
- Skeleton 气泡
- Typing Dots
- Composer

## 5. 空状态视觉约束

- 空状态的核心是“轻量引导”，不是一张新的完整插画页
- 允许用组件化方式实现中心视觉：
  - 玻璃感心形组件
  - 柔和云雾 / glow 效果
  - 毛玻璃建议 Pill
- 不允许导出或生成新的 `illus_*` 文件来承载这些内容

## 6. 加载状态视觉约束

- 骨架屏必须为组件实现
- Shimmer 必须是代码动画
- 不能使用静态骨架图片
- Header 中的 `...` 必须是真实动态状态，不是写死图片

## 7. 禁止事项

- 禁止生成 `illus_gem_heart.png`
- 禁止生成 `illus_cloud_glow.png`
- 禁止生成 `avatar_youyou.png`
- 禁止将空状态做成新的独立背景插画
