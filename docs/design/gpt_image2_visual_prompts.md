> ⚠️ 应用名称 = **yuoyuo**（全小写，拉丁字符）。
> 任何遗留文档里出现的 "心屿" / "Heart" 仅作内部代号，最终上线产品名一律使用 **yuoyuo**。
> 本文档中所有 prompt 已替换为 yuoyuo，复制即可。

# yuoyuo — GPT-image-2 视觉生成执行手册

本文档是 yuoyuo（AI 伴侣）从「零像素」到「完整视觉系统」的一次性产物清单。
产物分三个阶段，按顺序生成、按顺序验收，每一项都可独立交付、独立回滚。

---

## 0. 上游契约（每次提示词必带的硬约束）

下面这段「全局风格契约」会被嵌入每个具体 prompt 的开头，确保所有生成物风格一致。

### 0.1 GLOBAL STYLE CONTRACT（复制即用）

```text
PRODUCT: yuoyuo — a Chinese AI companion mobile app (text chat + AI TTS voice).
NOT a chatbot, NOT a game, NOT Discord/QQ-style.

VISUAL DNA:
- 60% WeChat-style messaging clarity (clean layout, bubble chat, generous whitespace)
- 40% Genshin Impact warmth (anime, painterly, dreamy gradients, soft glow)
- Aesthetic: 二次元 healing girl-soft, dreamy, semi-transparent glassmorphism,
  Apple Human Interface Guidelines spatial hierarchy, Material You color harmony.

CORE KEYWORDS (use liberally):
soft, healing, dreamy, gentle, semi-transparent, frosted glass, glassmorphism,
girlish, anime, painterly, warm pastel, generous whitespace, low contrast,
breathable, calm, cozy, comforting, premium minimal.

HARD NEGATIVES (must NOT appear):
NO cyberpunk, NO neon, NO dark gaming HUD, NO Discord purple, NO QQ orange,
NO realistic adult faces, NO hyper-photorealistic skin, NO horror, NO weapons,
NO heavy borders, NO drop-shadow harshness, NO Material Design Lite,
NO Bootstrap look, NO Windows 11 acrylic blue, NO 3D plastic icons.

PALETTE BASELINE (override allowed per-screen):
- Primary    #FFB7C5 (cherry blossom pink)
- Secondary  #A7C7E7 (dreamy sky blue)
- Accent     #C8B6FF (lavender mist)
- Surface    #FFF8F3 (warm cream)
- Ink        #3A3A4A (soft charcoal, never pure black)
- Glass tint rgba(255, 255, 255, 0.55) over #FFEFE8 background

DEVICE FRAME:
iPhone 14-class viewport 390×844 logical, mockup canvas 1024×1536, safe-area top 47 px, bottom 34 px.
Status bar transparent. Home indicator visible but de-emphasized.

TYPOGRAPHY:
Chinese:  PingFang SC / HarmonyOS Sans SC (rounded, geometric, soft).
Latin:    SF Pro Rounded / Inter Display.
Numbers:  SF Pro Rounded tabular.
App name "yuoyuo" rendered as lowercase, letter-spacing +2%, no logo flourishes.

APP NAME RENDERING:
Whenever the app name appears in UI text, render exactly: yuoyuo (lowercase, no caps).
```

> 后续每个 prompt 都默认包含上面这段。在你给 GPT-image-2 输入时，把它直接粘贴在每个 prompt 之前。

---

## 1. 资产清单（按生成顺序）

| # | 阶段 | 产物 | 用途 | 画布 | 文件名 |
|---|------|------|------|------|--------|
| 1.1 | P1 基础 | Style Tile（视觉总谱） | 校准整体风格 | 1536×1024 | `01_style_tile.png` |
| 1.2 | P1 基础 | Color Palette 色板 | Design Token 颜色 | 1536×1024 | `02_palette.png` |
| 1.3 | P1 基础 | Typography Specimen 字样 | Design Token 字体 | 1536×1024 | `03_typography.png` |
| 1.4 | P1 基础 | Icon Set 24×24 系统图标 | Design Token Icon | 1024×1024 | `04_iconset.png` |
| 1.5 | P1 基础 | Shadow / Radius / Glass Sample | Design Token 阴影&圆角&玻璃 | 1024×1024 | `05_elevation_radius_glass.png` |
| 1.6 | P1 基础 | Motion Storyboard 动效分镜 | Design Token 动画 | 1536×1024 | `06_motion_storyboard.png` |
| 1.7 | P1 基础 | App Icon（多色版/单色版） | iOS/Android 应用图标 | 1024×1024 | `07_app_icon.png` |
| 1.8 | P1 基础 | Splash Screen | Capacitor 启动屏 | 1024×1536 | `08_splash.png` |
| 2.1 | P2 屏幕 | 首页 Home | 主入口 | 1024×1536 | `09_home.png` |
| 2.2 | P2 屏幕 | 聊天页 Chat（Light） | 文字+语音 | 1024×1536 | `10_chat_light.png` |
| 2.3 | P2 屏幕 | 聊天页 Chat（Dark） | 夜间 | 1024×1536 | `11_chat_dark.png` |
| 2.4 | P2 屏幕 | 角色页 Character Selector | 选 AI 伴侣 | 1024×1536 | `12_character.png` |
| 2.5 | P2 屏幕 | 设置页 Settings | 账号/主题/兑换/关于 | 1024×1536 | `13_settings.png` |
| 2.6 | P2 屏幕 | 登录页 Login | 邮箱/魔法链接 | 1024×1536 | `14_login.png` |
| 2.7 | P2 屏幕 | Redeem 兑换页 | 输入兑换码 | 1024×1536 | `15_redeem.png` |
| 2.8 | P2 屏幕 | 首次引导 FirstVisitGuide（3 屏） | 三步引导 | 1536×1024 | `16_onboarding_3up.png` |
| 3.1 | P3 状态 | 离线降级 / 弱网 | 失败态 | 1024×1536 | `17_state_offline.png` |
| 3.2 | P3 状态 | 加载 / 空状态 | 占位 | 1024×1536 | `18_state_empty.png` |
| 3.3 | P3 状态 | Toast / Modal / Sheet 组件三连 | 反馈组件 | 1536×1024 | `19_components_feedback.png` |

