# 09 Accessibility — 加载 / 空状态

## 触摸目标（Touch Targets）

| 元素 | 视觉尺寸 | 触摸目标尺寸 | 是否达标（≥44×44pt）|
|------|---------|------------|-------------------|
| 返回按钮 "<" | ~24×24px | 48×48px（含热区） | 达标 |
| 角色头像（如可点击）| ~88px 圆 | 88×88px | 达标 |
| 电话按钮 | ~44×44px | 44×44px | 达标（最低线）|
| 更多菜单"···" | ~24×24px | 48×48px | 达标 |
| Suggestion Pill 1 | ~180×64px | 180×64px | 达标 |
| Suggestion Pill 2 | ~160×64px | 160×64px | 达标 |
| Suggestion Pill 3 | ~200×64px | 200×64px | 达标 |
| "+" 按钮 | ~64×64px | 64×64px | 达标 |
| 麦克风按钮 | ~64×64px | 64×64px | 达标 |
| 输入框 | 全宽×64px | 全宽×64px | 达标 |

**注意：** 电话按钮视觉尺寸偏小，若实际渲染低于 44pt，需在实现时增加透明热区（Padding / HitSlop）。

---

## 颜色对比度（WCAG 2.1）

### 文字对比度检验

| 前景色 | 背景色 | 对比比率（估算）| 等级 | 是否达标 |
|--------|--------|--------------|------|---------|
| `#3A3A4A`（引导文字）| `#FDF0EE`（页面背景） | ~9.5:1（估算）| AAA | 达标 |
| `#3A3A4A`（角色名）| `#FDF0EE` | ~9.5:1 | AAA | 达标 |
| `#A07888`（副标题）| `#FDF0EE` | ~4.2:1（估算）| AA | 达标（正文）|
| `#C8B6C8`（占位文字）| `#FDF0EE` | ~2.8:1（估算）| — | **不达标（仅装饰性）** |
| `#3A3A4A`（Pill 文字）| `rgba(255,255,255,0.80)` | ~9:1（估算）| AAA | 达标 |
| `#8A8A9A`（图标）| `#FDF0EE` | ~3.2:1（估算）| AA（大号图标可接受）| 边界 |

**说明：**
- 输入框占位文字颜色 `#C8B6C8` 对比度不足。此为 WCAG 豁免情形（placeholder 不要求 AA），但建议提升到 `#A090A0` 以改善低视力用户体验。
- 图标颜色 `#8A8A9A` 在纯装饰性场景可接受，交互图标（返回箭头、电话）建议对比度提升至 3:1 以上（满足非文本 AA 标准），当前估算值略超 3:1，需实测确认。

---

## ARIA 规范

### 空聊天状态

| 元素 | ARIA 属性建议 |
|------|-------------|
| 整体空状态容器 | `role="main"` 或 `aria-label="对话开始区域"` |
| 心形插画（纯装饰）| `aria-hidden="true"` |
| 云朵背景（纯装饰）| `aria-hidden="true"` |
| 引导文字 | 自动被读取（无需特殊 ARIA）；或 `aria-label="页面提示：我们刚认识，先聊点什么吧？"` |
| 建议 Pill 行容器 | `role="group"` `aria-label="快捷发言建议"` |
| Pill 1 | `role="button"` `aria-label="发送：今天心情如何？"` |
| Pill 2 | `role="button"` `aria-label="发送：陪我说话"` |
| Pill 3 | `role="button"` `aria-label="发送：给我讲个故事"` |

### 骨架加载状态

| 元素 | ARIA 属性建议 |
|------|-------------|
| 骨架聊天区整体容器 | `role="status"` `aria-label="正在加载消息，请稍候"` `aria-live="polite"` `aria-busy="true"` |
| 骨架气泡（单个）| `aria-hidden="true"`（视觉结构，无实际内容）|
| Shimmer 动画层 | `aria-hidden="true"` |
| Header 打点动画"···" | `aria-label="悠悠正在输入中"` `aria-live="polite"` |

### 全局 Header

