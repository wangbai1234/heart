# 05 Assets — 聊天页 Chat（深色模式）

本文件覆盖 Chat Dark 的资源真相。旧版“可自己实现星云背景”的说法失效。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 全屏深色背景 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | 全屏 `cover`，锚点 `center center` |

## 2. 背景使用规则

- Chat Dark 的整页背景必须直接使用 `暗色背景图.png`
- 不允许自己画星云、星点、云雾
- 不允许将深色页做成另一套新风格

## 3. 头像规则

- 若运行时已有真实角色头像，必须优先使用真实头像
- 若运行时无头像，必须使用“空白占位头像组件”
- 不允许使用任何角色资源作为默认头像
- 不允许生成新的“深色版头像”

## 4. 必须由组件实现的元素

- Header
- Bubble
- Voice Bubble
- Typing Indicator
- Composer
- Play / Pause / Send / More / Back / Plus
- 波形可视化

## 5. 禁止事项

- 禁止自绘深色背景
- 禁止把整页背景改成纯色黑底
- 禁止用图片替代气泡、波形、输入栏
