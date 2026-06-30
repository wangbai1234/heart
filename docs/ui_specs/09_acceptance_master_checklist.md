# 09 Acceptance — 逐页验收总清单

本文件是逐页最终验收母表。各页面目录下 `10_acceptance.md` 仍需满足，但资源与状态相关项以本文件为准。

## 全局必验

- □ 是否读取并遵守 `docs/ui_specs/README.md` 与 `00`–`08` 文档
- □ 是否严格引用了 `assets/backgrounds` 与 `assets/characters` 中的既有资源
- □ 是否没有出现任何 AI 新生成的图片
- □ 是否没有用图片替代 Button / Dialog / Toast / BottomSheet / Input / Nav / Typography
- □ 是否支持浅色模式
- □ 是否支持深色模式
- □ 是否支持 `390×844` 基准布局
- □ 是否支持顶部 `47pt` 与底部 `34pt` 安全区

## 1. Splash

- □ 是否整屏使用 `/Users/wanglixun/heart/assets/backgrounds/静态加载页面.png`
- □ 是否没有把 Splash 拆解重绘
- □ 是否按规范完成 `Loading -> Transition`
- □ 是否按规范转入 Onboarding 或 Login 或 Home

## 2. Onboarding

- □ Step 1 是否使用 `/Users/wanglixun/heart/assets/backgrounds/首次引导页1.png`
- □ Step 2 是否使用 `/Users/wanglixun/heart/assets/backgrounds/首次引导页2.png`
- □ Step 3 是否使用 `/Users/wanglixun/heart/assets/backgrounds/首次引导页3.png`
- □ 是否保持三步文案、分页点、按钮结构一致
- □ 是否保持页间横向切换节奏一致

## 3. Login

- □ 是否使用 `/Users/wanglixun/heart/assets/backgrounds/background_login_hero.webp`
- □ 是否没有重新生成天空插画和玻璃心
- □ 是否保持登录卡片、主 CTA、兑换入口位置一致
- □ 是否支持 `Empty / Error / Offline / Transition / Toast`

## 4. Home

- □ 浅色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 深色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ Hero 是否使用 `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp`
- □ 头像是否使用 `character_shenwuyue_avatar.png` 与 `character_taolesi_avatar.png`
- □ 是否保持 Hero、快捷入口、最近对话、TabBar 布局一致

## 5. Chat Light

- □ 是否使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 是否保持 Header、Bubble、VoiceBubble、Composer 结构一致
- □ 若用户未上传运行态头像，是否显示空白占位头像而非角色图
- □ 是否支持 `Loading / Loaded / Empty / Offline / Error / BottomSheet / Toast`
- □ 是否没有用图片代替气泡、输入栏、波形

## 6. Chat Dark

- □ 是否使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ 是否仅替换背景和深色 token，而不是重做一套新设计
- □ 若用户未上传运行态头像，是否显示空白占位头像而非角色图
- □ 是否保持与浅色版相同结构和状态流

## 7. Character

- □ 浅色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 深色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ Hero 是否使用 `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp`
- □ 头像是否使用 `character_shenwuyue_avatar.png` 与 `character_taolesi_avatar.png`
- □ 是否保持选择态、确认按钮、返回规则一致

## 8. Settings

- □ 浅色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 深色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ 若用户未上传头像，是否显示空白占位头像而非角色图
- □ 是否保持 profile 卡、section card、toggle、segment、slider 的真实组件实现
- □ 是否支持 Dialog / Toast / BottomSheet

## 9. Redeem

- □ 浅色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 深色模式是否使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ 礼盒是否使用 `/Users/wanglixun/heart/assets/backgrounds/兑换页礼品盒.png`
- □ 是否没有新生成礼盒或天空图
- □ 是否支持 OTP 输入、粘贴、Error、Toast、Offline

## 页面通用验收

- □ 是否保持正确背景
- □ 是否保持正确资源
- □ 是否保持布局一致
- □ 是否保持间距一致
- □ 是否保持动画一致
- □ 是否保持状态一致
- □ 是否保持页面流转一致
- □ 是否支持响应式
- □ 是否支持安全区域
- □ 是否达到 `>=95%` 视觉一致性