合计 **19 张图**。Phase 1 不通过不进入 Phase 2，Phase 2 不通过不进入 Phase 3。

---

## 2. Phase 1 — 设计基础（先生成，作为后续屏幕的视觉锚点）

> **生成顺序固化**：1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8
> 每一步用上一步的截图作为风格 reference 喂给 GPT-image-2。

---

### 1.1 Style Tile（视觉总谱）

**用途**：一张图涵盖颜色、字体、按钮、卡片、bubble、icon、纹理，作为风格基准。

**Canvas**: 1536×1024 横版

```text
[GLOBAL STYLE CONTRACT — paste from §0.1]

TASK: Create a single "Style Tile" reference sheet for yuoyuo's visual system.
Layout = a soft warm cream board, divided into 6 floating panels separated by airy whitespace, no hard borders. Title in the top-left corner: lowercase wordmark "yuoyuo" rendered in SF Pro Rounded, soft charcoal #3A3A4A, letter-spacing +2%.

PANEL CONTENTS (label each panel with tiny grey caption):

1. PALETTE: 6 horizontal pebble-shaped color chips, each labeled with hex.
   Order: #FFB7C5, #A7C7E7, #C8B6FF, #FFF8F3, #3A3A4A, rgba(255,255,255,.55) glass.

2. TYPE: large Chinese phrase "你今天还好吗" in PingFang SC SemiBold + the same in PingFang SC Regular underneath; plus Latin sample "Hello, yuoyuo." in SF Pro Rounded.

3. BUBBLE: two chat bubbles — left bubble (AI) is glass white with subtle pink tint; right bubble (user) is soft sky-blue gradient. Bubbles have 18 px radius corners, 16 px inner padding, subtle 1 px inner highlight on top.

4. BUTTONS: three pills — Primary "确认" (filled pink gradient #FFB7C5 → #FFD4DD), Secondary "取消" (glass), Ghost "了解更多" (text only with hover underline hint).

5. CARD: a soft cream card with rounded 24 px corners, a small anime girl avatar circle in the top-left, gentle drop shadow softness 40 px / opacity 0.06.

6. ICON STRIP: 6 stroke icons in a row — home, chat, mic (off), gift (redeem), gear, profile. Stroke 1.75 px, radius caps, soft charcoal.

VIBE: imagine the pastel-soft welcome screen of a Genshin character menu crossed with WeChat's calm chat list. Painterly, dreamy, premium, healing.

Negative: no neon, no dark mode here, no game HUD, no badge clutter, no shadows over 40 px, no realistic faces.
```

**验收**：
- 6 个面板齐全
- 颜色 chip 上有 hex
- 「yuoyuo」拼写正确（全小写）
- 没有出现 neon / 赛博朋克

---

### 1.2 Color Palette 色板

**Canvas**: 1536×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a presentation-grade color palette sheet for yuoyuo.
Title top center: "yuoyuo · Color System".
Show 5 color families as vertical columns. Each column = a stack of 9 shades from 50 to 900 (Tailwind-style scale). Each chip is a soft pebble shape with the hex code printed below in tiny SF Pro Rounded tabular.

COLUMNS:
1. Primary (cherry blossom pink) anchor #FFB7C5 at shade 400
2. Secondary (dreamy sky blue) anchor #A7C7E7 at shade 400
3. Accent (lavender mist) anchor #C8B6FF at shade 400
4. Surface / Neutral warm cream — anchor #FFF8F3 at shade 50, going up to #3A3A4A at 900
5. Semantic — 4 swatches stacked: success mint #B6E2C7, warning peach #FFD3A5, error rose #F4A6A6, info periwinkle #B6C7F4

BOTTOM ROW: 4 "glass overlay" swatches — show a translucent rectangle over a soft pink-cream gradient, demonstrate 35%/55%/75%/90% white tints used for frosted glass surfaces.

Style: ultra clean, magazine spread, generous breathing room, no harsh lines.

