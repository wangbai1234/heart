# 10 验收 Checklist（Acceptance）

## 目标：整体视觉一致度 ≥ 95%

本 Checklist 适用于前端实现完成后，与 Motion Storyboard 设计稿进行 Pixel Perfect 对比验收。

---

## 验收方式说明

- 使用截图与设计稿叠加对比（推荐 Figma Dev Mode 或 Overlay 工具）
- 数值使用设计稿估算值，允许 ±2px 误差
- 动效参数使用开发者工具 Animation Inspector 检查
- 标注「估算值」的尺寸以视觉匹配为准

---

## A. 画布 / 整体布局

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 画布背景色为 #FFF8F3（奶白/Surface），非纯白 | 03_design_tokens |
| □ | 4 个设备帧水平等间距排列，间距均匀 | 02_layout |
| □ | 标题 "yuoyuo · Motion" 左对齐，字体 SF Pro Rounded，约 28px | 02_layout |
| □ | 标题颜色为 #3A3A4A（Ink） | 03_design_tokens |
| □ | 帧间箭头为粉色（#FFB7C5），带时长文字标注 | 05_assets |
| □ | 底部说明区序号圆圈为 #FFB7C5 填充，白色数字 | 04_components |
| □ | 底部说明区标题字号约 16px，Semibold | 03_design_tokens |
| □ | 底部说明区描述文字字号约 13px，Regular，#6B6B7A | 03_design_tokens |

---

## B. 设备框架

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 设备框为白色边框，圆角约 47px | 02_layout |
| □ | 设备框比例符合 iPhone 14（约 390×844 逻辑像素比例） | 02_layout |
| □ | 设备框有轻微投影（阴影 blur 约 24px，y offset 4px） | 03_design_tokens |
| □ | 状态栏显示 9:41、信号、WiFi、电量图标 | 04_components |
| □ | 状态栏高度约 44px | 02_layout |

---

## C. 导航栏（ChatNavBar）

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 导航栏高度约 56px | 02_layout |
| □ | 返回箭头 `<` 位于左侧，距左边约 16px | 02_layout |
| □ | 情绪球位于导航栏中央偏左，正常态直径约 36px | 04_components |
| □ | 昵称"悠悠"字号约 15px，Semibold，#3A3A4A | 03_design_tokens |
| □ | "在线"文字字号约 11px，绿色（#7DCE7D） | 03_design_tokens |
| □ | `···` 菜单按钮位于右侧，距右边约 16px | 02_layout |

---

## D. 情绪球（EmotionOrb）— 重点验收

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 帧①③中情绪球直径约 36px（正常态） | 04_components |
| □ | 帧②情绪球放大展示约 80px，用于说明脉冲效果 | 04_components |
| □ | 情绪球为圆形，渐变从白色核心→天蓝→薰衣草→樱花粉 | 03_design_tokens |
| □ | 情绪球外有多彩光晕（紫/蓝/粉），blur 约 20px | 03_design_tokens |
| □ | 情绪球脉冲动效：scale 1.0 → 1.06 → 1.0，时长 1200ms | 06_interactions |
| □ | 情绪球脉冲缓动：ease-in-out | 06_interactions |
| □ | 情绪球脉冲无限循环（infinite） | 06_interactions |
| □ | 光晕亮度随 scale 同步变化（scale 最大时光晕最亮） | 06_interactions |

---

## E. AI 消息气泡（AIMessageBubble）

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | AI 气泡左对齐，头像在左侧 | 02_layout |
| □ | 头像圆形，直径约 40px | 04_components |
| □ | 头像为二次元少女插画（粉色发色） | 05_assets |
| □ | 气泡背景为白色/极浅毛玻璃 | 03_design_tokens |
| □ | 气泡圆角约 16px，左上角圆角较小 | 03_design_tokens |
| □ | 气泡内 Padding 约 12px（水平）/ 10px（垂直） | 02_layout |
| □ | 消息文字字号约 14px，Regular，#3A3A4A | 03_design_tokens |
| □ | 时间戳右下对齐，约 11px，#AAAAAA | 03_design_tokens |
| □ | 气泡有轻微投影（blur 8px，y 2px） | 03_design_tokens |

---

## F. 气泡绽放动效（Bubble Bloom）— 重点验收

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 新气泡出现时 scale 从 0.92 起始（而非 1.0） | 06_interactions |
| □ | scale 动效终点为 1.0，无弹超（不超过 1.0） | 06_interactions |
| □ | opacity 从 0 到 1.0 同步进行 | 06_interactions |
| □ | 总时长 300ms | 06_interactions |
| □ | 缓动使用 ease-out（快进慢出） | 06_interactions |
| □ | 气泡出现时伴随粉色光晕（cherry pink glow）散射 | 06_interactions |
| □ | 光晕在 150ms 内淡出消失 | 06_interactions |
| □ | 气泡绽放不影响其他已有气泡的位置 | 06_interactions |

---

