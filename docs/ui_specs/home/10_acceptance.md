# 10 Acceptance Checklist — 首页 Home

Pixel Perfect 验收标准。目标：整体视觉一致度 ≥ 95%。

---

## 一、全局 Layout

- [ ] 页面画布尺寸 390 × 844 pt，@2x 输出 780 × 1688 px，@3x 输出 1170 × 2532 px
- [ ] 页面背景是否直接使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` 或深色模式使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- [ ] Status Bar 高度 47 pt，背景透明，继承页面色
- [ ] Header 高度约 56 pt，位于 Safe Area Top（47 pt）正下方
- [ ] Bottom Tab Bar 高度 83 pt（含 Safe Area Bottom 34 pt），固定在页面最底部
- [ ] 主内容区在 Header 和 Tab Bar 之间，可垂直滚动
- [ ] 所有内容区元素不覆盖 Safe Area Bottom（34 pt）

---

## 二、Spacing / Padding / Margin

- [ ] Hero Card 左右外边距各 16 pt
- [ ] 快速操作瓷砖区左右外边距各 16 pt
- [ ] Section Header 左侧文字内边距 20 pt，右侧链接内边距 16 pt
- [ ] 对话列表行左内边距 20 pt，右内边距 16 pt
- [ ] Hero Card 距 Header 下方约 12 pt
- [ ] 快速操作区距 Hero Card 下方约 16 pt
- [ ] Section 标题区距快速操作区下方约 20 pt
- [ ] 两个对话行之间间距约 4 pt（或视觉上无分隔线，靠间距区分）
- [ ] QuickAction 三格之间 Gap 约 12 pt
- [ ] 头像与文字块间距约 14 pt

---

## 三、Radius（圆角）

- [ ] Hero Card 圆角 24 pt，四角均匀
- [ ] 快速操作瓷砖圆角 16 pt
- [ ] "开始聊天"按钮圆角 16 pt
- [ ] 所有头像圆形（radius-full = 9999 pt）
- [ ] Tab Active 指示圆点为正圆（radius-full）
- [ ] Bottom Tab Bar 顶部无圆角（直线上边框）

---

## 四、Shadow（阴影）

- [ ] Hero Card 有粉色柔和阴影（blur 约 20 pt，y-offset 约 4 pt，颜色 rgba(255,183,197,0.15)）
- [ ] 快速操作瓷砖有极轻阴影（blur 约 8 pt，rgba(0,0,0,0.06)）
- [ ] 心形宝珠外有紫色 glow 阴影（blur 约 40 pt，rgba(200,182,255,0.50)）
- [ ] Bottom Tab Bar 顶部有轻微阴影（blur 约 12 pt，向上方向）
- [ ] 用户头像右上角有粉色 glow 效果
- [ ] 若用户尚未上传头像，右上角是否显示空白占位头像而非角色头像
- [ ] 对话行角色头像无明显阴影（或极轻）

---

## 五、Blur 效果

- [ ] Hero Card 信息区（名称+状态+按钮所在区域）有 backdrop-filter blur，约 16 pt
- [ ] 快速操作瓷砖背景有轻微 backdrop-filter blur，约 8 pt
- [ ] Bottom Tab Bar 有 backdrop-filter blur，约 20 pt
- [ ] 心形宝珠外发光使用 blur 滤镜（非 box-shadow），约 40 pt
- [ ] 英雄卡片背景图本身无 blur（清晰的云彩插图）

---

## 六、Background / Gradient（背景/渐变）

- [ ] 页面背景图是否保留原始梦幻云层、暖光与星点氛围，无重画痕迹
- [ ] 英雄卡片背景渐变：从底部暖黄（#F5D89C）过渡到顶部浅紫粉（#D0A8D8），方向正确（下→上）
- [ ] 心形宝珠主体渐变：粉→蓝紫（#FFB7C5→#A89FD8），方向约 135°（右上→左下）
- [ ] 宝珠高光：白色→透明，约 45° 方向
- [ ] 是否未将页面背景替换为纯色或代码渐变
- [ ] Tab Bar 背景：接近纯色，rgba(255,248,243,0.92)，无明显渐变方向

---

## 七、Typography（字体 / 字号 / 字重 / 行高）

- [ ] "yuoyuo" App 名：SF Pro Rounded，约 26 pt，Bold，颜色 #3A3A4A，字母全小写
- [ ] "神无月凛"（Hero Card）：PingFang SC，约 22 pt，SemiBold，颜色 #3A3A4A，居中
- [ ] "刚刚和你聊过 · 心情：温柔"：PingFang SC，约 13 pt，Regular，颜色 #8E8E9A，居中
- [ ] "开始聊天 →"：PingFang SC / SF Pro Rounded，约 15 pt，Medium，颜色 #FF7A9A
- [ ] 瓷砖标签（兑换会员/切换角色/设置）：PingFang SC，约 13 pt，Regular，颜色 #3A3A4A
- [ ] "最近的......"：PingFang SC，约 16 pt，Bold，颜色 #3A3A4A
- [ ] "查看全部 >"：PingFang SC，约 13 pt，Regular，颜色 #8E8E9A
- [ ] 对话行角色名（神无月凛/桃乐丝）：PingFang SC，约 16 pt，SemiBold，颜色 #3A3A4A
- [ ] 对话预览文字（两行）：PingFang SC，约 14 pt，Regular，颜色 #8E8E9A
- [ ] 时间戳（22:18/昨天）：PingFang SC，约 13 pt，Regular，颜色 #8E8E9A
- [ ] Tab 标签文字：PingFang SC，约 10 pt，Regular，Active #FFB7C5，Inactive #ADADB8
- [ ] 所有中文字体一致（PingFang SC 或 HarmonyOS Sans SC），无 fallback 到衬线字体

---

## 八、所有组件尺寸

- [ ] Hero Card：宽约 358 pt，高约 280 pt
- [ ] 心形宝珠：约 120 × 130 pt，水平居中
- [ ] "开始聊天"按钮：约 120 × 38 pt，位于卡片右下角
- [ ] 快速操作每格：约 111 × 90 pt（三等分）
- [ ] 功能图标（瓷砖内）：约 32 × 32 pt
- [ ] 用户头像（右上角）：圆形约 40 pt 直径
- [ ] 空白占位头像若出现，是否保持中性、无角色特征
- [ ] 对话行角色头像：圆形约 56 pt 直径
- [ ] 对话列表每行：高度约 80 pt
- [ ] Section Header 行高：约 36 pt
- [ ] Tab 图标：约 24 × 24 pt
- [ ] Tab Active 指示点：约 4 pt 直径
- [ ] 未读红点：约 8 pt 直径

---

## 九、Glass Effect 透明度

- [ ] Hero Card 信息区玻璃层：rgba(255,255,255,0.60)（估算值），有毛玻璃效果
- [ ] 快速操作瓷砖：rgba(255,255,255,0.80)（估算值）
- [ ] Tab Bar 背景：rgba(255,248,243,0.92)（估算值）
- [ ] 宝珠高光：rgba(255,255,255,0.80)，位于左上角
- [ ] 宝珠外发光：rgba(200,182,255,0.50)（估算值）
- [ ] 卡片边框：rgba(255,183,197,0.25)（估算值）

---

## 十、Visual Weight（视觉重量）

- [ ] 页面视觉重心在上方 1/3（Hero Card 区域），符合设计意图
- [ ] 心形宝珠是页面最突出的视觉元素，有发光强调
- [ ] 快速操作区视觉轻盈，不抢夺宝珠主体地位
- [ ] 对话列表区信息密度适中，不产生拥挤感
- [ ] Tab Bar 视觉重量低于内容区（轻透明背景）
- [ ] "开始聊天"CTA 按钮在卡片中视觉清晰但不过度突出

---

## 十一、Alignment（对齐）

- [ ] "yuoyuo" 文字与用户头像垂直居中对齐
- [ ] 心形宝珠在 Hero Card 内水平居中
- [ ] 角色名"神无月凛"水平居中
- [ ] 状态文字水平居中
- [ ] 三个快速操作瓷砖等宽均分，图标+文字在各格内居中
- [ ] 对话行：头像垂直居中，文字块左对齐，时间+红点右对齐
- [ ] Section Header 左右文字基线对齐
- [ ] Tab 图标+文字在各格内水平垂直居中
- [ ] 所有内容区左边缘严格遵循 16 pt 或 20 pt 内边距（不混用）

---

## 十二、Safe Area 遵守

- [ ] 状态栏时间与图标不超出 Safe Area Top（47 pt）范围
- [ ] "yuoyuo" App 名位于 Safe Area Top 之下（Y > 47 pt）
- [ ] 底部 Tab Bar 内容区高于 Safe Area Bottom（34 pt）底线
- [ ] Tab 文字和图标不进入 Home Indicator 区域（Y < 810 pt）
- [ ] 页面内容在底部留有足够 padding（约 83 pt）避免被 Tab Bar 遮挡

---

## 十三、底部栏 / Tab 栏

- [ ] 共 4 个 Tab（首页/聊天/角色/设置），等宽均分
- [ ] 首页 Tab 为 Active 状态（粉色图标+文字+指示点）
- [ ] 其余 3 个 Tab 为 Inactive 状态（灰色图标+文字，无指示点）
- [ ] Active 指示点位于图标正下方，直径约 4 pt
- [ ] Tab Bar 顶部有细线分隔或轻微阴影（上边界清晰）
- [ ] Tab Bar 背景有毛玻璃效果

---

## 十四、状态指示器

- [ ] 神无月凛对话行有未读红点（直径约 8 pt，颜色 #FFB7C5）
- [ ] 桃乐丝对话行有未读红点（同上）
- [ ] 两个未读红点位于时间戳正下方，右对齐
- [ ] 心情状态文字"温柔"清晰可读（非截断，非省略）
- [ ] Tab Active 状态通过颜色变化 + 指示点双重呈现

---

## 十五、颜色 100% 符合 Design Token

- [ ] 页面背景色：#FFF0F3（无偏色）
- [ ] 主文字色：#3A3A4A（无偏色）
- [ ] 次级文字色：#8E8E9A
- [ ] 主强调色：#FFB7C5（Tab Active、未读点）
- [ ] 辅助强调色：#C8B6FF（切换角色图标）
- [ ] 蓝色辅助：#A7C7E7（设置图标）
- [ ] CTA 文字色：#FF7A9A（"开始聊天"）
- [ ] Inactive Tab 色：#ADADB8

---

## 十六、App 名称拼写

- [ ] App 名称显示为 "yuoyuo"（全小写 y-u-o-y-u-o，共6字母）
- [ ] 无大写，无空格，无连字符，无下划线
- [ ] 字母间距正常，无额外字间距
- [ ] 使用 SF Pro Rounded 字体（英文圆润风格）

---

## 验收通过标准

| 等级 | 条件 |
|------|------|
| ✅ 通过 | 所有 □ 勾选，或仅有标注"估算值"的尺寸存在 ≤5% 偏差 |
| ⚠️ 条件通过 | ≤5 项未通过，且均为 Spacing/Shadow 等视觉次要属性 |
| ❌ 不通过 | 任一以下情况：颜色错误 / 字体错误 / 组件缺失 / App 名称拼写错误 / Safe Area 违规 / 核心组件尺寸偏差 >20% |

**目标：整体视觉一致度 ≥ 95%**
