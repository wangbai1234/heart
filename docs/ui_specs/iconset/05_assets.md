# 05 资源清单 — Icon Set（24×24 系统图标）

## 资源概述

本资产为纯矢量图标库，所有图标应以 SVG 格式交付，不依赖位图资源。
画布背景为纯色，无插画、头像、装饰光效等附加资源。

---

## 背景资源

| 资源类型 | 描述 | 颜色值 | 位置 | 作用 |
|---------|------|--------|------|------|
| 画布背景色 | 暖奶油白纯色填充 | #FAF0EC（估算值） | 全画布铺满 1024×1024 | 图标展示底色 |
| Row 1 白色卡片 | 极浅白色圆角矩形 | #FFFFFF，透明度约 80%（估算值） | Row 1 图标后方 | 第一行图标视觉分组背景 |

---

## 图标资源（36 个 SVG）

### 建议文件命名规范

所有图标以 SVG 格式输出，建议采用以下命名结构：

```
icon-{name}.svg
```

### 完整资源命名列表

| 序号 | 图标名称 | 建议文件名 | 类别 |
|------|---------|-----------|------|
| 01 | 首页 | `icon-home.svg` | 导航 |
| 02 | 聊天气泡 | `icon-chat.svg` | 导航 |
| 03 | AI伴侣 | `icon-ai-companion.svg` | 导航 |
| 04 | 设置 | `icon-settings.svg` | 导航 |
| 05 | 个人资料 | `icon-profile.svg` | 导航 |
| 06 | 搜索 | `icon-search.svg` | 导航 |
| 07 | 发送 | `icon-send.svg` | 聊天 |
| 08 | 麦克风 | `icon-microphone.svg` | 聊天/语音 |
| 09 | 麦克风禁用 | `icon-microphone-off.svg` | 聊天/语音 |
| 10 | 表情 | `icon-emoji.svg` | 聊天 |
| 11 | 贴纸/便签 | `icon-sticker.svg` | 聊天 |
| 12 | 添加 | `icon-add.svg` | 聊天/通用 |
| 13 | 播放 | `icon-play.svg` | 媒体 |
| 14 | 暂停 | `icon-pause.svg` | 媒体 |
| 15 | 波形 | `icon-waveform.svg` | 媒体 |
| 16 | 音量增加 | `icon-volume-up.svg` | 媒体 |
| 17 | 静音 | `icon-mute.svg` | 媒体 |
| 18 | 耳机 | `icon-headphone.svg` | 媒体 |
| 19 | 锁 | `icon-lock.svg` | 系统 |
| 20 | 钥匙 | `icon-key.svg` | 系统 |
| 21 | 铃铛 | `icon-bell.svg` | 系统 |
| 22 | 月亮 | `icon-moon.svg` | 系统 |
| 23 | 太阳 | `icon-sun.svg` | 系统 |
| 24 | 地球 | `icon-globe.svg` | 系统 |
| 25 | 礼物 | `icon-gift.svg` | 商务 |
| 26 | 优惠券 | `icon-coupon.svg` | 商务 |
| 27 | 星星 | `icon-star.svg` | 商务/情感 |
| 28 | 闪光 | `icon-sparkle.svg` | 商务/AI |
| 29 | 皇冠 | `icon-crown.svg` | 商务 |
| 30 | 心形 | `icon-heart.svg` | 情感 |
| 31 | 左箭头 | `icon-arrow-left.svg` | 工具 |
| 32 | 右箭头 | `icon-arrow-right.svg` | 工具 |
| 33 | 关闭 | `icon-close.svg` | 工具 |
| 34 | 确认 | `icon-check.svg` | 工具 |
| 35 | 更多 | `icon-more.svg` | 工具 |
| 36 | 删除 | `icon-trash.svg` | 工具 |

---

## SVG 规范要求

### 画布（ViewBox）
```
viewBox="0 0 24 24"
```
标准 24×24 dp 坐标系。

### 描边参数
| 属性 | 值 |
|------|-----|
| `stroke` | `currentColor`（继承父元素色） |
| `stroke-width` | `1.5` |
| `stroke-linecap` | `round` |
| `stroke-linejoin` | `round` |
| `fill` | `none` |

### 路径规范
- 不使用内联颜色硬编码（使用 `currentColor`）
- 不使用 `!important`
- 所有路径合并为最少数量的 `<path>` 元素
- 删除不必要的 `<g>` 分组
- 不保留设计软件导出的冗余属性（`id`, `class`, `data-*`）

### 导出规格（多倍率）

| 格式 | 用途 | 尺寸 |
|------|------|------|
| SVG | 主格式，Web/React Native | 24×24 dp（缩放自适应） |
| PNG @1x | 备用位图 | 24×24 px |
| PNG @2x | Retina 屏备用 | 48×48 px |
| PNG @3x | 超高清备用 | 72×72 px |

---

## 图标分组文件夹建议

```
assets/icons/
├── navigation/
│   ├── icon-home.svg
│   ├── icon-chat.svg
│   ├── icon-ai-companion.svg
│   ├── icon-settings.svg
│   ├── icon-profile.svg
│   └── icon-search.svg
├── chat/
│   ├── icon-send.svg
│   ├── icon-microphone.svg
│   ├── icon-microphone-off.svg
│   ├── icon-emoji.svg
│   ├── icon-sticker.svg
│   └── icon-add.svg
├── media/
│   ├── icon-play.svg
│   ├── icon-pause.svg
│   ├── icon-waveform.svg
│   ├── icon-volume-up.svg
│   ├── icon-mute.svg
│   └── icon-headphone.svg
├── system/
│   ├── icon-lock.svg
│   ├── icon-key.svg
│   ├── icon-bell.svg
│   ├── icon-moon.svg
│   ├── icon-sun.svg
│   └── icon-globe.svg
├── commerce/
│   ├── icon-gift.svg
│   ├── icon-coupon.svg
│   ├── icon-star.svg
│   ├── icon-sparkle.svg
│   ├── icon-crown.svg
│   └── icon-heart.svg
└── tools/
    ├── icon-arrow-left.svg
    ├── icon-arrow-right.svg
    ├── icon-close.svg
    ├── icon-check.svg
    ├── icon-more.svg
    └── icon-trash.svg
```

---

## 头像 / 角色插画 / 装饰图形 / Logo

**N/A for this asset type** — 图标库画布无角色插画、头像、Logo、装饰光效。

yuoyuo 角色插画和光效资源由其他 Phase 1 资产文件管理（参见 01_character.png, 02_backgrounds.png 等）。

---

## 图标颜色版本建议

| 版本 | 描述 | 颜色 |
|------|------|------|
| Default | 默认墨色版 | #4A4A6A |
| White | 白色版（用于深色背景） | #FFFFFF |
| Primary | 品牌粉色版（激活态） | #FFB7C5 |
| Secondary | 天蓝版（语音激活） | #A7C7E7 |
| Accent | 薰衣草紫版（特效/VIP） | #C8B6FF |

建议通过 `currentColor` 机制由父组件传色，无需维护多套 SVG 文件。

---

## 图标透明度建议

| 场景 | 透明度 |
|------|--------|
| 正常状态 | 100% |
| 未选中导航项 | 60% |
| 禁用状态 | 30% |
| 背景装饰图标（仅视觉用） | 10%–20% |
