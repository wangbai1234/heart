# 05 Assets — 登录页 Login

本文件覆盖 Login 页资源真相。旧版“拆成天空图 + 玻璃心图 + 花瓣图”的建议失效。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| Login Hero | `/Users/wanglixun/heart/assets/backgrounds/background_login_hero.webp` | 顶部主视觉区域 `cover`，锚点 `center center` |

## 2. Hero 规则

- 登录页顶部主视觉必须直接使用 `background_login_hero.webp`
- 图中天空、玻璃心、云层、花瓣、光线视为同一张完整资源
- 不允许拆成多张新图分别重建
- 不允许重新绘制玻璃心

## 3. 表单区规则

以下必须由组件实现：

- 邮箱输入框
- 信封图标
- 发送登录链接按钮
- 用户协议 / 隐私政策文案
- “我有兑换码，直接激活”入口

## 4. 禁止事项

- 禁止新生成登录 Hero
- 禁止用 CSS 重画 Hero 内天空和心形
- 禁止因为实现方便而改成纯色头图
