# 06 交互规范（Interactions）— 颜色系统色板

> 该资产为静态规范展示画布，非可交互 App 界面。  
> 以下根据设计稿可见内容说明，设计稿未定义的交互均明确注明。

---

## 总体声明

该画布（Color Palette / 色板）是**设计工具中的规范文档画布**，不是用户可以交互的 App 界面。  
因此，绝大多数传统 UI 交互（点击、滑动、过渡等）均不适用于本资产本身。

本文件的价值在于：基于设计稿的色板规范，**定义当这些颜色 / 玻璃效果应用于真实 App 组件时**应具备的交互行为。

---

## 进入动画（Entrance Animation）

**设计稿未定义。**

推荐实现（供开发参考）：
- 色阶行从上到下依次 fade-in + slide-up，每行 stagger 延迟 20–30 ms
- 语义色卡片从右侧 fade-in，延迟 200 ms
- 玻璃叠加卡片从下方浮入（translateY 16px → 0），duration 400 ms，easing ease-out

---

## 退出动画（Exit Animation）

**设计稿未定义。**  
不适用（规范画布无退出场景）。

---

## Hover 状态

**设计稿未定义。**

推荐实现（供开发参考，用于 Web / Desktop 端）：

### 色阶行 Hover
- 色块轻微放大：`transform: scale(1.05)`
- 过渡时长：150 ms，easing ease-out
- 鼠标悬停时显示 Tooltip：展示色阶级别、HEX 值、RGB 值
- Tooltip 背景：`rgba(58,58,74,0.9)`，文字白色，圆角 8 px（估算值）

### 语义色卡片 Hover
- 卡片轻微上浮：`transform: translateY(-2px)`
- 卡片阴影加深：shadow 增强约 1.5x
- 过渡时长：200 ms

### 玻璃叠加卡片 Hover
- 边框白色透明度从约 30% 提升至约 60%（估算值）
- 过渡时长：200 ms

---

## Pressed / Active 状态

**设计稿未定义。**

推荐实现（供开发参考，用于移动端触摸）：

### 色阶行 Pressed
- 色块轻压缩：`transform: scale(0.97)`
- 过渡时长：100 ms

### 语义色卡片 Pressed
- 整体下沉：`transform: translateY(1px) scale(0.99)`
- 过渡时长：100 ms

---

## Selected / Active 状态

**设计稿未定义。**

推荐实现（用于色板选色工具场景）：
- 选中色阶行：外部显示 2px 圆角边框，颜色为对应色系 600 级别色
- 勾选图标：右侧显示白色勾号

---

## Disabled 状态

**设计稿未定义。**  
推荐：`opacity: 0.4`，`pointer-events: none`

---

## Loading 状态

**设计稿未定义。**  
推荐：色块使用 Skeleton 占位（灰色渐变闪烁动画）

---

## Error 状态

**设计稿未定义。**  
不适用（色板无数据加载失败场景）

---

## Empty 状态

**设计稿未定义。**  
不适用（色板为静态内容，无空态）

---

## Skeleton / Placeholder 状态

**设计稿未定义。**

推荐实现（色板数据异步加载时）：
- 色块位置显示 Skeleton 矩形（圆角一致，颜色 `#F6D5B4`）
- Shimmer 动画：从左到右渐变扫过，duration 1.5 s，循环
- HEX 文字位置显示短横线占位

---

## 滚动（Scroll）

**设计稿未定义。**  
不适用（该画布为横向展示，完整内容在一屏内）

若移植到移动端（竖屏），推荐：
- 纵向滚动，`scroll-behavior: smooth`
- 色柱改为横向 ScrollView，可左右滑动

---

## 复制交互（Copy Interaction）

**设计稿未定义。**

推荐实现（开发者/设计师色板工具常用功能）：
- 点击 HEX 值文字：复制到剪贴板，显示短暂 Toast "已复制 #FFB7C5"
- Toast 样式：玻璃背景 `rgba(255,255,255,0.9)`，黑色文字，duration 2 s，顶部居中

---

## 玻璃叠加卡片交互

**设计稿未定义。**

推荐（交互式色板工具）：
- 4个玻璃卡片的透明度可通过 Slider 实时调节（35%→90%）
- Slider 颜色使用 `#FFB7C5`（主色）

---

## 过渡与动画规范（Transition）

**设计稿未定义具体数值。**

基于 yuoyuo 品牌风格推荐：

| 场景 | Duration | Easing | 效果 |
|------|----------|--------|------|
| Hover 进入 | 150 ms | ease-out | 元素微微放大/上浮 |
| Hover 退出 | 150 ms | ease-in | 回到原始状态 |
| Pressed | 100 ms | ease-in-out | 元素轻压 |
| 卡片出现 | 300–400 ms | ease-out | fade + slide |
| Stagger 列表 | 20–30 ms/item | ease-out | 色阶行依次出现 |
| Toast 进入 | 200 ms | spring | 从顶部弹入 |
| Toast 退出 | 150 ms | ease-in | 淡出 |

---

## 键盘导航

**设计稿未定义。**

推荐（无障碍要求）：
- Tab 键：在色阶行间移动焦点
- Enter / Space：触发复制 HEX 值
- Arrow Keys：上下移动色阶
- Escape：关闭 Tooltip

---

## 手势交互（Mobile Touch）

**设计稿未定义。**

推荐（移动端实现时）：
- 长按色块：显示色值详情 Modal（含 HEX / RGB / HSL）
- 左右滑动：切换不同色系（若移动端改版为 Swipe 布局）

---

## 总结

本资产为静态设计规范画布，无原生交互定义。  
以上所有交互推荐均为**yuoyuo 设计系统级别的通用交互规范建议**，供后续基于该色板构建真实组件时参考。  
正式交互规范应在具体 App 界面（Chat Screen / Voice Call 等）对应规范文件中定义。
