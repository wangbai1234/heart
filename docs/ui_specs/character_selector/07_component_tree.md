# 07 Component Tree — 角色页 Character Selector

```
Page (CharacterSelectorPage)
├── PageBackground                              # 全页奶油底色 #FFF8F3，Z-index 0
│
├── StatusBar                                   # 系统状态栏，Z-index 100，高度 47 pt
│   ├── TimeLabel ("9:41")                      # 左侧时间文字
│   └── SystemIconGroup                         # 右侧系统图标组
│       ├── SignalIcon                           # 信号强度图标（3格）
│       ├── WiFiIcon                             # WiFi 扇形图标
│       └── BatteryIcon                         # 电池图标（满格）
│
├── NavigationBar                               # 顶部导航栏，fixed top，高度 44 pt，Z-index 90
│   ├── DismissButton                           # 左侧 ∨ 关闭按钮，44×44 pt touch target
│   │   └── ChevronDownIcon                     # 向下箭头图标，20×12 pt
│   └── PageTitle ("选择一位陪伴你的人")          # 居中标题文字，17 pt Medium
│
├── ScrollableContent                           # 可滚动主内容区，padding top 91 pt
│   │
│   ├── HeroSection                             # 天空英雄区，高度约 280 pt，Z-index 10
│   │   ├── HeroBackgroundImage                 # 动漫天空插画，全覆盖
│   │   │   ├── SkyGradientLayer                # 粉紫橙天空渐变
│   │   │   ├── CloudsLayer                     # 多层蓬松云彩
│   │   │   ├── MoonOrb                         # 右上角白色发光圆（月亮）
│   │   │   └── CherryBlossomParticles          # 樱花/光斑装饰粒子
│   │   ├── HeroBottomFadeOverlay               # 底部渐变叠加，高度约 80 pt
│   │   └── GlassHeart                          # 玻璃心形品牌图标，居中，约 120×110 pt
│   │       ├── HeartShape                      # 心形轮廓路径
│   │       ├── GlassGradientFill               # 内部粉紫渐变半透明填充
│   │       ├── TopHighlight                    # 顶部白色高光弧
│   │       └── GlowEffect                      # 外部粉色发光效果
│   │
│   └── CharacterCardList                       # 角色卡列表，垂直 ScrollView，padding 16 pt
│       │
│       ├── CharacterCard [selected] (神无月 凛) # 第一张卡，已选中态
│       │   ├── CardBackground                  # 白色圆角背景，radius 20 pt
│       │   ├── CardShadow                      # 卡片投影层
│       │   ├── AvatarContainer                 # 头像容器，120×120 pt 圆形
│       │   │   ├── AvatarGlowRing              # 紫色渐变光晕描边
│       │   │   └── AvatarImage (avatar_shenWuYue_lin.png)  # 角色插画
│       │   ├── CharacterInfo                   # 文字信息区
│       │   │   ├── NameRow                     # 名字行，Flex Row
│       │   │   │   ├── CharacterName ("神无月 凛")   # 18 pt Bold
│       │   │   │   └── PersonalityTag ("御姐型")     # 紫色系 pill 标签
│       │   │   └── CharacterDescription        # 角色描述段落，13 pt Regular
│       │   └── SelectedIndicator               # 已选中：实心粉圆 + 白色勾，绝对定位右上
│       │       ├── CircleBackground            # 粉色圆形背景 #FFB7C5
│       │       └── CheckmarkIcon               # 白色勾图标
│       │
│       └── CharacterCard [default] (桃乐丝)    # 第二张卡，未选中默认态
│           ├── CardBackground                  # 白色圆角背景，radius 20 pt
│           ├── CardShadow                      # 卡片投影层
│           ├── AvatarContainer                 # 头像容器，120×120 pt 圆形
│           │   ├── AvatarGlowRing              # 蓝色渐变光晕描边
│           │   └── AvatarImage (avatar_taolesi.png)  # 角色插画
│           ├── CharacterInfo                   # 文字信息区
│           │   ├── NameRow                     # 名字行，Flex Row
│           │   │   ├── CharacterName ("桃乐丝")      # 18 pt Bold
│           │   │   └── PersonalityTag ("元气型")     # 蓝色系 pill 标签
│           │   └── CharacterDescription        # 角色描述段落，13 pt Regular
│           └── SelectButton                    # 未选中：描边"选择"按钮，绝对定位右上
│               └── ButtonLabel ("选择")         # 粉色文字，15 pt Medium
│
│   # 注：第三张角色卡推测存在，在列表下方，需滚动显示
│   # 实际卡片数量以产品需求为准
│
├── ConfirmCTABar                               # 底部固定区域，fixed bottom，Z-index 80
│   └── ConfirmButton                           # 确认选择胶囊按钮
│       ├── ButtonGradientBackground            # 粉色渐变背景
│       ├── ButtonShadow                        # 粉色光晕投影
│       └── ButtonLabel ("确认选择")             # 白色文字，17 pt Semibold
│
└── HomeIndicator                               # iOS 系统底部条，Z-index 90
    └── IndicatorBar                            # 深灰色横条，130×5 pt
```

---

## 节点说明

| 节点类型 | 说明 |
|---------|------|
| 大写开头（如 `CharacterCard`） | 可复用组件节点 |
| 小写开头（如 `cardBackground`） | 纯样式/装饰子元素，通常不需要独立组件 |
| `[selected]` / `[default]` | 组件当前状态标注 |
| `（估算值）` | 尺寸或位置为视觉估算，非精确测量 |

## 注意事项

1. CharacterCard 内的 SelectedIndicator 与 SelectButton 是互斥显示的，同一时刻只显示其中一个
2. GlassHeart 浮于 HeroBackgroundImage 之上，是独立层而非图片一部分
3. HeroBottomFadeOverlay 是 CSS/代码实现的渐变叠加层，而非图片资源
4. ScrollableContent 包含 HeroSection 和 CharacterCardList，两者均在滚动区域内（或 HeroSection 固定，待确认）
5. 第三张角色卡在 ScrollView 内，需向下滚动显示，组件树结构与前两张相同
