/**
 * HTML 转义工具 —— 用于把不受信任的文本插进 HTML 字符串（如 iframe srcDoc）。
 *
 * 背景：PremiseCardBase 把角色数据拼进 srcDoc 喂 iframe。数据源目前是手写的
 * 内置卡片，但 UGC 角色创作功能会让用户自己编辑这些字段（见
 * docs/UGC_PRESENTATION_GAPS.md 第 3 节），届时每个字段都是脚本注入入口。
 *
 * 注意：这两个函数只对 **HTML 文本节点** 上下文安全。插进 CSS 属性值
 * （如 `border-left: 2px solid ${accent}`）或 HTML 属性值时，转义救不了 ——
 * 那些位置必须用取值白名单校验（色值只允许 #hex / rgb() / linear-gradient()）。
 */

/** 转义 HTML 文本节点里的全部特殊字符。用于不允许任何标签的字段。 */
export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 先全量转义，再仅放回 `<br>` / `<br/>` / `<br />`（大小写不限）。
 *
 * 用于既有内容依赖换行标签的字段：全部 46 个内置 premise card 共 86 处 `<br>`，
 * 全部集中在 note 字段，且未使用任何其他标签 —— 所以白名单只需 br。
 */
export function escapeHtmlAllowBr(input: string): string {
  return escapeHtml(input).replace(/&lt;br\s*\/?&gt;/gi, '<br>')
}
