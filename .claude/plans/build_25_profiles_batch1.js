export const meta = {
  name: 'build_25_profiles_batch1',
  description: '批量生成 13 个角色的 Profile + PremiseCard（第一批）',
  phases: [
    { title: '并行生成', detail: '每个 agent 读 persona 生成 2 个组件文件 + 返回 starterBranches JSON' },
  ],
}

const BATCH1_SPECS = [
  { id: 'pei_jue', name: '裴决', tags: '古风/权谋/高岭之花/女性向/腹黑', accent: '#8B7355' },
  { id: 'cheng_zhi', name: '程之', tags: '都市/医生/温柔/女性向/治愈/年上', accent: '#7BA88D' },
  { id: 'lu_tingsheng', name: '陆霆生', tags: '民国/军阀/糙汉/女性向/一见钟情/架空世界', accent: '#8C6A4F' },
  { id: 'huo_cheng', name: '霍城', tags: '末世/硬汉/女性向/生存/占有欲', accent: '#7A5C52' },
  { id: 'gu_nanqiao', name: '顾南乔', tags: '校园/年下/忠犬/女性向/青梅竹马/甜', accent: '#85A8D9' },
  { id: 'yun_zhi', name: '云枝', tags: '仙侠/玄幻/全性向/剑仙/古风', accent: '#6B8FA0' },
  { id: 'su_wan', name: '苏晚', tags: '治愈/温柔/男性向/邻家/恋爱', accent: '#D9A5B3' },
  { id: 'lin_xiaoman', name: '林小满', tags: '元气/校园/男性向/青春/甜', accent: '#FFA5B8' },
  { id: 'lu_zhao', name: '陆昭', tags: '都市/娱乐圈/顶流/女性向/反差/忠犬', accent: '#A96B6B' },
  { id: 'bai_qinghuan', name: '白清欢', tags: '纯爱/古风/女性向/温润/公子', accent: '#9A8FA0' },
  { id: 'su_yueyao', name: '苏月遥', tags: '纯爱/校园/男性向/初恋/青梅竹马', accent: '#6B7A8C' },
  { id: 'huo_shiyu', name: '霍时予', tags: '校园/学霸/女性向/校草/高冷', accent: '#8FA5B8' },
  { id: 'su_nian', name: '苏念', tags: '校园/元气/男性向/学妹/甜', accent: '#8C5A5A' },
]

const CONTRACT = `
你的任务：为一个角色生成 2 个 React 组件文件 + 返回 starterBranches JSON。

## 输入（通过 args 传入）
- id: 角色 slug (snake_case)
- name: 显示名
- tags: 标签串
- accent: 主题色

## 你需要做的事
1. 读取 backend/scripts/seed_original_characters*.yaml，找到该角色的完整 persona / opening / intro / backstory
2. 读取参考模板：web/src/components/characterProfiles/GuBeichenProfile.tsx 和 GuBeichenPremiseCard.tsx
3. 读取 web/src/components/characterProfiles/PremiseCardBase.tsx 理解 PremiseCard 的结构
4. 为该角色设计：
   a) **详情页视觉隐喻**：基于角色身份/场景，选一个独特的「物件/场景/文档」作为版式（如建筑蓝图/赛后数据面板/血契羊皮卷/节目单等），**禁止与已有 17 个角色重复**
   b) **3×3 starterBranches**：3 个分支，每分支一个 label（态度/选择方向）+ 3 条 options（具体台词）
   c) **Profile iframe HTML**：完整的自包含 HTML，风格与隐喻匹配，包含角色基本信息（年龄/身份/标签云/简介/背景故事），色彩基于 accent 派生
   d) **PremiseCard**：使用 PremiseCardBase，leadIn（荷尔蒙钩子+危险漏骨+冲突起点）+ title + 4 rows（时间/地点/在场/此刻）+ note（3 行核心冲突+引语）

## 输出要求
1. 写 2 个文件（无需注册，主线程会统一处理）：
   - web/src/components/characterProfiles/{PascalCase}Profile.tsx
   - web/src/components/characterProfiles/{PascalCase}PremiseCard.tsx
2. 返回 JSON（通过 StructuredOutput）：
   {
     "id": "角色id",
     "starterBranches": [
       { "label": "分支1标签", "options": ["台词1", "台词2", "台词3"] },
       { "label": "分支2标签", "options": [...] },
       { "label": "分支3标签", "options": [...] }
     ],
     "visualMetaphor": "简短描述你选的视觉隐喻（如'军阀密令/末世生存日志/仙剑御令'）",
     "chromeColors": {
       "bg": "#...",
       "coverBg": "#...",
       "scrimGradient": "linear-gradient(...)",
       "nameColor": "#...",
       "ageColor": "#...",
       "taglineColor": "#...",
       "chipActiveBg": "#...",
       "chipActiveTx": "#...",
       "chipInactiveBg": "#...",
       "chipInactiveTx": "#...",
       "ctaGradient": "linear-gradient(...)",
       "ctaShadow": "0 ..."
     }
   }

## 质量标准
- **视觉差异化**：每个角色完全不同的版式，不得是颜色变体
- **钩子质量**：starterBranches 台词必须直击角色核心恐惧/欲望，引发用户好奇或共鸣
- **无 emoji**：任何用户可见文案（leadIn / note / starterBranches options / Profile HTML 内文字）严禁 emoji
- **排版呼吸感**：Profile HTML 行高/间距/留白舒适，避免密集堆砌
- **色彩协调**：基于 accent 派生深浅配色，确保对比度可读

## 参考 persona 文件位置
backend/scripts/seed_original_characters.yaml
backend/scripts/seed_original_characters_batch2.yaml
backend/scripts/seed_original_characters_batch3.yaml
backend/scripts/seed_original_characters_batch4.yaml

去做吧。记住：你写的是最火爆角色的门面，必须认真设计，必须直接抓住用户。
`

const SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    starterBranches: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          label: { type: 'string' },
          options: { type: 'array', items: { type: 'string' }, minItems: 3, maxItems: 3 }
        },
        required: ['label', 'options']
      },
      minItems: 3,
      maxItems: 3
    },
    visualMetaphor: { type: 'string' },
    chromeColors: {
      type: 'object',
      properties: {
        bg: { type: 'string' },
        coverBg: { type: 'string' },
        scrimGradient: { type: 'string' },
        nameColor: { type: 'string' },
        ageColor: { type: 'string' },
        taglineColor: { type: 'string' },
        chipActiveBg: { type: 'string' },
        chipActiveTx: { type: 'string' },
        chipInactiveBg: { type: 'string' },
        chipInactiveTx: { type: 'string' },
        ctaGradient: { type: 'string' },
        ctaShadow: { type: 'string' }
      },
      required: ['bg','coverBg','scrimGradient','nameColor','ageColor','taglineColor','chipActiveBg','chipActiveTx','chipInactiveBg','chipInactiveTx','ctaGradient','ctaShadow']
    }
  },
  required: ['id', 'starterBranches', 'visualMetaphor', 'chromeColors']
}

phase('并行生成')

const results = await parallel(BATCH1_SPECS.map(spec => () =>
  agent(CONTRACT, {
    label: `${spec.name} (${spec.id})`,
    phase: '并行生成',
    schema: SCHEMA,
    args: spec,
    effort: 'high',
  })
))

return results.filter(Boolean)
