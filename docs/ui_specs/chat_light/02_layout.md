# 02 Layout — 聊天页 Chat（浅色模式）

## 画布规格
| 属性 | 值 |
|------|-----|
| 画布尺寸 | 1024 × 1536 px（设计稿） |
| 逻辑设备 | iPhone 14，390 × 844 pt |
| 像素密度 | @3x（约 3:1 比例） |
| 安全区顶部 | 47 px（逻辑值）/ 141 px（设计稿估算值） |
| 安全区底部 | 34 px（逻辑值）/ 102 px（设计稿估算值） |

---

## 整体层级结构（Z轴从底到顶）

```
Z0  Background Layer（渐变背景 + 光晕装饰）
Z1  Status Bar（系统状态栏）
Z2  Header Bar（角色信息栏，fixed）
Z3  Message Scroll Area（可滚动消息区域）
Z4  Composer Bar（底部浮动输入框，fixed）
Z5  Home Indicator（系统 Home Bar）
```

---

## 各区域规格

### 1. Status Bar（状态栏）
| 属性 | 值 |
|------|-----|
| 高度 | 47 pt（约 141 px 估算值） |
| 宽度 | 390 pt（满宽） |
| 背景 | 透明（继承背景渐变） |
| 内容 | 左：时间"9:41"；右：信号/WiFi/电池图标 |
| 字色 | #3A3A4A（深色） |

### 2. Header Bar（角色信息栏）
| 属性 | 值 |
|------|-----|
| 高度 | 约 80 pt（估算值） |
| 宽度 | 满宽 390 pt |
| 背景 | rgba(255, 255, 255, 0.55)，毛玻璃效果，blur 约 20px |
| 圆角 | 底部左右圆角约 20 pt（估算值） |
| 阴影 | 底部柔和投影，rgba(0,0,0,0.06) blur 12px |
| Padding 水平 | 左 20 pt，右 20 pt（估算值） |
| Padding 垂直 | 上 12 pt，下 12 pt（估算值） |
| 布局 | Flex Row，align-items: center，space-between |
| 固定 | fixed/sticky，始终显示 |

Header 内部元素布局（从左到右）：
```
[返回箭头 "<"] [头像 48×48] [角色名称+在线状态] [弹性空间] ["…" 更多按钮]
```

| 子元素 | 尺寸/规格 |
|--------|-----------|
| 返回按钮"<" | 触摸区 44×44 pt；图标约 12×20 pt（估算值） |
| 头像 | 48×48 pt，圆形裁切（估算值） |
| 角色名称"小屿" | 字号 17 pt，font-weight 600（估算值） |
| 在线状态"温柔在线" | 字号 13 pt，前置蓝点 6×6 pt（估算值） |
| 更多按钮"…" | 触摸区 44×44 pt（估算值） |
| 名称与在线状态 gap | 约 2 pt（估算值） |
| 头像与文字组 gap | 约 10 pt（估算值） |

### 3. Message Scroll Area（消息滚动区域）
| 属性 | 值 |
|------|-----|
| Top | 紧接 Header 底部（约 127 pt 从顶部，估算值） |
| Bottom | 紧接 Composer 顶部（约 710 pt 从顶部，估算值） |
| 高度 | 约 583 pt（估算值） |
| Padding 水平 | 左右各 16 pt（估算值） |
| Padding 顶部 | 约 12 pt |
| Padding 底部 | 约 16 pt |
| 滚动方向 | 垂直滚动（overflow-y: scroll） |
| 滚动条 | 隐藏 |
| 背景 | 透明（继承背景渐变） |

消息区域垂直间距：
```
日期分隔符
  ↓ gap: 约 16 pt
AI Bubble 1（早上好…）
  ↓ gap: 约 10 pt（同方向连续消息）
User Bubble（做了个奇怪的梦）
  ↓ gap: 约 10 pt
AI Bubble 2（讲给我听呀…）
  ↓ gap: 约 8 pt（同发送者相邻消息）
AI Voice Bubble（语音播放条）
  ↓ gap: 约 10 pt
User Bubble（好。）
  ↓ gap: 约 10 pt
AI Typing Bubble（···）
```

### 4. Date Separator（日期分隔符）
| 属性 | 值 |
|------|-----|
| 宽度 | 自适应文字宽度，水平居中 |
| 高度 | 约 28 pt（估算值） |
| 文字 | "今天 · 上午 9:41" |
| 字号 | 约 12 pt（估算值） |
| 颜色 | #999999（中灰，估算值） |
| 对齐 | 水平居中 |
| Margin top/bottom | 约 8 pt 各方向（估算值） |

### 5. Message Bubbles — AI（左对齐）
| 属性 | 值 |
|------|-----|
| 最大宽度 | 约 260 pt（估算值，约屏宽 67%） |
| 对齐 | 左对齐（flex-start） |
| Padding 内 | 约 14 pt 垂直，16 pt 水平（估算值） |
| 圆角 | 右上/右下/左上约 20 pt，左下约 6 pt（气泡尾部，估算值） |
| 背景 | rgba(255, 255, 255, 0.75)，半透明白色 |
| 字色 | #3A3A4A |
| 字号 | 约 16 pt（估算值） |
| Margin Left | 约 16 pt（估算值） |