| 元素 | ARIA 属性建议 |
|------|-------------|
| 整体 Header | `role="banner"` |
| 返回按钮 | `role="button"` `aria-label="返回"` |
| 角色头像（若可点击）| `role="button"` `aria-label="查看悠悠详情"` |
| 角色名"悠悠" | 自动读取（`<h1>` 或 `<p>`，取决于语义层级）|
| 状态文字（空状态）| `aria-label="状态：在线，愿意倾听你的一切"` |
| 状态文字（加载）| `aria-label="悠悠正在输入"` `aria-live="assertive"` |
| 电话按钮 | `role="button"` `aria-label="发起语音通话"` |
| 更多菜单 | `role="button"` `aria-label="更多选项"` `aria-haspopup="true"` |

### InputBar

| 元素 | ARIA 属性建议 |
|------|-------------|
| 输入框 | `role="textbox"` `aria-label="输入消息"` `aria-multiline="false"` `aria-placeholder="想对悠悠说什么呢..."` |
| "+" 按钮 | `role="button"` `aria-label="添加附件"` |
| 麦克风按钮 | `role="button"` `aria-label="语音输入"` 或 `aria-label="切换语音输入模式"` |

---

## Screen Reader（屏幕阅读器）状态播报规范

### 空聊天状态 — 进入播报

**VoiceOver / TalkBack 推荐播报顺序：**

```
1. "悠悠，对话页面"  ← 页面标题
2. "在线，愿意倾听你的一切"  ← Header 副标题
3. "我们刚认识，先聊点什么吧？"  ← 引导文字
4. "快捷发言建议，共 3 项"  ← Pill 容器
5. "发送：今天心情如何？，按钮"  ← Pill 1
6. "发送：陪我说话，按钮"  ← Pill 2
7. "发送：给我讲个故事，按钮"  ← Pill 3
8. "输入消息"  ← 输入框
```

**省略：** 插画（aria-hidden）、云朵背景（aria-hidden）、Shimmer 层（aria-hidden）

### 加载状态 — 变化播报

**切换到加载状态时 aria-live 播报：**

```
polite: "正在加载消息，请稍候"  ← SkeletonChatArea (role="status")
assertive/polite: "悠悠正在输入"  ← Header StatusText 打点
```

**骨架气泡本身：** 全部 `aria-hidden="true"`，不播报骨架结构

### 消息到达 — 恢复播报

```
polite: "消息已加载"  ← SkeletonChatArea aria-busy="false"
        然后按消息顺序自动播报新气泡内容
```

---

## 键盘导航（移动端蓝牙键盘 / 外接键盘）

| 操作 | 行为 |
|------|------|
| Tab | 顺序聚焦：返回按钮 → 头像 → 电话按钮 → 更多菜单 → Pill 1 → Pill 2 → Pill 3 → "+"按钮 → 输入框 → 麦克风 |
| Shift+Tab | 反向聚焦 |
| Space / Enter（Pill 聚焦时）| 触发 Pill 发送 |
| Space / Enter（麦克风聚焦时）| 切换语音模式 |
| Escape | 返回上一页（同 Back 按钮）|
| 方向键（Pill 组内）| 建议：Left/Right 在三个 Pill 间切换焦点（roving tabindex 模式）|

---

## 移动端操作建议

| 建议 | 原因 |
|------|------|
| Pill 提供充足的触摸热区（高度不低于 44pt）| 拇指操作区域覆盖 |
| 单手操作可达性：Pill 行放置于屏幕下 2/3 区域 | 设计稿已符合（Pill 在引导文字下方，接近拇指舒适区）|
| 骨架加载状态避免任何需要点击的元素出现在骨架区 | 防止误触骨架 |
| 输入框 Padding 不小于 44pt 高 | 拇指轻触可激活 |
| 麦克风按钮按住录音时避免和 Home Indicator 重叠 | Safe Area Bottom 34pt 须保留 |
| 减少动画选项（Reduce Motion）支持 | `@media (prefers-reduced-motion: reduce)` 时 Shimmer 和浮动动画应停止或简化为静态占位 |

---

## Reduce Motion 处理规范

| 动画 | 正常 | Reduce Motion 时 |
|------|------|----------------|
| GemHeart 浮动 | Y 轴 ±6px 循环 | 静止，不浮动 |
| Shimmer 扫光 | 线性扫光 | 替换为静态低透明度覆盖层（`opacity: 0.4`）|
| 打点动画"···" | 顺序淡入 | 显示静态"..."，不动 |
| Pill 进入动画 | 渐入+上移 | 直接显示（no fade/slide）|
| 页面进入动画 | 渐入 | 直接显示 |
