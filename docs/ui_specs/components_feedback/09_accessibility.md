# 09 Accessibility — 无障碍规范

## 触摸目标

### 最小触摸目标要求

| 标准 | 要求 |
|------|------|
| Apple HIG | 44×44 pt 最小触摸区域 |
| Material Design 3 | 48×48 dp 最小 |
| WCAG 2.5.5 | 44×44 CSS px（AAA 级） |
| WCAG 2.5.8 (2.2) | 24×24 CSS px（AA 级） |

### 各组件触摸目标评估

| 组件 | 实测/估算尺寸 | 合规状态 |
|------|-------------|---------|
| PrimaryButton "确认退出" / "完成" | ≈48px 高，全宽 | 合规（超出 44px） |
| SecondaryButton "取消" | ≈48px 高，全宽 | 合规 |
| RadioOption 行 | ≈44px 高，全宽 | 合规 |
| Toast 自身（可点击关闭） | ≈44px 高 | 合规 |
| ChatNavBar 图标（电话/更多） | ≈22px 图标，需扩展点击热区至 44px | 需扩展热区 |
| ChatInputBar 语音按钮 | ≈32px，需扩展热区至 44px | 需扩展热区 |
| ChatInputBar 加号按钮 | ≈32px，需扩展热区至 44px | 需扩展热区 |
| DragHandle | ≈36×4px，建议扩展可拖动区域高度至 24px | 建议扩展 |

---

## 颜色对比度

### WCAG 2.1 AA 标准：正文≥4.5:1，大文字≥3:1

| 文字 | 前景 | 背景 | 对比度（估算） | 状态 |
|------|------|------|-------------|------|
| Toast "兑换成功…" | `#3A3A4A` | `#FFFFFF` | ≈12.5:1 | 合规 |
| Modal 标题"确认退出登录？" | `#3A3A4A` | `#FFFFFF` | ≈12.5:1 | 合规 |
| Modal 副标说明 | `#888888` | `#FFFFFF` | ≈3.5:1 | **边缘（小文字不合规，大文字可能合规）** |
| Modal "确认退出"按钮 | `#FFFFFF` | `#FF8FA3`（渐变终点） | ≈2.9:1 | **不合规（需验证渐变区域）** |
| Modal "取消"按钮 | `#3A3A4A` | `#FFFFFF` | ≈12.5:1 | 合规 |
| Sheet 标题"选择主题" | `#3A3A4A` | `#FFFFFF` | ≈12.5:1 | 合规 |
| Sheet 选项"浅色/深色/跟随系统" | `#3A3A4A` | `#FFFFFF` | ≈12.5:1 | 合规 |
| Sheet "完成"按钮 | `#FFFFFF` | `#FF8FA3` | ≈2.9:1 | **不合规（需验证或使用较深粉色）** |
| NavBar 副标 | `#888888` | `≈#FFF5F8` | ≈3.4:1 | **边缘（小文字需注意）** |

### 对比度改进建议

1. 主操作按钮（"确认退出"/"完成"）文字白色与粉色背景对比度不足 4.5:1：
   - 建议加深按钮背景至 `#E8637A`（深粉红）或增加文字阴影 `text-shadow: 0 1px 2px rgba(0,0,0,0.2)`
   - 或将文字颜色改为 `#3A3A4A`（前提：渐变背景足够浅）

2. Modal 副标 `#888888`：
   - 若字号 < 18px（非加粗），需对比度 ≥ 4.5:1，建议加深至 `#666666`（约 4.5:1）

---

## ARIA 属性规范

### Toast

```
role="status"
aria-live="assertive"
aria-atomic="true"
```

| 属性 | 说明 |
|------|------|
| `role="status"` | 状态通知，不打断朗读 |
| `aria-live="assertive"` | 立即播报（成功/失败信息优先级高） |
| `aria-atomic="true"` | 整个 Toast 内容作为一个单元播报 |

**建议**：图标仅装饰性，`aria-hidden="true"` 隐藏图标，文字节点完整传达语义。

---

### ScrimOverlay

```
aria-hidden="true"
```

遮罩层为视觉装饰，屏幕阅读器无需感知。

---

### Modal

```
role="dialog"
aria-modal="true"
aria-labelledby="modal-title-id"
aria-describedby="modal-body-id"
```

| 属性 | 说明 |
|------|------|
| `role="dialog"` | 标识为对话框 |
| `aria-modal="true"` | 告知辅助技术背景内容被屏蔽 |
| `aria-labelledby` | 指向标题元素 ID |
| `aria-describedby` | 指向说明文字元素 ID |

