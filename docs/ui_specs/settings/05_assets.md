# 05 Assets — 设置页 Settings

本文件覆盖 Settings 页资源真相。旧版“代码渐变背景”为非权威内容。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 浅色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover` |
| 深色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | 全屏 `cover` |

## 2. 背景规则

- Light：必须使用 `亮色背景图.png`
- Dark：必须使用 `暗色背景图.png`
- 不允许改成新的代码渐变版本
- 不允许换成其他 Banner 图

## 3. Avatar 规则

- Settings 设计稿中的 profile avatar 属于运行态用户头像
- 若用户已绑定真实头像，必须使用真实头像
- 若用户尚未上传头像，必须使用“空白占位头像组件”
- 不允许使用角色资源作为默认 profile avatar
- 不允许生成“晨曦”新头像

## 4. 必须由组件实现的元素

- ProfileCard
- SettingRow
- SegmentedControl
- Slider
- Toggle
- Chevron
- Dialog
- Toast
- BottomSheet

## 5. 禁止事项

- 禁止用图片代替 Toggle / Slider / SegmentedControl
- 禁止自绘新背景
- 禁止生成新的 profile 插画
