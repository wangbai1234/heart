# 09 Accessibility — 角色页 Character Selector

---

## 触摸目标尺寸

iOS HIG 标准：最小触摸目标 44 × 44 pt

| 元素 | 可见尺寸（估算） | Touch Target | 是否达标 |
|------|--------------|-------------|---------|
| DismissButton（∨ 关闭） | 20 × 12 pt | 44 × 44 pt（建议通过 padding 扩展） | 需扩展 padding |
| CharacterCard（整体） | 358 × 约 200 pt | 358 × 200 pt（远超标准） | 达标 |
| SelectButton（"选择"） | 约 68 × 36 pt | 68 × 44 pt（建议增高至 44 pt） | 需增高 |
| SelectedIndicator（勾圆） | 约 40 × 40 pt | 44 × 44 pt（建议扩展） | 需扩展 |
| ConfirmButton（确认选择） | 350 × 54 pt | 350 × 54 pt | 达标 |

**修正建议：**
- DismissButton：不改变图标大小，通过 padding 将 touch area 扩展到 44 × 44 pt
- SelectButton：高度从 36 pt → 44 pt，或通过 hitSlop 扩展点击区域
- SelectedIndicator：直径从 40 pt → 44 pt，或 hitSlop 各向 +2 pt

---

## 颜色对比度

WCAG AA 标准：正文文字 ≥ 4.5:1，大文字（≥18pt 或 ≥14pt Bold）≥ 3:1

| 文字 | 颜色 | 背景色 | 对比度（估算） | 评级 |
|------|------|--------|-------------|------|
| 标题"选择一位陪伴你的人" | #3A3A4A | #FFF8F3 | 约 8.5:1 | AAA |
| 角色名称（如"神无月 凛"） | #1A1A2E | #FFFFFF | 约 16:1 | AAA |
| 描述文字 | rgba(58,58,74,0.75) | #FFFFFF | 约 5.8:1 | AA |
| 性格标签文字（御姐型） | #8B5CF6（估算） | rgba(200,182,255,0.3) | 约 3.2:1（估算） | 需核实 |
| 性格标签文字（元气型） | #3B82F6（估算） | rgba(167,199,231,0.3) | 约 3.5:1（估算） | 需核实 |
| 确认按钮文字"确认选择" | #FFFFFF | #FF8FAB → #FFB7C5 | 约 3.5:1（估算） | AA（大字体） |
| 未选中"选择"按钮文字 | #FFB7C5 | #FFFFFF | 约 2.8:1（估算） | 不达标（建议加深） |
| 时间"9:41" | #1A1A2E | #FFF8F3 | 约 16:1 | AAA |

**修正建议：**
- 性格标签：标签背景建议使用不透明或更高对比度背景，确保 AA 合规
- 未选中"选择"按钮：文字颜色可加深至 #E87FA0（约 3.5:1），或按钮背景改为粉色填充以保持对比

---

## 焦点状态（Focus State）

适用场景：iOS 外接键盘、macOS Catalyst、辅助技术

| 元素 | 建议焦点样式 |
|------|------------|
| DismissButton | 2 pt 粉色（#FFB7C5）描边环，圆角 4 pt，offset 2 pt |
| CharacterCard | 2 pt 粉色描边环，圆角 20 pt，offset 2 pt |
| SelectButton | 2 pt 粉色描边环（替代现有描边加粗），圆角 18 pt |
| ConfirmButton | 3 pt 白色描边 + 2 pt 粉色外环，圆角 27 pt |

**Tab 顺序建议：**
1. DismissButton（∨）
2. CharacterCard 1（神无月 凛，含 SelectButton / SelectedIndicator）
3. CharacterCard 2（桃乐丝，含 SelectButton）
4. CharacterCard 3（如存在）
5. ConfirmButton（确认选择）

---

## 文本可读性

| 检查项 | 实际值（估算） | 标准 | 是否达标 |
|--------|-------------|------|---------|
| 描述文字字号 | 13 pt | 最小 12 pt（iOS HIG） | 达标（临近边界，建议 14 pt） |
| 描述文字行高 | 约 1.6 | 最小 1.4 | 达标 |
| 性格标签字号 | 12 pt | 最小 12 pt | 达标（边界值） |
| 标签行高 | 约 1.0（内容由 padding 撑高） | 最小 1.4（实际由容器高度决定） | 可接受 |
| 导航标题字号 | 17 pt | 最小 12 pt | 达标 |
| 角色名称字号 | 18 pt | 最小 12 pt | 达标 |
| 确认按钮字号 | 17 pt | 最小 12 pt | 达标 |

