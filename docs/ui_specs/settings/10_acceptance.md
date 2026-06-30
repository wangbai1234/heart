# 10 Acceptance Checklist — 设置页 Settings

Pixel Perfect 视觉验收 Checklist。目标：整体视觉一致度 ≥ 95%。

---

## 整体布局

- □ 页面整体为竖向滚动布局，无水平滚动
- □ 所有内容卡片左右 margin 均为 16 pt（估算值）
- □ ScrollView 起始于 NavigationBar 底部（StatusBar + NavBar 共约 88 pt）
- □ 页面底部 ScrollView padding ≥ 34 pt（Safe Area Bottom）
- □ 无固定底部 Tab Bar（二级页面）
- □ 背景图不随 ScrollView 滚动（固定背景层）

---

## Safe Area

- □ 状态栏内容（时间、信号）处于 Safe Area Top 内（约 44 pt 内）
- □ 导航栏位于 Status Bar 下方，正确遵守 Safe Area
- □ 底部内容未被系统 Home Indicator 区域（34 pt）遮挡
- □ 页面内容未溢出至 Safe Area 之外

---

## 背景层

- □ 页面背景是否直接使用浅色模式 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` 或深色模式 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ 背景是否保留原始光感与云层氛围，无重画痕迹
- □ 整体暖调、治愈感，无冷色突兀区域

---

## 导航栏（NavigationBar）

- □ 标题文字"设置"居中显示
- □ 标题字体：PingFang SC Medium，约 18 pt，颜色 #3A3A4A
- □ 左侧返回按钮 `<` 正确显示，颜色与标题一致
- □ 返回按钮距左边缘约 20 pt（估算值）
- □ 导航栏背景透明（可透视背景渐变）

---

## Profile 卡（ProfileCard）

- □ 卡片宽度约 358 pt，居中（左右各 16 pt margin）
- □ 卡片高度约 96 pt（估算值）
- □ 卡片圆角约 20 pt
- □ 卡片背景为半透明白色，有轻微毛玻璃效果
- □ 卡片有轻微投影（粉紫色调，blur ~20 pt）
- □ 头像圆形裁剪，直径约 60 pt
- □ 若用户已上传头像，ProfileCard 是否显示真实头像
- □ 若用户未上传头像，ProfileCard 是否显示空白占位头像组件
- □ 头像有白色细边框（约 2 pt）
- □ 空白占位头像若出现，是否保持中性、无角色特征
- □ 用户名字体 Semibold，约 17 pt，颜色 #3A3A4A
- □ 会员标签"会员 · 至 2026-12-31"正确显示在名字下方
- □ 会员标签背景为淡粉色，圆角 pill 形，文字粉色（#FF85A1 估算值）
- □ 右侧 Chevron `>` 居卡片垂直中心，颜色灰色

---

## 分组标题（SectionLabel）

- □ 5 个分组标题均正确显示：我的会员 / 外观 / 通知 / 隐私与数据 / 关于
- □ 字号约 12 pt，颜色约 #8A8A9A（浅灰）
- □ 左对齐，与卡片左边缘对齐（x=16 pt）
- □ 与上方卡片间距约 16 pt，与下方卡片间距约 6–8 pt

---

## GroupCard 通用规范

- □ 所有 GroupCard 宽度一致（约 358 pt）
- □ 所有 GroupCard 圆角一致（约 20 pt）
- □ 所有 GroupCard 背景一致（半透明白色，约 rgba(255,255,255,0.88)）
- □ 所有 GroupCard 有统一轻投影
- □ 相邻 Row 之间有细分隔线（约 0.5 pt），颜色极浅
- □ 分隔线左侧有 inset（从 Label 文字起始位置）
- □ 首行上方和末行下方无分隔线

---

## 设置行（SettingRow）通用规范

- □ 所有 Row 高度约 54 pt
- □ 左侧图标尺寸约 22×22 pt
- □ 图标颜色为粉色系（#FFB7C5 ～ #FF85A1）
- □ 图标与 Label 间距约 14 pt
- □ Label 字号约 15–16 pt，颜色 #3A3A4A
- □ 内部左右 padding 均约 16 pt

---

## 会员组 - 具体行

- □ 会员兑换行：礼盒图标 + "会员兑换" + 向下 Chevron（∨）
- □ 订阅状态行：皇冠图标 + "订阅状态" + 副文字"至 2026-12-31" + 向右 Chevron

---

## 外观组 - 具体行

- □ 主题行：调色板图标 + "主题" + Segment Picker（浅色/深色/自动）
- □ Segment Picker 宽约 180 pt，正确显示 3 个选项
- □ 当前选中"浅色"：白色背景，有阴影，文字深色
- □ 未选中"深色"/"自动"：透明背景，文字灰色
- □ 字体大小行：字母A图标 + "字体大小" + [小A + Slider + 大A]
- □ Slider 轨道正确显示粉色填充区域（约 60% 处）
- □ Slider Thumb 圆形，粉色，直径约 22 pt
- □ 两端标识 A 大小差异可辨认（左小右大）

---

## 通知组 - 具体行

- □ 积极提醒行：铃铛图标 + "积极提醒" + Toggle（当前 ON）
- □ Toggle ON 状态：粉色渐变轨道（#FFB7C5→#FF85A1），白色 Thumb 在右侧
- □ Toggle 尺寸约 51×31 pt
- □ 静音行：月亮图标 + "静音" + 副文字"22:00 - 8:00" + 向右 Chevron

---

## 隐私与数据组 - 具体行

- □ 清除网格服务器行：垃圾桶图标 + "清除网格服务器" + 向右 Chevron
- □ 导出我的数据行：下载图标 + "导出我的数据" + 向右 Chevron
- □ 注销账号行：账号删除图标（粉色）+ "注销账号"（粉色，#FF85A1）+ 向右 Chevron
- □ 注销账号的 Label 颜色与其他行明显不同（警示粉色）
- □ 注销账号图标也为警示粉色

---

## 关于组 - 具体行

- □ 版本 1.0.0 行：信息圆圈图标 + "版本 1.0.0" + 向右 Chevron
- □ 用户协议行：文档图标 + "用户协议 / 隐私政策" + 向右 Chevron
- □ 联系我们行：耳机图标 + "联系我们" + 向右 Chevron

---

## Spacing / Padding / Margin

- □ 页面水平 margin 16 pt（估算值）
- □ 卡片内部水平 padding 16 pt（估算值）
- □ Row 高度约 54 pt（估算值）
- □ Section Label 与上方卡片间距约 16 pt（估算值）
- □ Section Label 与下方卡片间距约 6–8 pt（估算值）
- □ 卡片之间 gap 约 8–12 pt（估算值）

---

## Radius

- □ ProfileCard 圆角约 20 pt
- □ 所有 GroupCard 圆角约 20 pt
- □ MemberBadge 为 pill 形（圆角约 11 pt）
- □ 头像圆形（border-radius: 9999 pt）
- □ Segment Picker 容器圆角约 10 pt
- □ Segment 选中项圆角约 8 pt
- □ Toggle 为完全圆角（pill 形）

---

## Shadow

- □ ProfileCard 投影存在且柔和（粉紫色调，blur ~20 pt）
- □ 所有 GroupCard 投影存在且一致（粉紫色调，blur ~16 pt）
- □ Segment 选中项有轻微阴影（区分未选中项）
- □ Toggle 有轻微阴影（立体感）
- □ 阴影颜色为粉紫色调（非纯黑），与品牌色调一致

---

## Blur 效果

- □ ProfileCard 背景有轻微 backdrop-blur（毛玻璃感）
- □ 所有 GroupCard 背景有轻微 backdrop-blur
- □ 背景光晕有 blur 效果（非清晰边缘）
- □ Glass 效果不过强（卡片内容清晰可读）

---

## Gradient

- □ 页面背景渐变从上至下由浅粉逐渐过渡到紫粉（无突变）
- □ Toggle ON 轨道有粉色渐变（非纯色）
- □ 底部光晕为径向渐变（中心较深，边缘透明）

---

## Typography

- □ 所有中文字体为 PingFang SC 或 HarmonyOS Sans SC
- □ 导航栏标题字号约 18 pt，Medium 字重
- □ 用户名字号约 17 pt，Semibold 字重
- □ Row Label 字号约 15–16 pt，Regular/Medium 字重
- □ 副文字字号约 13 pt，Regular 字重，灰色
- □ Section Label 字号约 12 pt，Regular 字重
- □ MemberBadge 字号约 12 pt，Medium 字重
- □ 无字号小于 12 pt 的文字出现
- □ 所有文字行高 ≥ 1.3（单行标题可接受）

---

## 组件尺寸

- □ ProfileCard：约 358×96 pt
- □ 头像圆形直径约 60 pt
- □ GroupCard 宽约 358 pt
- □ SettingRow 高约 54 pt
- □ Toggle：约 51×31 pt
- □ Segment Picker：约 180×34 pt
- □ 图标尺寸：约 22×22 pt（统一）
- □ Chevron：约 8×14 pt（向右）/ 约 14×8 pt（向下）

---

## Glass Effect 透明度

- □ 卡片背景透明度约 0.88（估算值），可透视背景渐变但内容清晰
- □ 分隔线透明度约 0.8（极淡）
- □ 会员标签背景透明度约 0.20（极浅粉色）

---

## Visual Weight 视觉重量

- □ ProfileCard 为页面视觉重心（最大、最显眼的单个元素）
- □ Section Label 视觉权重最低（小字、灰色、无背景）
- □ 注销账号行有适度的视觉警示感（粉色），但不过分恐吓（非红色）
- □ Toggle ON 状态在视觉上明显突出（品牌粉色渐变）
- □ 整页视觉重量均匀分布，无某区域过于沉重

---

## Alignment 对齐

- □ 所有 GroupCard 左右边缘对齐（同一水平 margin）
- □ 所有 Section Label 左边缘与 GroupCard 左边缘对齐
- □ 所有 Row 内图标垂直居中
- □ 所有 Row 内文字垂直居中
- □ 右侧控件（Toggle/Chevron/副文字）垂直居中
- □ 导航栏标题水平居中
- □ ProfileCard 内所有元素垂直居中

---

## 状态指示器

- □ Toggle 正确显示 ON 状态（粉色轨道 + 右侧 Thumb）
- □ Segment Picker 正确显示"浅色"为选中态（白色背景+阴影）
- □ 会员兑换行 Chevron 向下（表示折叠/可展开）
- □ 所有跳转行 Chevron 向右（表示可导航）

---

## 颜色符合 Design Token

- □ 主品牌粉：#FFB7C5（Toggle、Slider Thumb、Icon 等）
- □ 深品牌粉：#FF85A1（Toggle 渐变终点、危险文字、Badge 文字）
- □ 主文字：#3A3A4A
- □ 次要文字：#8A8A9A
- □ Chevron：约 #C0C0CC
- □ 无使用规范外的颜色（无随意使用的蓝色、纯红色等）

---

## 应用名拼写

- □ 如页面中出现 App 名称，必须拼写为 "yuoyuo"（全小写）
- □ 当前设计稿页面（设置页）未显示 App 名称，此条款不适用（N/A）

---

## 综合验收标准

- □ 整体视觉风格与其他页面（首页/聊天页/登录页等）保持一致
- □ 页面加载后无内容跳动或布局偏移（CLS = 0）
- □ 所有文字清晰可读，无截断或溢出
- □ 设计稿与实现之间视觉差异 ≤ 5%（即一致度 ≥ 95%）
- □ 页面在 iPhone 14 Pro Max（430pt 宽）和 iPhone SE（375pt 宽）上均正常显示

---

**验收通过标准：** 以上所有 □ 项均打勾，且整体视觉一致度 ≥ 95%。
如发现不符合项，记录 issue 并标注具体元素名称和期望/实际值对比。
