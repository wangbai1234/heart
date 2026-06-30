# 05 Assets — 视觉资源规范

本模块是反馈组件展示参考，不是独立业务页面。本文件用于限制 Toast / Modal / Bottom Sheet 的资源使用方式，避免误导 AI 生成不存在的新素材。

## 1. 资源定位

- `components_feedback` 展示的是反馈组件如何叠加在聊天页面之上
- 背景必须复用 Chat Light 页面资源
- 组件本身必须由 React 实现，不允许用整张图替代

## 2. 允许复用的既有资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 展示底图背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 作为聊天页背景 `cover` |

说明：

- 设计展示图中的暖粉聊天背景，统一视为对 `亮色背景图.png` 的复用
- 不允许再生成 `illustration_crystal_heart.png` 或 `avatar_youyou_default.jpg`

## 3. 头像规则

- 反馈组件叠加在聊天页时，导航栏头像属于运行态头像
- 有真实头像时显示真实头像
- 无头像时显示“空白占位头像组件”
- 不允许使用 demo 角色图作为默认导航头像

## 4. 必须由组件实现的元素

- Toast
- Modal
- Bottom Sheet
- Scrim
- Radio
- Confirm / Cancel / Done 按钮
- Home Indicator 预留

## 5. 可复用的图标来源

- 成功勾选：使用现有图标系统或组件绘制
- 电话、更多、加号、录音：使用现有图标系统
- Radio：使用组件绘制
- 不允许为了这份参考图新增专用位图图标

## 6. 反馈组件视觉约束

- Toast / Modal / Bottom Sheet 必须保持毛玻璃、圆角、粉色品牌系
- 但这些都必须通过组件与 token 实现，不得引导生成新插画资源
- Modal 顶部云朵装饰若保留，必须作为轻量装饰图形或组件实现，不得新生成单独 PNG

## 7. 禁止事项

- 禁止生成 `illustration_crystal_heart.png`
- 禁止生成 `illustration_cloud_heart.png`
- 禁止生成 `avatar_youyou_default.jpg`
- 禁止把 Toast / Modal / Bottom Sheet 做成整张图片
