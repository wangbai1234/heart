# 06 Interactions — Redeem 兑换页

---

## 进入动画

**触发**：用户从上一页面导航至此页

**动画方案**：
- 页面从右侧滑入（标准 iOS push 转场），duration ≈ 400ms，easing ease-out
- 进入后，InputCard 从 Y+20px offset 淡入到原位（opacity 0→1，translateY 20px→0），delay ≈ 100ms，duration ≈ 300ms
- ActivateButton 稍晚进入，delay ≈ 200ms，duration ≈ 300ms（估算值）
- 礼品盒插画：建议轻微弹性出现（scale 0.8→1.0，spring easing），duration ≈ 500ms

⚠️ 设计稿未定义具体进入动画，建议参考 Motion Storyboard

---

## 退出动画

**触发**：点击返回按钮 / 系统右滑手势

**动画方案**：
- 标准 iOS pop 转场（当前页向右滑出，前一页从左侧露出），duration ≈ 350ms

**激活成功退出**：
- Toast「激活成功！🎉」从底部出现（duration ≈ 250ms）→ 停留 1500ms → 页面跳转会员权益页
- 跳转动画：⚠️ 设计稿未定义，建议参考 Motion Storyboard

---

## 输入框交互

### 聚焦（Focus）
- 触发：点击任意字符格
- 效果：该格边框从 `rgba(255,183,197,0.35)` 变为 `#FFB7C5`，duration ≈ 150ms
- 键盘弹出：系统键盘向上滑出，页面整体上移（避免键盘遮挡输入框）

### 输入字符
- 每输入一个字符，字符显示在当前格中，焦点自动移至下一格
- 第 4 格填满后，焦点跳转至下一段第一格（跳过「-」分隔符）
- 第 12 格填满后：键盘自动收起（建议），⚠️ 设计稿未定义，建议参考 Motion Storyboard

### 退格删除
- 删除当前格字符，若当前格为空则焦点回到上一格并删除
- 跨段退格：第 5 格退格 → 删除第 4 格字符，焦点移至第 4 格

### 粘贴（系统长按菜单）
- 支持长按输入框唤起系统粘贴菜单
- 粘贴后自动解析并填入 4-4-4 格式（去掉非字母数字字符后分组）

---

## PasteButton（粘贴按钮）交互

**触发**：点击「粘贴兑换码」按钮

**流程**：
1. 读取系统剪贴板内容
2. 解析兑换码格式：
   - 若剪贴板为 12 位字母数字（或带连字符的 4-4-4 格式）→ 填入输入框，所有格填满，轻微振动反馈（haptic feedback，medium impact）
   - 若格式不匹配 → Toast 提示「格式不正确，请检查兑换码」，duration 2000ms
   - 若剪贴板为空 → Toast 提示「剪贴板中没有内容」

**按钮按下效果**：
- scale: 1.0 → 0.97，duration 100ms，easing ease-in
- 松手后 0.97 → 1.0，duration 150ms，easing ease-out

---

## ActivateButton（立即激活）交互

### 按下效果
- scale: 1.0 → 0.97，duration 100ms
- 阴影缩小（blur: 24px → 12px）

### 禁用态（12位未填满）
- 整体 opacity ≈ 0.60
- 点击时：轻微抖动动画（translateX -4px → 4px → 0，duration 300ms）
- Toast 提示「请先填写完整兑换码」

### Loading 态（API 请求中）
- 文字「立即激活」隐藏
- 显示白色旋转 loading 指示器（spinner），大小 ≈ 40px
- 按钮不可再次点击（防重复提交）
- duration：等待 API 响应

### 成功态
- loading spinner 消失
- ✓ 图标出现（scale 0→1，duration 300ms）
- 按钮颜色短暂变为 `#6BCB77`（成功绿）（可选）
- 触发 haptic feedback（success notification feedback）
- delay 500ms 后跳转页面

### 错误态（API 返回失败）
- loading spinner 消失
- 按钮恢复默认态
- 输入框显示 error 状态（边框红色 `#FF6B6B`）
- 输入框组执行横向抖动动画（shake，duration ≈ 400ms）
- Toast 错误提示（根据 API 错误码）：
  - 兑换码无效：「兑换码无效，请检查后重试」
  - 已被使用：「该兑换码已被使用」
  - 已过期：「该兑换码已过期」
  - 网络错误：「网络错误，请稍后重试」

---

## FAQAccordion（折叠卡片）交互

### 展开
- 触发：点击 Header 行任意位置
- 动画：
  - 卡片高度从折叠态高度插值到展开态高度，duration ≈ 250ms，easing ease-out（spring）
  - 右侧 chevron 图标旋转 -90° → 0°（从右指向向下），duration ≈ 250ms
  - 步骤列表内容 fade-in + translateY(-8px → 0)，stagger delay 每条 ≈ 50ms

### 折叠
- 触发：再次点击 Header 行
- 动画：与展开相反，duration ≈ 200ms，easing ease-in

⚠️ 设计稿中 FAQ 卡片呈展开状态，初始状态（collapsed vs expanded）未在设计稿中明确定义。
建议：默认折叠，方便用户聚焦主要操作。

---

## 「去爱发电」链接交互

**触发**：点击「去爱发电 →」文字链接

**效果**：
- 文字 opacity 1.0 → 0.60，duration 100ms（按下）
- 松手后打开系统浏览器（Safari）跳转至爱发电赞助页
- 或使用 SFSafariViewController 在 App 内打开（推荐）

---

## Hover 状态

本页为移动端，无 Hover 状态。以下仅用于跨平台（iPad/桌面端）适配参考：
⚠️ 设计稿未定义，建议参考 Motion Storyboard（若需要 iPad 适配）

---

## Scroll 行为

- 键盘弹出时：页面整体上移，确保输入框不被键盘遮挡（`KeyboardAvoidingView` 或 `adjustResize` 方案）
- 手动下滑：键盘收起（建议 `dismissKeyboard on scroll`）
- 无下拉刷新
- 无横向滚动

---

## Skeleton / Empty 状态

本页无列表数据加载，无需 Skeleton 状态。

---

## Error 状态汇总

| 场景 | 表现 |
|------|------|
| 兑换码不完整 | ActivateButton 禁用态 + 点击时抖动 + Toast |
| 兑换码格式错误（粘贴） | Toast「格式不正确」 |
| 兑换码无效 | 输入框红色边框 + 抖动动画 + Toast |
| 兑换码已使用 | 同上，Toast 文案不同 |
| 网络错误 | Toast「网络错误，请稍后重试」+ 按钮恢复 |

---

## 页面转场

| 来源 | 目标 | 转场方式 |
|------|------|---------|
| 上一页 → 此页 | Redeem 兑换页 | iOS push（左→右滑入） |
| 此页（返回） → 上一页 | — | iOS pop（右→左滑出） |
| 此页（成功）→ 会员权益页 | 会员权益页 | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| 此页（去爱发电）→ 外部浏览器 | Safari/SFSafariVC | 系统级模态上推 |