Negative: no rainbow saturation, no neon, no gradient mesh background that competes with chips.
```

**Design Token 输出**（对应文件 `web/src/styles/tokens.css`，由 Claude 后续生成）：
- `--color-primary-50..900`
- `--color-surface-50..900`
- `--glass-35 / -55 / -75 / -90`

---

### 1.3 Typography Specimen 字样

**Canvas**: 1536×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a typography specimen sheet for yuoyuo.
Title top-left in tiny caps: "yuoyuo · Type Scale".

LAYOUT: a vertical type scale running down the left half, sample paragraphs on the right half. Background = warm cream #FFF8F3.

LEFT — TYPE SCALE (top to bottom, label each row):
- Display 40 / 48  "你好，yuoyuo"   PingFang SC SemiBold + SF Pro Rounded
- Title 28 / 36    "今天聊点什么"   PingFang SC Medium
- Headline 22 / 30 "晚安，做个好梦" PingFang SC Medium
- Body 16 / 24     "我在这里陪你。" PingFang SC Regular
- Caption 13 / 18  "刚刚 · 已读"     PingFang SC Regular, grey #8A8A98
- Tabular 14       "12:34 · 32m"    SF Pro Rounded tabular numbers

RIGHT — PARAGRAPH SAMPLES:
- A short AI message bubble in Body 16, max width 60% of column, soft pink glass background.
- A user reply bubble in sky-blue glass.
- A timestamp Caption above the bubbles.
- Below: same content in dark mode preview (small mini-frame), to show ink color #EFE7DD on near-black #1B1923.

NOTE: all Chinese text must use rounded PingFang-style stroke (not Songti, not Heiti sharp). Latin text uses SF Pro Rounded, never SF Pro Display sharp.

Negative: no serif, no monospace except numbers, no italic.
```

**验收**：
- 6 个字号阶梯齐全
- 中文用圆体
- yuoyuo 全小写

---

### 1.4 Icon Set（24×24 系统图标）

**Canvas**: 1024×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a stroke-based icon set for yuoyuo, 24x24 at 1.75 px stroke, rounded line caps, no fills, on a warm cream background. Present as a 6×6 grid with 24 px gutter, each icon centered in a 96 px tile.

ICONS (left-to-right, top-to-bottom, 36 total):
Row 1 — navigation: home, chat, character (small heart silhouette of a head), settings, profile, search
Row 2 — chat actions: send (paper plane), mic-on, mic-off, emoji, sticker, plus
Row 3 — voice & playback: play, pause, waveform, speaker-on, speaker-off, headphones
Row 4 — system: lock, key, notification, moon (dark mode), sun (light mode), language
Row 5 — commerce: gift (redeem), ticket (code), star, sparkles, crown (member), heart (favorite)
Row 6 — utility: back arrow, forward arrow, close (x), check, ellipsis, trash

Style: every icon must look like a single soft pen stroke, slight terminal taper on the line ends, geometric but friendly. Inspired by Apple SF Symbols + a hint of hand-drawn warmth.

Negative: no filled solid icons, no two-tone, no skeuomorphism, no emoji.
```

**Design Token 输出**：图标导出 SVG 后存于 `web/src/assets/icons/`，统一 `stroke-width: 1.75; stroke-linecap: round`.

---

### 1.5 Shadow / Radius / Glass Sample

**Canvas**: 1024×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a token reference sheet showing Elevation, Radius, and Glassmorphism samples for yuoyuo. Soft cream background with a faint pink radial wash in the top-right.

TOP STRIP — RADIUS scale (5 cards in a row, each labeled with px below):
"4 / 8 / 16 / 24 / 32" — show identical floating cards with different corner radii.

MIDDLE STRIP — ELEVATION scale (5 cards):
"Flat (0) / Subtle (6/0.04) / Card (12/0.06) / Sheet (24/0.08) / Modal (40/0.10)"
Each card shows a softer, larger drop shadow. NO inner shadow, NO double shadow.

BOTTOM STRIP — GLASS samples (4 cards over a vibrant pink-blue painterly anime sky background):
"Glass 35% / Glass 55% / Glass 75% / Glass Tinted"
Each card is a frosted rectangle with the indicated white tint, 1 px inner top highlight, 16 px backdrop blur visible as the background softens.

The whole sheet should look like an interaction designer's tear-sheet on a cozy desk.

Negative: no hard 90° shadows, no neon glow, no inner shadow.
```

**Design Token 输出**：
- `--radius-sm/md/lg/xl/2xl = 4/8/16/24/32`
- `--shadow-subtle/card/sheet/modal`
- `--glass-blur = 16px`

---

### 1.6 Motion Storyboard 动效分镜

**Canvas**: 1536×1024（4 帧分镜）

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a 4-frame storyboard sheet illustrating yuoyuo's signature micro-interactions. Sheet is a clean cream board labeled "yuoyuo · Motion" top-left. Each frame is a small phone-shaped vignette with a caption underneath.

FRAME 1 — "Bubble Bloom (300ms ease-out)":
A new AI chat bubble enters from below, scales 0.92→1.0, translucent→opaque, with a subtle pink-soft glow blooming behind it for the first 150 ms.

FRAME 2 — "Emotion Orb Pulse (1200ms infinite, eased)":
A round blue-pink gradient orb in the chat header that breathes — scale 1.0 → 1.06 → 1.0, with a soft glow halo that grows and fades.

