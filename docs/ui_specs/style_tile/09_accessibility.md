# 09 无障碍规格 — Style Tile（视觉总谱）

> Style Tile 为静态参考画布，不可交互，本身不需要无障碍实现。
> 本文件基于 Style Tile 中展示的 UI 元素，为实际 App 组件的无障碍规格提供指导原则。

---

## 1. 点击区域（Touch Target）

### 规范要求

- iOS HIG 最低点击区域：**44×44px**
- Material Design 建议：**48×48dp**
- yuoyuo 采用值：最小 **48×48px**（逻辑像素）

### Style Tile 元素评估

| 元素 | 估算显示尺寸 | 是否满足 44px | 建议 |
|------|-------------|--------------|------|
| Primary 按钮（"确认"） | ~200×48px | ✅ 满足 | — |
| Secondary 按钮（"取消"） | ~200×48px | ✅ 满足 | — |
| Text Link（"了解更多"） | ~80×24px（估算值） | ❌ 不满足 | 增加 padding 至 44px 高，或扩大点击区域 |
| 底部 NavTabItem | ~(全宽/5)×64px（估算值） | ✅ 满足 | — |
| 头像圆形 | ~88×88px | ✅ 满足 | — |
| 等级徽章（"Lv.12"） | ~32×20px（估算值） | ❌ 不满足 | 如可点击，需扩大点击区域；或设为不可点击展示元素 |
| 统计数据 StatItem | ~80×40px（估算值） | ❌ 略小 | 如可点击，增加垂直 padding |
| 气泡（聊天） | 随内容动态高度 | ✅ 通常满足 | 确保最小高度 ≥ 44px |

---

## 2. 颜色对比度（Color Contrast）

### 评估标准

- WCAG 2.1 AA 级：正常文字 ≥ 4.5:1，大文字（18px Bold 以上）≥ 3:1
- WCAG 2.1 AAA 级：正常文字 ≥ 7:1（推荐但不强制）

### 关键颜色组合分析

| 文字颜色 | 背景颜色 | 对比度（估算） | 状态 |
|---------|---------|--------------|------|
| `#3A3A4A`（ink） on `#FFF8F3`（cream bg） | — | ~10.5:1（估算值） | ✅ AA + AAA |
| `#3A3A4A` on `rgba(255,255,255,0.80)` 卡片 | — | ~10.5:1（估算值） | ✅ AA + AAA |
| `#FFB7C5`（primary）on `#FFF8F3` | — | ~2.8:1（估算值） | ❌ 不满足 AA（正文使用禁止） |
| `#FFB7C5` on `rgba(255,255,255,0.80)` | — | ~2.8:1（估算值） | ❌ 不满足（仅用于装饰性元素） |
| `#FFFFFF` on `#FFB7C5` 按钮 | — | ~2.8:1（估算值） | ❌ 不满足 AA |
| `#3A3A4A` on `#A7C7E7` 用户气泡 | — | ~4.8:1（估算值） | ✅ 满足 AA |
| `#C8B6FF`（link）on `#FFF8F3` | — | ~3.2:1（估算值） | ❌ 不满足（小字链接需加粗或加深） |
| 时间戳 `~#9A9AB0` on `#FFF8F3` | — | ~3.8:1（估算值） | ❌ 勉强/不满足（次级信息可接受，但需关注） |

### 高风险建议

> 警告：Primary 按钮（粉底白字）和 Text Link（紫色链接）的颜色对比度不满足 WCAG AA 标准。

建议处理方案：
1. **Primary 按钮**：按钮文字从白色改为 `#6B3A4A`（深玫红，估算值）以提升对比度；或接受 iOS 视觉风格优先的妥协，并在产品可访问性说明中声明。
2. **Text Link**：将 `#C8B6FF` 加深至 `#8B70D4`（估算值），在 cream 背景上满足 4.5:1。
3. **时间戳等次级文字**：字号小于 14px 时需满足 4.5:1，建议使用 `#7A7A8A` 而非更浅的灰色。

---

## 3. 焦点状态（Focus State）

> Style Tile 未定义焦点状态，以下为设计系统推断。

| 元素 | 焦点样式建议 |
|------|------------|
| 所有可交互按钮 | `outline: 2px solid #A7C7E7; outline-offset: 2px`（天蓝色 Focus Ring，估算值） |
| 气泡（长按操作时） | 背景微暗（`rgba(0,0,0,0.05)` overlay） |
| 底部 NavTabItem | Tab 区域高亮（蓝色 Focus Ring） |
| 输入框（聊天输入） | `border: 2px solid #FFB7C5`（粉色描边） |

