# 01 Asset Mapping — 页面资源映射总表

本文件是所有业务页面的资源映射主表。页面目录下的 `05_assets.md` 必须与本文件保持一致。

## 1. 全局资源清单

| 资源名 | 绝对路径 | 原始尺寸 | 用途 |
|---|---|---:|---|
| 亮色背景图 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | `1024×1536` | 浅色模式全屏背景 |
| 暗色背景图 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | `1024×1536` | 深色模式全屏背景 |
| Character Banner | `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp` | `1024×273` | Home / Character 顶部横幅背景 |
| Login Hero | `/Users/wanglixun/heart/assets/backgrounds/background_login_hero.webp` | `1024×447` | Login 顶部主视觉 |
| Redeem Gift Box | `/Users/wanglixun/heart/assets/backgrounds/兑换页礼品盒.png` | `1024×1024` | Redeem 礼盒主视觉 |
| Splash | `/Users/wanglixun/heart/assets/backgrounds/静态加载页面.png` | `1024×1536` | Splash 全屏图 |
| Onboarding 1 | `/Users/wanglixun/heart/assets/backgrounds/首次引导页1.png` | `1254×1254` | Onboarding Step 1 插画 |
| Onboarding 2 | `/Users/wanglixun/heart/assets/backgrounds/首次引导页2.png` | `1254×1254` | Onboarding Step 2 插画 |
| Onboarding 3 | `/Users/wanglixun/heart/assets/backgrounds/首次引导页3.png` | `1254×1254` | Onboarding Step 3 插画 |
| 神无月凛头像 | `/Users/wanglixun/heart/assets/characters/character_shenwuyue_avatar.png` | `299×299` | Character / Home 列表头像 |
| 桃乐丝头像 | `/Users/wanglixun/heart/assets/characters/character_taolesi_avatar.png` | `300×300` | Character / Home 列表头像 |

## 2. 页面级映射

### 2.1 Home

- 浅色模式背景：`/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- 深色模式背景：`/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- Hero Banner：`/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp`
- 角色头像 1：`/Users/wanglixun/heart/assets/characters/character_shenwuyue_avatar.png`
- 角色头像 2：`/Users/wanglixun/heart/assets/characters/character_taolesi_avatar.png`

### 2.2 Chat Light

- 浅色模式背景：`/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`

### 2.3 Chat Dark

- 深色模式背景：`/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`

### 2.4 Character

- 浅色模式背景：`/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- 深色模式背景：`/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- Hero Banner：`/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp`
- 角色头像 1：`/Users/wanglixun/heart/assets/characters/character_shenwuyue_avatar.png`
- 角色头像 2：`/Users/wanglixun/heart/assets/characters/character_taolesi_avatar.png`

### 2.5 Settings

- 浅色模式背景：`/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- 深色模式背景：`/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`

### 2.6 Login

- Hero Background：`/Users/wanglixun/heart/assets/backgrounds/background_login_hero.webp`

### 2.7 Redeem

- 浅色模式背景：`/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- 深色模式背景：`/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- 礼盒图：`/Users/wanglixun/heart/assets/backgrounds/兑换页礼品盒.png`

### 2.8 Onboarding 3-Up

- Step 1：`/Users/wanglixun/heart/assets/backgrounds/首次引导页1.png`
- Step 2：`/Users/wanglixun/heart/assets/backgrounds/首次引导页2.png`
- Step 3：`/Users/wanglixun/heart/assets/backgrounds/首次引导页3.png`

### 2.9 Splash

- 全屏图：`/Users/wanglixun/heart/assets/backgrounds/静态加载页面.png`

## 3. 裁切与缩放规则

- 全屏背景图：使用 `cover`，锚点 `center center`
- Hero Banner：使用 `cover`，锚点 `center center`，只允许裁掉左右，不允许压缩变形
- 头像：使用 `cover` + 圆形裁切，不允许拉伸
- 礼盒图：使用 `contain`，保持原始比例，不允许裁切主体
- Onboarding 三张插画：使用 `contain`，顶部居中，保留完整主体，不允许切掉主体
- Splash：必须整张全屏显示，不得拆成多个图层重建

## 4. 资源禁止事项

- 禁止重命名后让 AI 看不出原始资源
- 禁止用 CSS 重画本地已有背景
- 禁止用 AI 重生成人物头像
- 禁止用渐变代替已有插画
- 禁止从设计稿截图二次切图替代已存在资源
