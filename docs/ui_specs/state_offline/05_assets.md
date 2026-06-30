# 05 Assets — 离线降级状态页

本模块是状态参考图，不是独立业务路由页面。本文件只定义离线态允许复用的既有资源与组件边界。

## 1. 资源定位

- `state_offline` 是 Chat Light 页面的 `Offline` 子状态参考
- 离线态必须复用 Chat Light 的背景和基础组件
- 不允许为了离线态再生成一套新头像、新背景、新图标插画

## 2. 允许复用的既有资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 离线态背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover` |

说明：

- 离线态背景必须与正常 Chat Light 保持同源
- 不允许使用新的 `bg_chat_offline_gradient`

## 3. 头像规则

- 导航栏头像和消息列表头像都属于运行态角色头像
- 有真实头像时必须使用真实头像
- 无真实头像时必须使用“空白占位头像组件”
- 不允许使用 `avatar_youyou_circle_*` 之类不存在的默认角色头像

## 4. 必须由组件实现的元素

- Offline Banner
- Retry Button
- Status Subtitle
- Message List
- Divider
- Composer
- Clock Status Button
- Read Receipt

## 5. 图标规则

以下元素必须由组件或现有图标系统实现，不允许引导生成单独资产：

- 云朵图标
- 刷新图标
- 时钟图标
- 双勾已读图标
- 返回 / 电话 / 更多 / 加号

## 6. 离线态视觉约束

- 只是“正常聊天页进入离线子状态”，不是另一张新页面
- 历史消息变暗、横幅出现、Composer 状态变化，都必须由组件状态驱动实现
- 不允许把离线态做成单独长图

## 7. 禁止事项

- 禁止生成 `bg_chat_offline_gradient`
- 禁止生成 `avatar_youyou_circle_40`
- 禁止生成 `avatar_youyou_circle_36`
- 禁止用新图片替代离线横幅、时钟角标、分割线
