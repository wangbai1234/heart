# 05 Assets — Redeem 兑换页

本文件覆盖 Redeem 页资源真相。旧版“代码渐变背景 + 重新画礼盒”的建议失效。

## 1. 必须引用的复杂资源

| 用途 | 绝对路径 | 使用方式 |
|---|---|---|
| 浅色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` | 全屏 `cover` |
| 深色模式全屏背景 | `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png` | 全屏 `cover` |
| 礼盒主视觉 | `/Users/wanglixun/heart/assets/backgrounds/兑换页礼品盒.png` | 卡片内 `contain`，完整显示主体 |

## 2. 背景规则

- Light：必须使用 `亮色背景图.png`
- Dark：必须使用 `暗色背景图.png`
- 不允许自己绘制天空和云层

## 3. 礼盒规则

- 卡片顶部礼盒必须直接使用 `兑换页礼品盒.png`
- 不允许改成新生成礼盒
- 不允许仅用 CSS 画一个盒子近似替代
- 礼盒只能等比缩放，不能裁掉主体

## 4. 必须由组件实现的元素

- OTP 输入格
- 粘贴按钮
- 立即激活按钮
- FAQ 折叠卡
- Toast / Error / Success 反馈

## 5. 禁止事项

- 禁止重新生成礼盒
- 禁止改成代码渐变背景
- 禁止用图片代替输入格、按钮、Accordion