### 6. Message Bubbles — User（右对齐）
| 属性 | 值 |
|------|-----|
| 最大宽度 | 约 260 pt（估算值，约屏宽 67%） |
| 对齐 | 右对齐（flex-end） |
| Padding 内 | 约 14 pt 垂直，16 pt 水平（估算值） |
| 圆角 | 左上/左下/右下约 20 pt，右上约 6 pt（气泡尾部，估算值） |
| 背景 | #A7C7E7（天蓝色，实色） |
| 字色 | #FFFFFF |
| 字号 | 约 16 pt（估算值） |
| Margin Right | 约 16 pt（估算值） |

### 7. AI Voice Bubble（语音播放器 Bubble）
| 属性 | 值 |
|------|-----|
| 宽度 | 约 300 pt（估算值，较宽） |
| 高度 | 约 90 pt（估算值，内含两行：波形+标注） |
| 布局 | 内部 Flex Column |
| 背景 | rgba(255, 255, 255, 0.75) |
| 圆角 | 与 AI Bubble 相同（估算值） |
| Padding | 约 16 pt（估算值） |
| 内部 Row 1 | Flex Row：[播放按钮] [波形可视化] [时长"0:18"] |
| 内部 Row 2 | 标注文字"AI朗读 · 可点击播放" |
| 间距 Row1-Row2 | 约 8 pt（估算值） |

语音 Bubble 内部元素：
| 元素 | 规格 |
|------|------|
| 播放按钮（三角形） | 约 32×32 pt 圆形容器，图标约 14 pt（估算值），颜色 #FFB7C5 |
| 波形可视化 | 约 170 pt 宽，多条竖线，颜色渐变（粉→紫，估算值） |
| 时长文字"0:18" | 约 13 pt，颜色 #999999（估算值） |
| 标注文字 | 约 12 pt，颜色 #AAAAAA，水平居中（估算值） |

### 8. AI Typing Indicator（打字中指示器）
| 属性 | 值 |
|------|-----|
| 宽度 | 约 72 pt（估算值） |
| 高度 | 约 48 pt（估算值） |
| 布局 | Flex Row，3个圆点，居中对齐 |
| 背景 | rgba(255, 255, 255, 0.75) |
| 圆角 | 与 AI Bubble 相同（估算值） |
| 圆点直径 | 约 10 pt（估算值） |
| 圆点颜色 | #FFB7C5（樱花粉） |
| 圆点间距 | 约 6 pt（估算值） |
| 对齐 | 左对齐，Margin Left 约 16 pt（估算值） |

### 9. Composer Bar（底部浮动输入框）
| 属性 | 值 |
|------|-----|
| 高度 | 约 64 pt（估算值） |
| 宽度 | 约 358 pt（距左右各约 16 pt 边距，估算值） |
| 底部距离 | 距 Home Indicator 上方约 12 pt（估算值） |
| 背景 | rgba(255, 255, 255, 0.65)，毛玻璃效果 |
| 圆角 | 约 32 pt（高度的一半，胶囊形，估算值） |
| 阴影 | rgba(0,0,0,0.08) blur 16px，向上偏移 -4px（估算值） |
| 布局 | Flex Row，align-items: center，gap 约 10 pt |
| Padding 水平 | 约 12 pt 左右（估算值） |
| Position | fixed，bottom 约 46 pt（估算值，含 Home Indicator 高度） |

Composer 内部元素：
| 元素 | 规格 |
|------|------|
| "+" 按钮 | 约 36×36 pt 圆形，线框"+"图标，颜色 #BBBBBB（估算值） |
| 输入框 PlaceholderText | "想和小屿说点什么..."，颜色 #BBBBBB，字号约 15 pt（估算值） |
| 发送按钮 | 约 40×40 pt 圆形，背景 #FFB7C5（樱花粉），图标白色纸飞机，约 18 pt（估算值） |

### 10. Home Indicator（系统 Home Bar）
| 属性 | 值 |
|------|-----|
| 高度 | 5 pt（Home Bar 细线，估算值） |
| 宽度 | 约 134 pt（估算值） |
| 颜色 | #3A3A4A（深色） |
| 位置 | 底部居中，距底边约 8 pt（估算值） |
| 圆角 | 2.5 pt（全圆，估算值） |

### 11. Background Layer（背景层）
| 属性 | 值 |
|------|-----|
| 尺寸 | 满屏 390×844 pt |
| 类型 | 径向渐变 + 线性渐变叠加 |
| 主渐变 | 从顶部 #FFF0EC（奶油白）到底部 #E8D5F5（薰衣草紫），约 180° 方向（估算值） |
| 中部光晕 | 椭圆形白色光斑，位于画面中央偏下，opacity 约 0.4（估算值） |
| 右下光晕 | 薰衣草紫光晕，opacity 约 0.3（估算值） |

---

## Padding / Spacing 总览

| 区域 | Padding/Gap |
|------|-------------|
| 全局水平 Padding | 16 pt（估算值） |
| Header 内部水平 Padding | 20 pt（估算值） |
| Bubble 之间纵向 Gap | 8–12 pt（估算值） |
| AI Bubble 内部 Padding | 14 pt 垂直 × 16 pt 水平（估算值） |
| User Bubble 内部 Padding | 14 pt 垂直 × 16 pt 水平（估算值） |
| Voice Bubble 内部 Padding | 16 pt 四周（估算值） |
| Composer 内部元素 Gap | 10 pt（估算值） |
| Composer 距屏底 | 46 pt（估算值） |

---

## 滚动区域说明
- 消息列表区域为唯一可滚动区域
- Header 和 Composer 均为 Fixed 定位，不参与滚动
- 新消息到达时，列表自动滚动到底部（auto-scroll behavior）
- 用户手动上滑时，auto-scroll 暂停（scroll-anchoring behavior）