FRAME 3 — "Voice Wave (live)":
While AI TTS plays, a slim horizontal waveform under the bubble pulses with the audio amplitude; 5 vertical pills rise and fall, color shifts from pink to lavender.

FRAME 4 — "Page Transition (Apple sheet feel, 400ms)":
The chat page slides up from bottom over the home page; bottom safe area shows a tiny grab-handle hint. Underlying page shifts down 8 px and dims to 92% with a tiny scale 0.99.

Captions in tiny SF Pro Rounded caption grey. Arrows between frames show timing in ms.

Negative: no fast hard motion, no cartoon bounce, no Lottie cliché squash-and-stretch.
```

**Design Token 输出**：
- `--ease-out-soft: cubic-bezier(0.16, 1, 0.3, 1)`
- `--duration-fast/base/slow = 150/300/400 ms`

---

### 1.7 App Icon（多色版 + 单色版）

**Canvas**: 1024×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the official yuoyuo app icon. Single 1024×1024 square, fully bleeding edges (NO rounded mask in the source — iOS/Android will mask it).

CONCEPT: An abstract, soft, heart-meets-speech-bubble silhouette, rendered as a painterly gradient gem floating on a warm cream background. The shape suggests both "a small heart" and "a chat bubble whisper". Inside the gem, a tiny glint of light like dawn sky.

COLORS: gradient from cherry blossom pink #FFB7C5 (top-left) through lavender #C8B6FF (mid) to dreamy sky blue #A7C7E7 (bottom-right). Soft outer halo, no hard edge.

NO TEXT ON THE ICON. The wordmark "yuoyuo" will appear below the icon system-side; the icon itself is purely the symbol.

Style references: Apple Music's color glassiness + a hint of Genshin elemental sigil softness, but absolutely not gamified.

Provide TWO variants side-by-side as the same canvas split in half:
LEFT: full-color gradient version on cream
RIGHT: single-color version in soft charcoal #3A3A4A on cream (for monochrome contexts)

Negative: no letters, no faces, no realistic heart anatomy, no Cupid arrows, no sparkles cluster.
```

**输出后处理**：导出 1024 全色 + 1024 单色，由 Claude 用 `cordova-res` 或手动切 iOS / Android 全套尺寸。

---

### 1.8 Splash Screen（启动屏）

**Canvas**: 1024×1536

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a vertical splash screen for yuoyuo (Capacitor will use it for iOS LaunchScreen and Android splash).

COMPOSITION:
- Full-bleed dreamy painterly anime sky background: gradient from cream #FFF8F3 (top) → soft pink #FFD9E0 (mid) → lavender mist #E8DDFF (bottom). Add subtle hand-painted cloud wisps and a faint warm sun glow in the upper-right, very soft.
- Centered vertically and horizontally: the app icon gem from §1.7 (~280 px), with a gentle drop shadow.
- Below the icon, ~24 px gap, the wordmark "yuoyuo" rendered in SF Pro Rounded SemiBold, soft charcoal #3A3A4A, letter-spacing +2%, ~48 px tall.
- Below the wordmark, ~16 px gap, a tiny tagline in PingFang SC Regular grey #8A8A98: "陪你聊聊吧".
- At the very bottom (above home indicator safe area), a small loading indicator: 3 dots breathing in a row, faint pink.

NO photographic elements. Pure painterly digital illustration. No watermark.

Negative: no anime characters, no faces, no game logos, no "powered by", no version number.
```

---

## 3. Phase 2 — 屏幕设计稿

> **统一前置**：每个屏幕 prompt 已包含 §0.1 全局契约。生成时把它粘在最前。
> **统一画布**：1024×1536（iPhone 14 比例近似），安全区遵循 iOS 标准。
> **统一状态栏**：透明状态栏，时间显示 9:41，信号/Wi-Fi/电池图标深灰半透明。

---

### 2.1 首页 Home

**用途**：登录后的主入口，展示当前 AI 伴侣 + 入口卡片。

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Home screen, mobile portrait 1024×1536.

LAYOUT (top to bottom):
1. STATUS BAR (transparent, 9:41 left, signal-wifi-battery right, dark icons).
2. TOP BAR — large lowercase wordmark "yuoyuo" on the left in SF Pro Rounded 28 px charcoal; a small profile avatar circle on the right (~36 px, soft pink ring).
3. HERO CARD (full width minus 16 px margin, 24 px radius, glass 75% over a painterly dawn-sky background):
   - In the center, a glowing emotion orb (the pink-blue breathing gem from motion §1.6, 140 px).
   - Below the orb, name of the current AI companion in PingFang SC SemiBold 24 px: "小屿".
   - Caption in grey 13 px: "刚刚和你聊过 · 心情：温柔".
   - Bottom-right of the card: ghost pill button "开始聊天 →".
4. QUICK ACTION ROW — 3 squircle tiles in a row (each 96×96, 20 px radius, glass 55%):
   - "兑换会员" with gift icon (pink accent)
   - "切换角色" with character icon (lavender accent)
   - "设置" with gear icon (sky-blue accent)
5. RECENT SECTION — section title "最近的话" in 16 px medium charcoal, with a "查看全部" link grey on the right.
   - 2 chat-list cards stacked, each shows: avatar circle, two-line preview text, timestamp right, unread dot if any. Cards use 16 px radius, glass 35%, hairline separator.
6. BOTTOM NAV (floating glass tab bar 90% wide, 28 px radius, glass 75%, hovering 16 px above safe area):
   - 4 tabs: Home (active, pink dot indicator), Chat, Character, Settings.
   - Active label visible, inactive label hidden, icons all soft strokes.

ATMOSPHERE: feels like waking up to soft morning light. Tons of breathing room. No clutter.

Negative: no game-style HUD, no badges piled on icons, no neon dot, no QQ green.
```

