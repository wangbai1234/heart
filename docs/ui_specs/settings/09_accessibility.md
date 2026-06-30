# 09 Accessibility — 设置页 Settings

---

## 触摸目标尺寸

iOS HIG 标准：最小 44×44 pt

| 组件 | 估算触摸尺寸 | 是否符合 |
|------|-----------|---------|
| 返回按钮 `<` | ~44×44 pt（需确保） | ✅ 需扩展热区至 44×44 pt（估算值） |
| ProfileCard（整个卡片） | ~358×96 pt | ✅ 远超标准 |
| SettingRow（整行） | ~358×54 pt | ✅ 宽度足够，高度 54 pt > 44 pt |
| Toggle（积极提醒） | ~51×44 pt（建议扩展高度到 44 pt） | ⚠️ Toggle 高 31 pt，需增加垂直热区 |
| Segment Picker 各项 | ~58×34 pt（单项） | ⚠️ 高度 34 pt < 44 pt，建议扩展热区至 44 pt |
| Slider Thumb | ~22 pt 直径，需 44×44 热区 | ⚠️ 视觉尺寸 22 pt，需扩展热区 |
| Chevron（仅图标区域） | ~20×20 pt | ⚠️ 仅靠 Row 整行触摸弥补（Row 本身 ≥44 pt 高） |

**建议：**
- Toggle、Slider Thumb、Segment 各项均需在视觉之外扩展不可见触摸热区（iOS 可用 `contentEdgeInsets` 或 hitTest 扩展）
- Row 整行可点击，无需单独扩展 Chevron 热区

---

## 颜色对比度（WCAG）

基于设计稿推断颜色，对比度为估算值。

| 文字 | 背景 | 推断对比比 | WCAG AA（≥4.5:1） | WCAG AAA（≥7:1） |
|------|------|----------|-----------------|----------------|
| 导航栏"设置" #3A3A4A | 透明背景（背景浅粉 ~#FDEEF3） | ~7.5:1（估算值） | ✅ AA | ✅ AAA |
| Row Label #3A3A4A | 卡片背景 rgba(255,255,255,0.88)≈#FFF8FA | ~7.2:1（估算值） | ✅ AA | ✅ AAA |
| Section Label #8A8A9A | 背景 ~#F5E8F5 | ~3.2:1（估算值） | ⚠️ 未达 AA（建议加深至 #666677） |  |
| 副文字"至 2026-12-31" #8A8A9A | 卡片白色背景 | ~3.5:1（估算值） | ⚠️ 接近 AA 边界，建议确认 |  |
| MemberBadge "会员·至 2026-12-31" #FF85A1 | 浅粉背景 rgba(255,183,197,0.20)≈#FFF0F3 | ~2.8:1（估算值） | ❌ 未达 AA（建议加深文字至 #D4547A） |  |
| 注销账号 #FF85A1 | 卡片白色背景 | ~2.9:1（估算值） | ❌ 未达 AA（危险操作需高可辨识度，建议加深） |  |
| Toggle Thumb 白色 | Toggle Track 粉色 #FFB7C5 | ~2.5:1（估算值） | ❌ 但 Toggle 状态通过形状+位置区分，颜色不是唯一线索 |  |

**重要提示：**
- `Section Label`（#8A8A9A）和 `MemberBadge` 对比度未达 WCAG AA，是本页主要 accessibility 风险点
- `注销账号` 警示色对比度不足，建议加深至 #D4547A 或 #C9426B

---

## 焦点状态（Keyboard Focus）

⚠️ 设计稿未定义焦点环样式。

**建议规范：**
- 焦点环颜色：`#FFB7C5`（品牌粉色）或反转色
- 焦点环样式：2 pt solid 边框 + 2 pt offset（与背景之间的间隙）
- 圆角：与组件圆角一致（Row 约 0，Card 约 20 pt）
- 不使用系统默认蓝色焦点环（与品牌色不符）

**Tab 顺序建议（从上至下，从左至右）：**
1. 返回按钮
2. ProfileCard
3. 会员兑换行
4. 订阅状态行
5. 主题 Segment（浅色→深色→自动）
6. 字体大小 Slider
7. 积极提醒 Toggle
8. 静音行
9. 清除网格服务器行
10. 导出我的数据行
11. 注销账号行
12. 版本 1.0.0 行
13. 用户协议 / 隐私政策行
14. 联系我们行

---

## 文本可读性

| 层级 | 字号 | 行高 | 是否符合（≥12px，行高≥1.4） |
|------|------|------|--------------------------|
| 导航栏标题 | 18 pt | ~24 pt（比例 1.33） | ⚠️ 行高比例略低，但标题单行无需大行高 |
| 用户名 | 17 pt | ~22 pt（比例 1.29） | ⚠️ 单行标题，可接受 |
| Row Label | 15–16 pt | ~22 pt（比例 1.37–1.47） | ✅ 符合 |
| 副文字 | 13 pt | ~18 pt（比例 1.38） | ✅ 符合 |
| Section Label | 12 pt | ~16 pt（比例 1.33） | ✅ 字号达标，行高略低但单行 |
| MemberBadge | 12 pt | ~16 pt | ✅ 字号达标（≥12px 边界值） |

**建议：**
- 所有正文内容行高保持 ≥1.4（建议 1.5 用于多行文本）
- 12 pt 为最小可用字号，不建议再小

---

## ARIA 建议