## G. 用户消息气泡（UserMessageBubble）

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 用户气泡右对齐，无头像 | 02_layout |
| □ | 气泡背景为浅粉色（约 #FFD6DF） | 03_design_tokens |
| □ | 气泡圆角约 20px，右上角圆角较小 | 03_design_tokens |
| □ | 时间戳含 ✓ 已送达标志，右下对齐 | 04_components |
| □ | 气泡有粉色投影（blur 12px，y 2px，rgba(255,183,197,0.20)） | 03_design_tokens |

---

## H. 输入栏（InputBar）

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 输入栏高度约 52px | 02_layout |
| □ | 输入栏背景为毛玻璃/极浅灰 | 03_design_tokens |
| □ | 输入框圆角约 24px | 03_design_tokens |
| □ | 麦克风图标在左侧，约 24px，灰色 | 05_assets |
| □ | 占位文字"输入消息..."，约 14px，#BBBBCC | 03_design_tokens |
| □ | 加号按钮圆形，直径约 36px，#FFB7C5 | 04_components |
| □ | 加号按钮图标为白色 + 号 | 05_assets |
| □ | 加号按钮有粉色投影 | 03_design_tokens |
| □ | 输入栏上方有细分割线（rgba(0,0,0,0.06)） | 03_design_tokens |

---

## I. 语音波（VoiceWave）— 重点验收

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 语音播放时输入栏上方出现 5 个圆形波点 | 04_components |
| □ | 波点颜色从左到右由 #FFB7C5 渐变至 #C8B6FF | 03_design_tokens |
| □ | 波点直径约 8px | 04_components |
| □ | 波点间距约 6px | 04_components |
| □ | 中心点振幅最高（视觉上为竖线/高点） | 06_interactions |
| □ | 振幅变化实时跟随 AI 语音 | 06_interactions |
| □ | 振幅最小约 4px，最大约 24px | 06_interactions |
| □ | 动效为 linear 缓动（实时映射，非预设） | 06_interactions |

---

## J. 页面过渡（Page Transition）— 重点验收

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 点击对话条目时聊天页从屏幕底部向上滑入 | 06_interactions |
| □ | 顶层 Sheet 动效时长 400ms | 06_interactions |
| □ | 底层首页 translateY 变化：0 → +8px | 06_interactions |
| □ | 底层首页 scale 变化：1.0 → 0.99 | 06_interactions |
| □ | 底层首页亮度（brightness）变化：1.0 → 0.92 | 06_interactions |
| □ | 三种变化（translateY/scale/brightness）同步发生，时长同为 400ms | 06_interactions |
| □ | 顶层聊天页顶部有拖拽手柄提示 | 06_interactions |
| □ | 过渡缓动使用 ease-in-out / Apple Spring | 06_interactions |
| □ | 过渡完成后底层首页不可见（被顶层完全覆盖） | 06_interactions |

---

## K. 消息列表布局

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 消息气泡垂直排列，最新消息在最下方 | 02_layout |
| □ | AI 消息与用户消息交替排列，左右对齐正确 | 02_layout |
| □ | 消息气泡间距约 8–12px | 02_layout |
| □ | 消息列表区域上下 Padding 约 16px | 02_layout |
| □ | 头像与气泡间距约 8px | 02_layout |

---

## L. 安全区域（Safe Area）

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 顶部 Safe Area 47px 内无可交互内容 | 02_layout |
| □ | 底部 Home Indicator 区域（34px）不被 InputBar 遮挡 | 02_layout |
| □ | 输入栏底部距 Home Indicator 有适当间距 | 02_layout |

---

## M. 视觉权重与整体氛围

| # | 验收项 | 对应规范 |
|---|--------|---------|
| □ | 整体配色以粉色（#FFB7C5）为主调，无鲜明对比色干扰 | 03_design_tokens |
| □ | 背景为奶白（#FFF8F3），非纯白，有温暖感 | 03_design_tokens |
| □ | 情绪球带有朦胧光晕，视觉上有"梦幻感" | 03_design_tokens |
| □ | 所有圆角充足（≥16px），无生硬直角边缘 | 03_design_tokens |
| □ | 字体为系统中文字体（PingFang SC），无杂字体 | 03_design_tokens |
| □ | 整体视觉风格符合"二次元愈系"设计语言 | 01_overview |
| □ | 动效节奏柔和，无突兀抖动或过度动效 | 06_interactions |
| □ | 所有动效时长在合理范围内（≤1200ms） | 03_design_tokens |

---

## 验收评分方法

| 评分区间 | 结论 |
|---------|------|
| ≥95% 通过 | ✅ 验收通过，可上线 |
| 85–94% 通过 | ⚠️ 有明显偏差，需修复 2–3 项关键问题后重验 |
| <85% 通过 | ❌ 验收不通过，需返工并重新提交验收 |

**关键项（P0）**：气泡绽放、情绪球脉冲、语音波、页面过渡动效参数的任意一项不通过，直接判定整体不通过。
