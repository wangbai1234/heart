# 05 Assets — 角色页 Character Selector

本文件覆盖 Character 页资源真相。旧版“建议命名”“推测第三角色”等内容不再作为执行依据。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 浅色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover` |
| 深色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | 全屏 `cover` |
| Hero Banner | `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp` | 顶部 Hero 区 `cover` |
| 神无月凛头像 | `/Users/wanglixun/heart/assets/characters/character_shenwuyue_avatar.png` | 角色卡头像，圆形裁切 |
| 桃乐丝头像 | `/Users/wanglixun/heart/assets/characters/character_taolesi_avatar.png` | 角色卡头像，圆形裁切 |

## 2. 页面资源落位

### 2.1 Background

- Light：必须使用 `亮色背景图.png`
- Dark：必须使用 `暗色背景图.png`

### 2.2 Hero

- 顶部横幅必须使用 `background_character_hero.webp`
- Hero 中的天空、心形、日光都来自该图
- 不允许重新绘制玻璃心和天空

### 2.3 Character Cards

- 神无月凛卡片头像必须使用 `character_shenwuyue_avatar.png`
- 桃乐丝卡片头像必须使用 `character_taolesi_avatar.png`
- 头像不得替换为新生成版本

## 3. 必须由组件实现的元素

- 返回按钮
- 选中勾选态
- “选择”按钮
- “确认选择”按钮
- 标签胶囊
- 卡片容器

## 4. 禁止事项

- 禁止生成第三张角色图补位
- 禁止重画 Hero
- 禁止修改两位角色头像