| 组件 | role | aria-label / aria-* 建议 |
|------|------|------------------------|
| 返回按钮 | `button` | `aria-label="返回"` |
| ProfileCard | `button` | `aria-label="查看和编辑账号：晨曦，会员至2026年12月31日"` |
| SectionLabel（我的会员） | `heading` level=2 | — |
| SectionLabel（外观） | `heading` level=2 | — |
| SectionLabel（通知） | `heading` level=2 | — |
| SectionLabel（隐私与数据） | `heading` level=2 | — |
| SectionLabel（关于） | `heading` level=2 | — |
| GroupCard | `group` 或 `region` | `aria-labelledby="对应 SectionLabel ID"` |
| 会员兑换行（折叠） | `button` | `aria-expanded="false"` `aria-label="会员兑换，折叠"` |
| 订阅状态行 | `button` | `aria-label="订阅状态，至2026年12月31日，点击查看详情"` |
| 主题 Segment Picker | `radiogroup` | `aria-label="主题选择"` |
| 主题选项（浅色） | `radio` | `aria-checked="true"` `aria-label="浅色主题"` |
| 主题选项（深色） | `radio` | `aria-checked="false"` `aria-label="深色主题"` |
| 主题选项（自动） | `radio` | `aria-checked="false"` `aria-label="自动主题"` |
| 字体大小 Slider | `slider` | `aria-label="字体大小"` `aria-valuemin="最小值"` `aria-valuemax="最大值"` `aria-valuenow="当前值"` |
| 积极提醒 Toggle | `switch` | `aria-checked="true"` `aria-label="积极提醒"` |
| 静音行 | `button` | `aria-label="静音，当前时段22:00至8:00，点击修改"` |
| 清除网格服务器行 | `button` | `aria-label="清除网格服务器"` |
| 导出我的数据行 | `button` | `aria-label="导出我的数据"` |
| 注销账号行 | `button` | `aria-label="注销账号"` `aria-describedby="delete-warning"` |
| 版本 1.0.0 行 | `button` 或 `listitem` | `aria-label="应用版本 1.0.0"` |
| 用户协议行 | `button` | `aria-label="查看用户协议和隐私政策"` |
| 联系我们行 | `button` | `aria-label="联系我们"` |

---

## Keyboard Navigation

| 按键 | 行为 |
|------|------|
| `Tab` | 按上述顺序移动焦点 |
| `Shift+Tab` | 反向移动焦点 |
| `Enter` / `Space` | 激活当前聚焦的 Row / Button / Toggle |
| `Escape` | 关闭弹窗 / 收起展开项 / 返回上一页 |
| `←` / `→` | Segment Picker 切换选项 |
| `←` / `→` | Slider 调整值（建议步长：1 单位） |
| `Home` / `End` | Slider 跳至最小/最大值 |
| `PageUp` / `PageDown` | 快速滚动 ScrollView（约 500 pt）（估算值） |

---

## Screen Reader 建议（VoiceOver / TalkBack）

重要元素朗读文本建议（中文）：

| 元素 | 推荐朗读文本 |
|------|-----------|
| 页面标题 | "设置" |
| 返回按钮 | "返回，按钮" |
| 用户信息卡 | "晨曦，会员，有效期至2026年12月31日，点击查看个人资料" |
| 会员兑换行 | "会员兑换，折叠，按钮，点击展开" |
| 订阅状态行 | "订阅状态，有效期至2026年12月31日，按钮" |
| 主题（浅色已选） | "主题，当前选择浅色，可选深色或自动，单选组" |
| 字体大小 Slider | "字体大小，当前值60%，可调整，滑块" |
| 积极提醒 Toggle | "积极提醒，已开启，开关按钮，点击关闭" |
| 静音行 | "静音，22点到8点，按钮，点击修改静音时段" |
| 注销账号行 | "注销账号，危险操作，按钮" |
| 版本行 | "当前版本1.0.0，按钮" |

---

## 移动端操作友好度

### 单手操作分析（拇指区域）

基于 iPhone 14（390 × 844 pt），单手右手握持：
- **安全拇指区（Easy Reach）**：屏幕底部约 60% 高度（y > 380 pt）
- **可达区（Reachable）**：屏幕中部（230 < y < 380 pt）
- **困难区（Stretch）**：屏幕顶部（y < 230 pt）

| 元素 | 位置（估算） | 拇指友好度 |
|------|-----------|----------|
| 返回按钮 | 顶部 y ~66 pt | ❌ 需拇指伸展，困难区 |
| ProfileCard | y ~88–184 pt | ⚠️ 可达区（上部） |
| 会员组 | y ~200–310 pt | ⚠️ 可达区 |
| 外观组 | y ~320–440 pt | ✅ 安全区（需滚动） |
| 通知组 | y ~450–570 pt | ✅ 安全区 |
| 隐私组 | y ~580–760 pt | ✅ 安全区 |
| 关于组 | y ~770–950 pt | ✅ 安全区（需滚动） |

**建议：**
- 返回按钮位于困难区（顶部），依赖 iOS 左滑手势作为辅助
- 高频操作（Toggle、主题切换）位于页面中部，用户通常会滚动到合适位置操作
- 危险操作（注销账号）位于页面下部安全区，单手可达，但需二次确认弹窗防误操作
- 整体布局对单手操作较友好（通过滚动调整）

### 间距充裕度
- 所有 Row 高度 ~54 pt，远超 44 pt 最小标准，误触风险低
- 相邻 Row 之间靠分隔线区分，无需额外间距避免误触
