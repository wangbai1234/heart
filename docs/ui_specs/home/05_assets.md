# 05 Assets — 首页 Home

本文件已升级为 Home 页资源唯一执行说明。旧版“建议生成”“纯色替代”等表述全部失效。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 浅色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover`，锚点 `center center` |
| 深色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | 全屏 `cover`，锚点 `center center` |
| Hero Banner | `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp` | HeroCard 内部 `cover`，只裁边不变形 |
| 神无月凛头像 | `/Users/wanglixun/heart/assets/characters/character_shenwuyue_avatar.png` | 最近对话列表、角色相关入口，圆形裁切 |
| 桃乐丝头像 | `/Users/wanglixun/heart/assets/characters/character_taolesi_avatar.png` | 最近对话列表、角色相关入口，圆形裁切 |

## 2. 页面资源落位

### 2.1 Page Background

- Light：必须使用 `亮色背景图.png`
- Dark：必须使用 `暗色背景图.png`
- 不允许改成纯色底
- 不允许重新生成梦幻云彩背景

### 2.2 Hero Card

- 必须使用 `background_character_hero.webp`
- HeroCard 内看到的心形玻璃、天空、太阳光效都来自这张图
- 不允许把 Hero 拆成“新画的天空 + 新画的心形”
- 允许的工程行为只有：
  - 按容器比例裁切
  - 在其上叠加规范允许的文字、按钮、玻璃层

### 2.3 Avatar Usage

- 第 1 个角色必须使用 `character_shenwuyue_avatar.png`
- 第 2 个角色必须使用 `character_taolesi_avatar.png`
- 头像显示方式必须是圆形裁切 + `cover`
- 不允许替换为新生成头像
- Header 右上角头像属于运行态用户头像，不属于角色资源映射
- 若用户已上传头像，Header 右上角必须显示真实头像
- 若用户尚未上传头像，Header 右上角必须显示“空白占位头像组件”
- 不允许使用角色头像作为 Header 右上角默认头像

## 3. 组件与资源分工

以下必须由组件实现，不得做成位图：

- “开始聊天”按钮
- 三个快捷入口卡片
- 最近对话列表容器
- 底部 TabBar
- 标题、时间、未读点、分割线

## 4. 允许的代码视觉层

可由代码实现的只有基础 UI 效果：

- 卡片毛玻璃
- 轻阴影
- 文字
- 按钮
- 图标
- 未读红点

这些代码效果不得替代已经存在的 Banner 和背景图。

## 5. 禁止事项

- 禁止把页面背景实现成纯色或渐变替代图
- 禁止重新生成 Hero 云海
- 禁止重新生成 Hero 心形
- 禁止替换两张角色头像
- 禁止将复杂视觉资源转成 CSS 模拟版
