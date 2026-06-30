# 06 Interactions — 设置页 Settings

---

## 进入动画（Page Enter）

**触发：** 从个人中心页点击「设置」入口
**动画类型：** iOS 标准 Push 转场（从右侧滑入）
**参数：**
- 方向：从右 → 左（新页面从右边缘滑入）
- Duration：约 350 ms（iOS 系统默认）
- Easing：`cubic-bezier(0.4, 0, 0.2, 1)`（估算值）
- 前一页：向左偏移约 100 pt 并略微变暗
- 新页面：从 x=390 pt 滑至 x=0 pt

**卡片入场（推荐增强）：**
⚠️ 设计稿未定义，建议参考 Motion Storyboard
- 建议：各 GroupCard 从下方 offset 20 pt 淡入，stagger 30 ms（估算值）

---

## 退出动画（Page Exit）

**触发：** 点击左上角 `<` 返回，或 iOS 左滑手势
**动画类型：** iOS 标准 Pop 转场（向右侧滑出）
**参数：**
- 方向：从左 → 右（当前页从左边缘滑出）
- Duration：约 350 ms
- 前一页：从左偏移位置归位

---

## Hover 状态

⚠️ iOS 移动端无标准 Hover（鼠标悬停），适用于 iPad 外接鼠标或未来 Web 版。
建议 Web 版：Row 背景轻微变浅粉色 rgba(255,183,197,0.08)。

---

## Pressed 状态（按下态）

### SettingRow 按下态
- 触发：手指按下 SettingRow 任意位置
- 效果：Row 背景色变为 rgba(255,183,197,0.12)（估算值）
- Duration：即时（0 ms delay，触摸即触发）
- 松开后：立即恢复（或在导航转场中保持）

### ProfileCard 按下态
- 触发：手指按下 ProfileCard
- 效果：卡片背景稍变深（opacity +5%）（估算值）
- Duration：即时

### 返回按钮按下态
- 透明度降至 0.6
- Duration：约 100 ms

---

## Selected 状态

### Segment Picker 选中态
- 触发：点击「浅色/深色/自动」任一选项
- 效果：选中项背景从透明 → 白色，带阴影
- 动画：滑动（selected indicator 平滑移动）
- Duration：约 200 ms，easing: spring（damping 0.8）（估算值）
- 即时生效全局主题

### SettingRow 无 selected 状态
（设置行是无状态导航，不需要 selected 态）

---

## Disabled 状态

⚠️ 设计稿未定义任何 disabled 态。
建议规范：
- 整行 opacity 降至 0.4
- Chevron 颜色变为 #C0C0CC
- 点击无反应
- 不适用于本页当前所有可见行

---

## Loading 状态

⚠️ 设计稿未定义 loading 态。
建议：
- 导出我的数据、清除网格服务器点击后：
  - Row 右侧显示 ActivityIndicator（品牌粉色）（估算值）
  - 或 Row 整体 skeleton shimmer

---

## Error 状态

⚠️ 设计稿未定义 error 态。
建议：
- 网络操作失败时（清除/导出）：Toast 提示（底部弹出，红/警示色）
- 表单操作失败：inline 红色提示文字

---

## Empty 状态

⚠️ 设计稿未定义 empty 态（本页内容固定，无动态列表）。

---

## Skeleton 加载态

⚠️ 设计稿未定义 skeleton。
建议：
- Profile 卡：头像位置显示灰色圆形 shimmer，名字位置显示灰色矩形 shimmer
- Duration：约 1.2 s 循环，left-to-right shimmer（估算值）

---

## Scroll 行为

- 方向：垂直滚动
- iOS 弹性滚动（rubber-band）开启
- 滚动时：NavigationBar 固定不动
- 滚动时：背景渐变固定不动
- 无 sticky section headers（Section Label 随内容滚动）
- 无下拉刷新
- 无上拉加载

**滚动阴影增强（推荐）：**
⚠️ 设计稿未定义，建议参考 Motion Storyboard
- NavigationBar 下方：当 ScrollView offset > 0 时，出现轻微底部阴影（高度约 4 pt，rgba(180,160,200,0.1)）（估算值）

---

## Toggle 开关交互（积极提醒）

**触发：** 点击 Toggle 控件
**ON → OFF：**
- Thumb 从右向左滑动（约 20 pt 位移）
- Track 颜色渐变从粉色 → 灰色
- Duration：约 250 ms，spring easing
- 同时触发：关闭系统通知权限（或提示用户）

**OFF → ON：**
- Thumb 从左向右滑动
- Track 颜色渐变从灰色 → 粉色渐变
- Duration：约 250 ms，spring easing

**Haptic 建议：** UIImpactFeedbackGenerator（.light）（估算值）

---

## Slider 交互（字体大小）

**触发：** 拖拽 Thumb 或点击 Track
**拖拽中：**
- Thumb 放大约 1.2x（估算值）
- ⚠️ 当前值气泡显示未定义，建议参考 Motion Storyboard
- 全局文字大小即时跟随更新（实时预览）

**释放：**
- Thumb 恢复原始大小
- 当前值持久化存储
- Haptic 建议：UISelectionFeedbackGenerator 每间隔一定距离触发（估算值）

---

## Card Selection（会员兑换展开）

**触发：** 点击「会员兑换」行
**折叠 → 展开：**
- Chevron 从 0° 旋转至 -180°（向上）
- 子内容区域从 height 0 展开至完整高度
- Duration：约 250 ms，easing: decelerate
- ⚠️ 展开后的子内容设计稿未定义，建议参考产品文档

**展开 → 折叠：**
- 反向动画，height 从完整收缩至 0
- Chevron 从 -180° 旋转至 0°

---

## 危险操作确认（注销账号）

**触发：** 点击「注销账号」行
**流程：**
1. Row 按下态（轻粉色背景）
2. 弹出确认 Modal（⚠️ Modal 样式未定义，建议参考 Motion Storyboard）
3. Modal 建议：
   - 遮罩 rgba(30,20,40,0.4)
   - 毛玻璃卡片从底部弹出
   - 标题「确定注销账号？」
   - 警示文字（粉色）
   - 取消/确认两个按钮
4. 确认 → 执行注销，跳转登录页

---

## 清除网格服务器 交互

**触发：** 点击「清除网格服务器」行
**流程：**
1. 弹出二次确认弹窗（⚠️ 设计稿未定义，建议参考 Motion Storyboard）
2. 确认 → Loading 态 → 成功/失败 Toast

---

## 导出我的数据 交互

**触发：** 点击「导出我的数据」行
**流程：**
1. 跳转至导出确认/进度页（⚠️ 设计稿未定义）
2. 或直接触发系统分享 Sheet

---

## 页面转场（二级页面进入）

适用于：订阅状态、静音、清除/导出、注销、版本详情、协议、联系我们
- 统一使用 iOS Push 转场（右进左出）
- Duration：约 350 ms（iOS 系统默认）

---

## Bottom Button

本页无固定底部按钮（无 Bottom Bar，无 Tab Bar）。

---

## Haptic Feedback 建议

| 操作 | Haptic 类型 |
|------|-----------|
| Toggle 切换 | UIImpactFeedbackGenerator(.light) |
| Slider 到端点 | UIImpactFeedbackGenerator(.medium) |
| 危险操作确认 | UINotificationFeedbackGenerator(.warning) |
| 成功操作完成 | UINotificationFeedbackGenerator(.success) |
