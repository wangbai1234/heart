# 06 Interactions — 登录页 Login

⚠️ 标注「设计稿未定义，建议参考 Motion Storyboard」的状态在 PNG 设计稿中未体现，需补充定义。

---

## 一、页面进入动画

### 方案一：顺序淡入（推荐）
各层元素依次从下向上淡入（stagger 效果）：

| 序号 | 元素 | 延迟 | 动效 |
|------|------|------|------|
| 1 | 插画区背景（AnimeIllustration） | 0ms | fade-in，duration 500ms，ease-out |
| 2 | 玻璃心形（GlassHeart） | 150ms | fade-in + scale(0.8→1.0)，duration 600ms，spring easing |
| 3 | "yuoyuo" 字标 | 280ms | fade-in + translateY(12px→0)，duration 400ms，ease-out |
| 4 | Tagline | 360ms | fade-in + translateY(8px→0)，duration 350ms，ease-out |
| 5 | FormCard（含内部元素） | 440ms | fade-in + translateY(16px→0)，duration 400ms，ease-out |
| 6 | LegalText | 520ms | fade-in，duration 300ms，ease-out |
| 7 | RedeemLink | 580ms | fade-in，duration 300ms，ease-out |

### 方案二：整体淡入（备选，简化实现）
全页内容整体 opacity 0→1，duration 400ms，ease-out。

⚠️ 设计稿未定义具体进入动画方案，建议参考 Motion Storyboard。

---

## 二、页面退出动画

### 触发「发送登录链接」后（成功态）
- 主按钮变为 Loading 状态（spinner 替换文字），duration 150ms
- 请求成功后：整页 fade-out（opacity 1→0），duration 300ms，ease-in
- 跳转至「邮件已发送」确认页（slide-up 或 fade，取决于路由配置）

⚠️ 设计稿未定义退出动画，建议参考 Motion Storyboard。

### 触发「兑换码激活」后
- 轻微 tap 反馈（RedeemLink 颜色闪变）
- 整页 slide-left（向左滑出），进入兑换码页面

⚠️ 设计稿未定义，建议参考 Motion Storyboard。

---

## 三、持续动效（Ambient Animation）

### 玻璃心形漂浮
- 类型：垂直方向轻微上下漂浮（float）
- 振幅：±8px（估算值）
- 周期：~3000ms
- 曲线：ease-in-out / sin wave
- 循环：infinite

### 心形呼吸光晕（Pulse）
- 类型：外发光 blur 值轻微脉动
- 范围：blur 50px → 70px → 50px（估算值）
- 周期：~4000ms
- 循环：infinite

⚠️ 设计稿未定义持续动效参数，建议参考 Motion Storyboard。

### 樱花花瓣飘落（可选）
- 类型：Lottie 动画叠加于插画之上
- 速度：缓慢随机飘落
- ⚠️ 设计稿未定义，建议参考 Motion Storyboard。

---

## 四、组件交互状态

### EmailInput（邮箱输入框）

| 状态 | 触发方式 | 视觉反馈 |
|------|---------|---------|
| Default | 页面加载完成 | 信封图标 + 「你的邮箱」占位文字 |
| Focused | 点击输入框 | 键盘弹起；光标显示；⚠️ 聚焦样式设计稿未定义，建议参考 Motion Storyboard（推荐：图标色加深，底部分隔线变为主粉色 #FFB7C5） |
| Typing | 用户输入 | 占位文字消失，显示输入字符 |
| Filled | 输入完成 | 显示完整邮箱地址 |
| Error | 邮箱格式错误/发送失败 | ⚠️ 设计稿未定义，建议：分隔线变为 #FF5252（红色），输入框下方显示错误提示文字 |
| Disabled | N/A | ⚠️ 设计稿未定义 |

**键盘行为：**
- 键盘弹起时，FormCard 上移，插画区压缩或隐藏（KeyboardAvoidingView）
- 点击页面其他区域（非输入框）时，键盘收起

---

### PrimaryButton（发送登录链接按钮）

| 状态 | 触发方式 | 视觉反馈 |
|------|---------|---------|
| Default | 页面加载 | 渐变粉色背景，白色文字，轻微阴影 |
| Pressed | 手指按下 | scale(0.97) + 背景加深 ~10%；duration 100ms，bounce easing（⚠️ 设计稿未定义） |
| Released | 手指抬起 | scale(1.0) 恢复；duration 150ms（⚠️ 设计稿未定义） |
| Loading | 点击后请求发送中 | 文字替换为 spinner（白色 24px）或「发送中…」；按钮不可再次点击（⚠️ 设计稿未定义） |
| Success | 请求成功 | 短暂显示「✓ 已发送」或直接页面跳转（⚠️ 设计稿未定义） |
| Error | 请求失败 | 按钮抖动（shake animation）+ Toast 提示（⚠️ 设计稿未定义） |
| Disabled | 邮箱为空或格式错误 | opacity 0.5，不可点击（⚠️ 设计稿未定义） |

---

### LegalText（协议链接）

| 状态 | 触发方式 | 视觉反馈 |
|------|---------|---------|
| Default | 静态显示 | 基础文字灰色，链接粉色 |
| Link Pressed（《用户协议》） | 点击 | 颜色加深（⚠️ 设计稿未定义）；打开 WebView/外部浏览器 |
| Link Pressed（《隐私政策》） | 点击 | 同上 |

---

### RedeemLink（兑换码入口）

| 状态 | 触发方式 | 视觉反馈 |
|------|---------|---------|
| Default | 静态显示 | 深色文字 + 「→」 |
| Pressed | 点击 | ⚠️ 设计稿未定义，建议：文字颜色变为 #FFB7C5（主粉色），「→」向右轻移 4px，duration 150ms |
| Navigation | 点击完成 | 跳转至兑换码激活页 |

---

## 五、键盘行为详细说明

| 场景 | 行为 |
|------|------|
| 键盘弹起 | FormCard 及以下区域上移，确保输入框可见；插画区可安全压缩至 0 |
| 键盘收起 | 布局平滑恢复；duration ~300ms，ease-in-out |
| 点击输入框外部 | 收起键盘（dismissKeyboard）|
| 点击主按钮 | 先收起键盘，再执行提交逻辑（或同步执行） |

---

## 六、Loading / Error / Empty 状态汇总

| 状态 | 适用范围 | 设计稿定义 |
|------|---------|-----------|
| Loading（提交中） | PrimaryButton | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Error（邮箱格式错） | EmailInput | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Error（网络错误） | 全局 Toast | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Empty（邮箱为空） | PrimaryButton Disabled | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Success（发送成功） | 页面跳转 | ⚠️ 设计稿未定义，建议参考 Motion Storyboard |
| Skeleton | 本页不适用（内容固定） | N/A |

---

## 七、页面转场汇总

| 来源 | 目标 | 转场类型 |
|------|------|---------|
| Splash / 冷启动 | 登录页 | Fade / Cross-dissolve |
| 登录页 | 邮件已发送确认页 | Slide-up（Modal Push，估算值）（⚠️ 设计稿未定义） |
| 登录页 | 兑换码激活页 | Slide-left（Standard Push）（⚠️ 设计稿未定义） |
| 登录页 | 用户协议/隐私政策 | Present Modal（Sheet）（⚠️ 设计稿未定义） |
| 登录成功 | 主界面 Home | Fade / Replace（不保留返回栈） |
