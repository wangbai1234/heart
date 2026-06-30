# 07 Component Tree — 登录页 Login

完整 ASCII 组件树，覆盖所有可见元素（含装饰性背景）。

---

```
Page（LoginScreen）
│
├── Background                          # 全页底色层（#FFF8F3 奶油白渐变）
│
├── IllustrationLayer                   # 插画背景层（Z-index 1）
│   ├── AnimeIllustration               # 动漫天空背景图片
│   │   ├── SkyGradient                 # 天空渐变（薰衣草紫→玫瑰粉→暖橙）
│   │   ├── CloudLayer_Far              # 远景云朵（小型，模糊）
│   │   ├── CloudLayer_Near             # 近景云朵（大型，蓬松，暖光）
│   │   ├── HorizonReflection           # 地平线水面反光
│   │   ├── RadialLightRays             # 放射状「神光」光线
│   │   └── SakuraPetals                # 装饰性樱花花瓣（4-6 片）
│   │
│   └── GlassHeart                      # 玻璃心形图标（Z-index 2）
│       ├── HeartBody                   # 心形主体（半透明渐变）
│       ├── HeartHighlight              # 白色折射高光（左上角条状）
│       ├── HeartSparkle                # 顶部闪光点（星形）
│       ├── HeartGlow_White             # 外发光（白色辉光）
│       └── HeartGlow_Pink              # 外发光（粉色软光晕）
│
├── SafeArea
│   ├── StatusBar                       # 系统状态栏（顶部，Z-index max）
│   │   ├── TimeLabel                   # 时间文字「9:41」
│   │   └── SystemIcons                 # 信号 + WiFi + 电池图标组
│   │       ├── SignalIcon              # 信号格图标
│   │       ├── WifiIcon                # WiFi 图标
│   │       └── BatteryIcon             # 电量图标
│   │
│   └── ContentArea                     # 主内容区（SafeArea 内）
│       │
│       ├── BrandZone                   # 品牌区（水平居中）
│       │   ├── BrandWordmark           # "yuoyuo" 字标（SF Pro Rounded Bold）
│       │   └── Tagline                 # 「独属于你的虚拟宇宙」（PingFang SC）
│       │
│       ├── FormCard                    # 登录表单卡（毛玻璃容器）
│       │   ├── GlassBackground         # 卡片毛玻璃背景层
│       │   ├── GlassBorder             # 卡片玻璃边框（半透明白色）
│       │   │
│       │   ├── EmailInputRow           # 邮箱输入行
│       │   │   ├── EmailIcon           # 信封图标（SVG，#FFB7C5）
│       │   │   └── EmailInput          # 邮箱文字输入框（placeholder：你的邮箱）
│       │   │
│       │   ├── Divider                 # 输入行下方分隔线（1px，半透明）
│       │   │
│       │   ├── HintText                # 说明文字（无密码登录说明）
│       │   │
│       │   └── PrimaryButton           # 「发送登录链接」主按钮
│       │       ├── ButtonBackground    # 渐变背景（#FFB7C5 → #FF8FAB）
│       │       ├── ButtonShadow        # 按钮投影（粉色软阴影）
│       │       └── ButtonLabel         # 按钮文字（白色，Medium）
│       │
│       ├── LegalZone                   # 协议区（水平居中）
│       │   └── LegalText               # 协议文字行
│       │       ├── LegalTextBase       # 基础文字（灰色）
│       │       ├── AgreementLink       # 《用户协议》链接（粉色）
│       │       ├── LegalTextConnector  # 「与」连接词（灰色）
│       │       └── PrivacyLink         # 《隐私政策》链接（粉色）
│       │
│       └── RedeemZone                  # 兑换码区（水平居中）
│           └── RedeemLink              # 「我有兑换码，直接激活 →」可点击文字
│               ├── RedeemLinkText      # 文字部分
│               └── RedeemArrow         # 「→」箭头符号
│
└── BottomSafeArea                      # iOS Home Indicator 安全区（空白）
```

---

## 节点说明

| 节点 | 类型 | 交互性 |
|------|------|--------|
| `Page（LoginScreen）` | 容器 | 无 |
| `Background` | 视图/色块 | 无 |
| `AnimeIllustration` | Image | 无（仅展示，可配 Lottie 叠层） |
| `GlassHeart` | Image / Lottie | 无（可有环境动效） |
| `StatusBar` | 系统组件 | 系统控制 |
| `BrandWordmark` | Text | 无 |
| `Tagline` | Text | 无 |
| `FormCard` | 容器 | 无（子元素有交互） |
| `EmailInput` | TextInput | 可聚焦、可输入 |
| `Divider` | 视图/线条 | 无 |
| `HintText` | Text | 无 |
| `PrimaryButton` | Pressable / Button | 可点击、有 Loading 状态 |
| `LegalText` | Text + 内联链接 | 链接可点击 |
| `AgreementLink` | Text / Link | 可点击 |
| `PrivacyLink` | Text / Link | 可点击 |
| `RedeemLink` | Pressable / Link | 可点击 |
| `BottomSafeArea` | SafeArea 占位 | 无 |

---

## 层叠顺序（Stacking Order，从下至上）

```
1. Background（页面底色渐变）
2. AnimeIllustration（插画背景）
3. GlassHeart（漂浮心形，叠于插画之上）
4. ContentArea（品牌区 + 表单区 + 底部链接）
   └── FormCard（毛玻璃，位于内容区内）
5. StatusBar（始终最顶层）
```