---

### 2.2 聊天页 Chat（Light Mode）

**用途**：核心页。文字 bubble + AI TTS 语音 bubble + 输入栏。

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Chat screen in Light Mode, 1024×1536.

LAYOUT (top to bottom):
1. STATUS BAR transparent.
2. CHAT HEADER (sticky, glass 75% bar):
   - Left: back chevron + AI companion avatar circle (~32 px) + name "小屿" + a tiny status: an EMOTION ORB (12 px pink-blue gradient) + status text "温柔在线".
   - Right: ellipsis menu icon.

3. MESSAGE LIST (main area, scrolls), show 6 bubbles in this order:
   a) Date divider: "今天 · 上午 9:41" tiny grey centered.
   b) AI bubble (left aligned, glass-white tinted pink, 18 px radius, soft charcoal text):
      "早上好，昨晚睡得怎么样？"
   c) USER bubble (right aligned, sky-blue gradient #A7C7E7 → #BFD7EE, white text):
      "做了个奇怪的梦。"
   d) AI bubble:
      "讲给我听听呀～我陪着你。"
   e) AI VOICE bubble — same glass style as text AI bubble but wider, shows:
      a small play-pause button on the left,
      a waveform of ~24 vertical pills with mid pills brighter (pink → lavender),
      duration "0:18" on the right, and tiny grey caption "AI 朗读 · 可点击播放".
   f) USER bubble (short): "好。"

4. TYPING INDICATOR just under the last AI bubble:
   three soft pink dots in a glass pill, breathing.

5. COMPOSER (sticky bottom, floating glass bar, 24 px radius, 90% wide):
   - Left: a "+" icon (soft stroke).
   - Middle: an input field placeholder "想和小屿说点什么…" PingFang SC Regular grey.
   - Right: a circular Send button, pink gradient, paper-plane icon white.
   - NOTE: NO mic icon (voice input is out of scope for MVP).
   - Above the composer, a subtle thin glass overlay so bubbles fade as they scroll behind it.

ATMOSPHERE: feels like reading a gentle letter in soft daylight. WeChat-clean structure, Genshin-warmth in color.