**焦点管理**：
- Modal 打开时，焦点自动移至 Modal 内（建议移至标题或第一个可交互元素）
- Modal 内焦点循环（Focus Trap），不能 Tab 到背景内容
- Modal 关闭时，焦点返回触发按钮

**背景元素**：Modal 激活时，背景所有可交互元素设置 `aria-hidden="true"`（或使用 `inert` 属性）

---

### BottomSheet

```
role="dialog"
aria-modal="true"
aria-labelledby="sheet-title-id"
```

| 属性 | 说明 |
|------|------|
| `role="dialog"` | 标识为对话框（Sheet 是模态对话框的一种形式） |
| `aria-modal="true"` | 背景内容被屏蔽 |
| `aria-labelledby` | 指向"选择主题"标题 ID |

**焦点管理**：同 Modal，Sheet 内 Focus Trap，关闭后焦点返回触发元素

---

### RadioGroup / RadioOption

```
role="radiogroup"
aria-labelledby="radiogroup-label-id"

role="radio"
aria-checked="true" (选中)
aria-checked="false" (未选中)
tabindex="0" (当前选中项)
tabindex="-1" (其他项)
```

**键盘导航**：
- 方向键（↑↓）在 Radio 选项间切换
- Space 键选中当前聚焦项
- 无需 Tab 逐项穿越，方向键导航为标准 radio group 行为

---

### DragHandle

```
role="separator"
aria-orientation="horizontal"
aria-label="拖动以关闭"
```

或可提供关闭按钮作为辅助：

```
role="button"
aria-label="关闭选择主题面板"
```

---

### PrimaryButton / SecondaryButton

```
role="button"（默认，使用 <button> 元素即可）
aria-label（当按钮文字不充分时补充）
```

| 按钮 | aria-label 建议 |
|------|----------------|
| "确认退出" | `aria-label="确认退出登录"` |
| "取消" | `aria-label="取消退出登录"` |
| "完成" | `aria-label="完成主题选择"` |

---

## Screen Reader 状态播报流程

### Toast 播报
```
[VoiceOver / TalkBack 播报]
"兑换成功，会员已激活。" (assertive, 立即打断当前播报)
[2.5秒后]
Toast 消失，无需播报关闭动作
```

### Modal 播报
```
[打开时]
VoiceOver 移入 Modal
"确认退出登录？ 对话框" (标题 + role)
"退出后需要重新通过邮箱链接登录。" (描述)
[用户 Tab]
"确认退出, 按钮"
"取消, 按钮"

[关闭时]
"对话框已关闭" (系统自动)
焦点返回触发元素
```

### BottomSheet 播报
```
[打开时]
"选择主题 对话框"
"浅色, 已选中, 1/3" (Radio 选中项)
"深色, 未选中, 2/3"
"跟随系统, 未选中, 3/3"
"完成, 按钮"

[切换选项]
"深色, 已选中, 2/3"

[关闭时]
焦点返回触发元素
```

---

## 键盘导航（iPad / 外接键盘场景）

| 操作 | 快捷键 |
|------|--------|
| 关闭 Modal/Sheet | Escape |
| 切换 Radio 选项 | ↑ / ↓ 方向键 |
| 确认选中 Radio | Space |
| 提交 / 确认 | Enter（聚焦 Primary Button 时） |
| 焦点循环（Modal/Sheet 内） | Tab / Shift+Tab（循环不外逸） |

---

## 移动端操作建议

### Toast
- 文字内容控制在 1-2 行（约 30 字以内），避免截断
- 2.5 秒对于慢速阅读用户可能不足，建议提供"无障碍慢速模式"延长至 5 秒（跟随系统 Accessibility 设置）

### Modal
- "取消"按钮始终可见，避免用户卡住
- 破坏性操作按钮（"确认退出"）建议颜色与"取消"有足够差异，但不能降低对比度

### BottomSheet
- Radio 选项行高 ≥ 44px，确保触摸准确
- 提供 DragHandle 视觉提示，配合手势引导（设计稿已满足）
- 在 Sheet 打开期间，屏幕旋转时 Sheet 应保持展示并调整布局

### 减少动画（遵循系统设置）
- `prefers-reduced-motion: reduce` 时，所有进出动画改为 opacity 渐变（无位移、无缩放）
- 保留功能性反馈（如 Radio 选中状态变化），仅去除装饰性过渡