**移动端说明：** iOS / Android 原生会处理焦点样式，React Native 默认无 Focus Ring，无障碍用户使用 Switch Control 或 VoiceOver 时需测试 focus 顺序。

---

## 4. 文本可读性

| 建议 | 说明 |
|------|------|
| 最小正文字号 ≥ 14px | Style Tile 气泡文字约 14px，满足 |
| 最小辅助文字字号 ≥ 11px | 图标标签约 11px，边界值，建议 12px |
| 行高 ≥ 1.4 | Style Tile 推断行高 1.4–1.5，满足 |
| 最大行长 ≤ 80 字符 | 移动端单列气泡最大约 20–24 个汉字，满足 |
| 不使用纯装饰文字颜色传达信息 | 确保"已读 ✓" 颜色变化有其他辅助指示（如文字说明） |

---

## 5. ARIA 建议

> 以下为 React Native 对应属性（iOS 对应 accessibilityLabel / accessibilityRole）。

| 元素 | aria-label / accessibilityLabel | role |
|------|--------------------------------|------|
| AppLogo "yuoyuo" | `"yuoyuo 应用Logo"` | `none`（装饰性） |
| Primary 按钮 | `"确认"` | `button` |
| Secondary 按钮 | `"取消"` | `button` |
| Text Link | `"了解更多"` | `link` |
| AI 气泡 | `"yuoyuo 说：[消息内容]，发送于 09:30"` | `text` |
| 用户气泡 | `"你说：[消息内容]，发送于 09:32，已读"` | `text` |
| CharacterAvatar | `"yuoyuo 角色头像"` | `image` |
| NavTabItem 首页 | `"首页"` | `tab` |
| NavTabItem 聊天 | `"聊天"` | `tab` |
| NavTabItem 麦克风关闭 | `"麦克风已关闭，点击开启"` | `button` |
| NavTabItem 礼物 | `"礼物兑换"` | `tab` |
| NavTabItem 齿轮 | `"设置"` | `tab` |
| NavTabItem 个人资料 | `"个人资料"` | `tab` |
| LevelBadge | `"等级 12"` | `text` |
| 爱心统计 | `"陪伴天数：1250 天"` | `text` |
| 星星统计 | `"温暖时刻：3560 次"` | `text` |
| CheckTick | `"已读"` | `text`（合并到气泡 label） |
| 底部插画 | `"梦幻城堡花园装饰插画"` | `image`（decorative，可设 `accessibilityIgnoresInvertColors: false`） |

---

## 6. Keyboard Navigation（键盘导航）

> 主要适用于 iPad 外接键盘 + Web 端。

| 规则 | 说明 |
|------|------|
| Tab 顺序 | 从上至下、从左至右，与视觉阅读顺序一致 |
| 底部 NavBar | Tab / Shift+Tab 可在 5 个 Tab 间切换 |
| 按钮 | Enter / Space 触发，与点击等效 |
| 气泡长按菜单 | 通过 Context Menu 键（键盘右键）触发 |
| Escape | 关闭模态、取消输入焦点 |

---

## 7. Screen Reader 指南（VoiceOver / TalkBack）

| 规则 | 说明 |
|------|------|
| 图标 + 文字组合 | 读出文字标签即可，图标设为 `accessibilityElementsHidden: true` |
| 装饰性背景插画 | 设为 `accessible: false`，不读出 |
| 颜色椭圆（Style Tile） | 读出颜色名称（"樱花粉 #FFB7C5"），仅文档用途 |
| 时间戳 | 可选：合并到气泡 label 读出，减少焦点停顿 |
| 新消息到达 | 使用 `accessibilityLiveRegion: "polite"` 通知 |
| 消息已读状态变化 | 使用 `accessibilityAnnouncement("消息已读")` |

---

## 8. 移动端操作建议

| 建议 | 说明 |
|------|------|
| 单手操作优化 | 底部 NavBar 位于屏幕底部，拇指热区友好 |
| 手势冲突避免 | 气泡长按勿与系统手势（边缘滑动返回）冲突，气泡左边距 ≥ 20px |
| 动效降低选项 | 支持系统"减少动态效果"设置（`prefers-reduced-motion`），关闭樱花飘落、星点闪烁等装饰动效 |
| 高对比度模式 | 当系统开启高对比度时，Glass 毛玻璃背景降级为纯白 `#FFFFFF`，减少透明度带来的可读性问题 |
| 字体大小缩放 | 支持系统字体大小设置（`accessibilityLargeContentViewer`），布局在最大字号下不发生溢出 |
| 色盲友好 | 已读 ✓ 状态不仅依赖颜色，还需有形态差异（勾形 vs 无勾） |