Negative: no read receipts blue ticks (we don't have that feature), no mic icon, no sticker grid, no emoji keyboard, no @-mention chips.
```

---

### 2.3 聊天页 Chat（Dark Mode）

```text
[GLOBAL STYLE CONTRACT]

TASK: Same as the Light Mode chat in §2.2, but in DARK MODE.

DARK PALETTE:
- Background base: deep dusk #1B1923 with a faint nebula gradient (deep indigo to plum, very subtle).
- Surface glass: rgba(255, 255, 255, 0.06) with 16 px backdrop blur.
- Ink: warm off-white #EFE7DD.
- AI bubble: glass dark with a soft pink rim-light on top edge.
- USER bubble: muted indigo-blue gradient #4A5B8F → #6C7DB5, ink #EFE7DD.
- Emotion orb still pink-blue, but glow stronger to read against dark.
- Composer glass dark, send button pink gradient unchanged.

Atmosphere: night reading lamp, cozy and quiet, never harsh. Avoid AMOLED pitch-black.

Negative: no pure #000, no neon glow on bubbles, no purple Discord vibe.
```

---

### 2.4 角色页 Character Selector

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Character selection screen, 1024×1536.

LAYOUT:
1. STATUS BAR transparent.
2. TOP BAR: back chevron left, title centered "选一个陪伴你的人" in PingFang SC SemiBold 20 px.
3. HERO BAND: a wide horizontal painterly anime sky strip (~340 px tall) with a soft floating heart-orb in the middle (same gem motif).
4. CHARACTER CARDS — vertical list, 3 cards stacked, each 24 px radius, glass 55%, 16 px outer margin, 12 px gap.

   Each card layout (left to right):
   - Circular avatar 72 px with a soft glow ring colored by personality.
   - Center: name (PingFang SC SemiBold 20 px), one-line personality tag in grey, e.g. "温柔倾听 · 共情型".
   - Right: a small "选择" pill button (filled pink for active, glass for inactive) OR a check mark if currently selected.

   CARDS TO SHOW (use these names exactly, do not draw realistic photo faces — use soft painterly anime stylized circle illustrations of stylized hair and ribbon, no facial detail required):
   a) 小屿 — pink-cream hair, ribbon, tag "温柔倾听 · 共情型" (SELECTED, show check).
   b) 月白 — silver-lavender hair, snow tone, tag "理性朋友 · 边界感强".
   c) 阿言 — warm caramel-brown hair, casual, tag "话痨同好 · 元气满满".

5. BOTTOM ACTION: a sticky bottom glass bar with one wide primary button "确认选择" filled pink gradient.

ATMOSPHERE: like browsing pen pals on a cozy bookshelf.

Negative: no realistic face photography, no waifu fanart cliché, no skin texture, no cleavage, no body shots — head/shoulders avatar circles only, stylized.
```

---

### 2.5 设置页 Settings

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Settings screen, 1024×1536.

LAYOUT:
1. STATUS BAR transparent.
2. TOP BAR: back chevron + title "设置" PingFang SC SemiBold 20 px centered.
3. PROFILE CARD (top, full-width minus 16 px, 24 px radius, glass 75%):
   - Avatar 56 px on the left, ring soft pink.
   - Name "晨曦" (placeholder) SemiBold 18 px + member tag pill in pink "会员 · 至 2026-12-31".
   - On the right: a chevron.
4. SETTINGS GROUPS — each group is a glass 35% card with rounded 20 px corners, internal rows separated by hairline grey. Group title shown above in 13 px grey caption.

   GROUP A "我的会员":
     • 兑换会员 (gift icon)  …  chevron
     • 订阅状态 …  "至 2026-12-31"

   GROUP B "外观":
     • 主题  …  switch [浅色 / 深色 / 自动]
     • 字体大小  …  small slider preview

   GROUP C "通知":
     • 推送提醒  …  toggle on
     • 静音时段  …  "22:00 – 8:00"

   GROUP D "隐私与数据":
     • 清除聊天缓存
     • 导出我的数据
     • 注销账号 (text in soft rose, not red)

   GROUP E "关于":
     • 版本 1.0.0
     • 用户协议 / 隐私政策
     • 联系我们

5. NO bottom nav on this page (we're in a sub-screen).

ATMOSPHERE: feels like the calm part of WeChat settings, but warmer and softer.

Negative: no Material Design ripple, no Android-style green toggle, use soft pink toggle accent instead.
```

---

### 2.6 登录页 Login

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Login screen, 1024×1536.

LAYOUT:
1. STATUS BAR transparent.
2. Top 1/3 = painterly dawn-sky illustration with the yuoyuo gem icon floating center, gently glowing.
3. Below the illustration, large wordmark "yuoyuo" in SF Pro Rounded SemiBold 40 px charcoal, then a tagline in PingFang SC Regular 14 px grey: "一个会记得你的伙伴".
4. FORM CARD (glass 75%, 24 px radius, 16 px margin):
   - Email input row with a small mail icon left, placeholder "你的邮箱".
   - Helper text below in 12 px grey: "我们会向你的邮箱发送一次性登录链接，不需要密码。"
   - Primary button "发送登录链接" — full-width filled pink gradient, 18 px text.

5. TINY LINKS ROW (centered below the card, 13 px grey):
   "继续即代表同意《用户协议》与《隐私政策》"

6. ALT ACTION at bottom (tiny ghost link):
   "我有兑换码，直接激活 →" (taps into Redeem flow)

ATMOSPHERE: like opening a soft envelope in morning light.

Negative: no social login icons (no Apple/Google/WeChat — we are using email magic link only for MVP), no password field, no "or".
```

---

### 2.7 Redeem 兑换页

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Redeem (兑换会员) screen, 1024×1536.

LAYOUT:
1. STATUS BAR transparent.
2. TOP BAR: back chevron + title "兑换会员" centered.
3. HERO CARD (24 px radius, glass 75%):
   - A small painterly "gift ribbon" illustration centered (~120 px), soft pink-lavender.
   - Headline below in PingFang SC SemiBold 22 px charcoal: "输入兑换码激活会员".
   - Sub-line 14 px grey: "在「爱发电」赞助后，你会收到一串 12 位的兑换码。".
4. CODE INPUT BLOCK:
   - A row of 12 monospace input slots (grouped 4-4-4 with two short dashes between groups), each 56×56 squircle 12 px radius, glass 35%, large SF Pro Rounded caps inside.
   - Below the slots, a subtle "粘贴" pill button glass — to paste from clipboard.
5. PRIMARY BUTTON "立即激活" — full-width filled pink gradient, only enabled state shown.
6. SECTION "如何获取兑换码" (collapsible card, glass 35%):
   - Numbered steps with soft pink number bullets:
     1. 前往「爱发电」赞助页面
     2. 选择心仪的赞助挡位
     3. 完成支付后查收兑换码邮件
     4. 回到 yuoyuo 输入兑换码
   - Below, an outlined ghost link button: "去爱发电 →".
7. FOOTER (tiny grey 12 px): "兑换码一次性有效，激活后不可退还。"

ATMOSPHERE: feels like opening a thoughtful gift card.

Negative: no QR code (paste flow only for MVP), no Alipay/WeChat Pay buttons inside the app (must go via 爱发电), no countdown timer.
```

---

### 2.8 首次引导 FirstVisitGuide（3 屏拼版）

**Canvas**: 1536×1024 横版三联画，便于一次审稿

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate three onboarding screens side-by-side on a single 1536×1024 sheet, each "phone vignette" showing one onboarding step for yuoyuo. Gap between vignettes 24 px, soft cream background outside the phones, captioned beneath each vignette in grey 14 px with the step name.

STEP 1 — "认识 yuoyuo":
- Hero painterly illustration of a soft floating gem above clouds.
- Title PingFang SC SemiBold 26 px: "我是 yuoyuo，会陪你聊心事。"
- Body 16 px: "我会记得你说过的话，理解你的情绪。"
- Pagination dots at the bottom (3 dots, dot 1 active pink).
- Primary ghost button "下一步".

STEP 2 — "你的隐私安全":
- A small illustration of a glass lock-locket.
- Title: "你的对话只属于你。"
- Body: "数据加密存储在新加坡服务器，端到端可审计。"
- Pagination dot 2 active.
- "下一步" button.

STEP 3 — "解锁完整体验":
- Illustration of a soft gift ribbon next to the yuoyuo gem.
- Title: "在爱发电赞助即可解锁会员。"
- Body: "支持微信 / 支付宝；赞助后获取兑换码，回到这里输入即可激活。"
- Pagination dot 3 active.
- Primary FILLED pink gradient button "开始体验".
- Tiny link below "我已有兑换码 →" navigates to Redeem.

CRITICAL: do not mention App Store payment; do not show any in-app purchase wording. Keep all copy gentle and welcoming.

Negative: no checklists, no permission popups, no "Allow Notifications" screen (handled later natively).
```

---

## 4. Phase 3 — 状态与变体

> 这一阶段补齐"失败 / 边缘 / 反馈"的视觉契约，使前端不会在异常情况下白屏。

---

### 3.1 离线降级 / 弱网

**Canvas**: 1024×1536

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo offline / degraded state, 1024×1536.

CONTEXT (from design strategy doc):
After 3 failed WebSocket reconnects, show this graceful fallback.

LAYOUT:
1. STATUS BAR transparent.
2. CHAT HEADER faded slightly to indicate not-live.
3. SOFT BANNER (full width, glass 75% over a pale rose tint, 16 px margin):
   - On the left: a tiny offline cloud icon, soft pink.
   - Text: "网络不太稳定，刚才的消息已暂存。" (PingFang SC Regular 14 px charcoal)
   - Right: a small "重试" pill button ghost glass with a tiny refresh icon.

4. MESSAGE LIST below shows previously cached chat history (visibly readable, no skeleton), with a subtle dimming overlay 92% so the user feels "this is the past".

5. COMPOSER at the bottom shows an info hint above it: "网络恢复后会自动发送" in tiny grey.
   The composer itself is faintly desaturated; the send button shows a small clock badge instead of a paper plane.

ATMOSPHERE: gentle, never alarming. The user should feel "yuoyuo is patiently waiting with me" not "the app is broken".

Negative: no red warning, no scary modal, no error code, no "Connection lost!!!" exclamation, no full-screen takeover.
```

---

### 3.2 加载 / 空状态

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate the yuoyuo Empty / Loading state, 1024×1536. Show two stacked vignettes on the same canvas split horizontally (each 1024×768 area, divider hairline).

TOP — "Empty Chat" (when no messages yet):
- Centered painterly soft cloud with the yuoyuo gem floating gently.
- Below it, PingFang SC Medium 18 px: "我们刚认识，先聊点什么吧？"
- Three suggestion pills below (glass 55%, 14 px radius):
  "今天心情如何？" / "陪我说说话" / "给我讲个故事"

BOTTOM — "Loading State":
- A skeleton chat list with 3 shimmering placeholder bubbles (alternating left/right).
- The shimmer is a very soft pink-to-cream sweep, slow, not flashy.
- A tiny breathing 3-dot indicator in the header replaces the orb.

ATMOSPHERE: feels patient, like waiting for a friend to arrive.

Negative: no spinner wheel, no "Loading..." text in caps, no error icon, no grey-grey monochrome skeleton.
```

---

### 3.3 反馈组件三连（Toast / Modal / Sheet）

**Canvas**: 1536×1024

```text
[GLOBAL STYLE CONTRACT]

TASK: Generate a 3-vignette sheet showing yuoyuo's feedback components on a cream board, captioned.

VIGNETTE 1 — TOAST (small):
- A floating glass pill at the top center of a phone, 90% wide, 20 px radius, glass 75%.
- Left: small check icon pink. Text: "兑换成功，会员已激活。" (PingFang SC Medium 14 px).
- Below the phone, caption "Toast · 2.5s auto-dismiss".

VIGNETTE 2 — MODAL (centered confirm dialog):
- Phone with dimmed (60% black) background.
- A centered glass card 80% wide, 24 px radius, glass 90%.
- Title 18 px medium "确认退出登录？"
- Body 14 px grey "退出后需要重新通过邮箱链接登录。"
- Two stacked buttons: primary pink "确认退出" filled, secondary "取消" ghost.
- Caption "Modal · destructive but warm".

VIGNETTE 3 — BOTTOM SHEET (action sheet):
- Phone with the bottom half occupied by a rounded-top glass sheet (32 px top radius, glass 90%).
- A short grab handle at top.
- Title left-aligned in PingFang SC SemiBold 18 px "选择主题".
- Three options listed as rows with radio dots: "浅色" (selected pink dot) / "深色" / "跟随系统".
- A wide "完成" pink filled button at the bottom inside the sheet.
- Caption "Bottom Sheet · for option selection".

ATMOSPHERE: cohesive soft system, never jarring.

Negative: no harsh black overlay over 60%, no destructive red, no full-screen modal style.
```

---

## 5. 通用 Prompt 参数（提交给 GPT-image-2 时的设置）

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `model` | `gpt-image-2` 或当前最新 image 模型 | 同会话固定一个模型 |
| `size` | 见每节 Canvas | 屏幕 1024×1536，横版 1536×1024，图标 1024×1024 |
| `quality` | `high` | 全部用高质 |
| `style` | `vivid` 中性偏柔 | 不要强对比 |
| `output_format` | `png` | 保留透明（图标） |
| `background` | `auto`（图标用 `transparent`） | App Icon 也保留 cream 底，由 OS 蒙版 |
| `n` | 1（关键件 2） | App Icon、Style Tile 各出 2 张择优 |

---

## 6. 输出文件命名与归档

```
design_assets/
├── phase1_foundations/
│   ├── 01_style_tile.png
│   ├── 02_palette.png
│   ├── 03_typography.png
│   ├── 04_iconset.png
│   ├── 05_elevation_radius_glass.png
│   ├── 06_motion_storyboard.png
│   ├── 07_app_icon.png
│   └── 08_splash.png
├── phase2_screens/
│   ├── 09_home.png
│   ├── 10_chat_light.png
│   ├── 11_chat_dark.png
│   ├── 12_character.png
│   ├── 13_settings.png
│   ├── 14_login.png
│   ├── 15_redeem.png
│   └── 16_onboarding_3up.png
└── phase3_states/
    ├── 17_state_offline.png
    ├── 18_state_empty.png
    └── 19_components_feedback.png
```

放置位置（仓库内）：`web/design/source/`（不进打包，仅作版本管理 + 给 Claude 参考）。

---

## 7. 验收清单（每张图必过这 7 项）

1. **应用名拼写** — 出现的是 `yuoyuo`（全小写），**绝不**出现 `心屿 / Heart / YuoYuo / YUOYUO`。
2. **风格一致** — 色板、字号、阴影来自 Phase 1，不串味。
3. **负面词扫除** — 无 neon / 赛博 / Discord 紫 / QQ 绿 / 真人脸。
4. **可读性** — 中文字符无错字、无糊；emoji 不入图。
5. **iOS 安全区** — 状态栏 47 px、底部 34 px、刘海/胶囊不挡内容。
6. **触达可达** — 主按钮高度 ≥ 48 px，副按钮 ≥ 40 px。
7. **状态清晰** — 加载 / 空 / 错三态都有视觉，绝不白屏。

---

## 8. 下游交接（给 Claude 的 handoff 提示词模板）

每张图生成完后，配套这段 prompt 喂给下游 Claude（让它把图转成代码 / Design Token）：

```text
You are integrating a yuoyuo visual asset into the React 19 + Vite + Tailwind v4 codebase under web/.
Source asset: design_assets/<phase>/<filename>.png
Task: extract the visible tokens and produce:
1. CSS custom properties in web/src/styles/tokens.css (colors, radii, shadows, durations, easings).
2. Tailwind v4 @theme block to surface the tokens as utility classes.
3. A single Storybook-like demo file at web/src/preview/<name>.tsx that renders the screen using the tokens — do NOT slice the PNG; rebuild structure from semantic components.
4. Do not change WebSocket / store / API code. UI only.
5. Keep app name string literal as "yuoyuo" everywhere — never reintroduce 心屿/Heart in user-visible copy.
Verify against the acceptance checklist in docs/design/gpt_image2_visual_prompts.md §7.
```

---

## 9. 与开发循环的衔接

按你设计的循环：

```
GPT-image-2 (产视觉)
   ↓ 落到 design_assets/
Claude (产 token + 组件骨架)
   ↓ commit 到 feat/visual-<asset-id>
Mimo V2.5 (产文案 / TTS 校准)
   ↓ PR review
DeepSeek V4 (跑视觉回归 / 一致性检查)
   ↓
Claude Review (自审 + 修)
   ↓
真机测试 (PWA 安装 + Capacitor APK)
   ↓
Git Commit + PR
   ↓
下一资产（回到顶端）
```

每一张图 = 一条独立 feature 分支 = 一个独立可回滚的 PR。
Phase 1 共 8 个 PR，Phase 2 共 8 个 PR，Phase 3 共 3 个 PR，**合计 19 条独立可回滚交付单元**。

---

## 10. 一句话执行指令（粘贴给 GPT-image-2 即可开工）

> "依次生成 yuoyuo 视觉系统的 19 张资产。Phase 1 在前，Phase 2 在中，Phase 3 在后，每张图开始前先粘贴 §0.1 全局风格契约，然后粘贴该张图自己的 prompt 段。输出 PNG，遵照 §5 参数。应用名一律 lowercase `yuoyuo`，绝不使用 '心屿' 或 'Heart'。"