**建议：**
- 角色描述文字从 13 pt → 14 pt，提升长文可读性（二次元用户年轻，但长描述文字可读性优先）

---

## ARIA 建议

> 以下为 Web/React Native Web 实现时的 ARIA 属性建议；原生 iOS 使用 UIAccessibility。

| 元素 | role | aria-label / 说明 |
|------|------|-----------------|
| DismissButton | `button` | `aria-label="关闭角色选择"` |
| PageTitle | `heading` level 1 | 已有文字内容，无需额外 label |
| HeroSection | `img` 或 `presentation` | 如为纯装饰，`aria-hidden="true"` |
| GlassHeart | `img` | `aria-label="yuoyuo 品牌心形图标"` 或 `aria-hidden="true"`（纯装饰） |
| CharacterCard（已选中） | `radio` / `option` | `aria-selected="true"` `aria-label="神无月 凛，御姐型，已选中"` |
| CharacterCard（未选中） | `radio` / `option` | `aria-selected="false"` `aria-label="桃乐丝，元气型，未选中"` |
| CharacterCardList | `radiogroup` | `aria-label="角色选择列表"` |
| SelectButton | — | 父 CharacterCard 已有交互，此按钮可 `aria-hidden="true"` 避免重复（整卡可点击时） |
| SelectedIndicator | — | `aria-hidden="true"`（状态由父 Card 的 aria-selected 表达） |
| ConfirmButton | `button` | `aria-label="确认选择当前角色"` |
| AvatarImage | `img` | `alt="神无月 凛 的角色头像"` / `alt="桃乐丝 的角色头像"` |
| PersonalityTag | `span` | 无需独立 role，内容由父 card aria-label 包含 |

---

## Keyboard Navigation（键盘导航）

| 按键 | 行为 |
|------|------|
| Tab | 在可交互元素间顺序移动（顺序见上方 Tab 顺序建议） |
| Shift+Tab | 反向移动 |
| Enter / Space | 激活当前焦点元素（选中卡片 / 点击按钮） |
| Escape | 关闭 modal（等效 DismissButton） |
| Arrow Down / Up | 在 CharacterCardList 中移动选中项（radiogroup 行为） |

---

## Screen Reader 朗读建议（中文）

| 元素 | 建议朗读文本 |
|------|------------|
| 页面标题 | "选择一位陪伴你的人" |
| DismissButton | "关闭，返回上一步" |
| 英雄区 | （建议静音，aria-hidden，避免打断流程） |
| CharacterCard 1（选中） | "神无月 凛，御姐型，已选中。失去时代的雷神……（描述全文）" |
| CharacterCard 2（未选中） | "桃乐丝，元气型，未选中。失去职责的冥界少女……（描述全文）" |
| SelectButton | "选择桃乐丝" |
| SelectedIndicator | （由父 Card 状态表达，自身 aria-hidden） |
| ConfirmButton | "确认选择，进入聊天" |
| 确认成功后 | 应播报"已选择 [角色名]，正在进入聊天页面" |

---

## 移动端操作友好度

### 单手操作分析（右手持机，iPhone 14）

| 区域 | 拇指可达性 | 分析 |
|------|----------|------|
| DismissButton（左上角） | 困难（拇指难及） | 建议支持下拉手势（pan-to-dismiss）替代按钮 |
| 角色卡片区（中部） | 良好 | 主操作区，拇指自然范围内 |
| "选择"按钮（右上角） | 困难（一般位于卡片右上角） | 整卡可点击可缓解，但按钮本身难达 |
| ConfirmButton（底部） | 优秀 | 位于最自然的拇指点击区域 |

**优化建议：**
- 将整张 CharacterCard 设为可点击（不只靠右上角按钮），提升单手可操作性
- 支持 pan-to-dismiss 手势替代左上角关闭按钮
- "选择"按钮右上角位置可考虑调整为卡片底部或右侧中央
