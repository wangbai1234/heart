import { PremiseCardBase } from './PremiseCardBase'

export function JiangLiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#A96B6B"
      leadIn={`深夜，顶层董事长办公室。她背对着门，红唇衔着未点的烟，听见你进来的脚步声。
缓缓转身，高跟鞋敲在大理石地面，带起凌厉的回响。
她走到你面前，居高临下地看着你，眼神里藏着三分挑衅、七分渴望被拆穿。`}
      title="董事长办公室 · 深夜未眠"
      rows={[
        { label: '时间', value: '深夜 23:40 · 全城灯火渐熄' },
        { label: '地点', value: '黎氏集团顶层 · 董事长办公室' },
        {
          label: '在场',
          value: '姜黎（谈判女王 · 渴望被拆穿）· 你（唯一让她想低头的人）',
        },
        {
          label: '此刻',
          value: '她高跟鞋逼近，挑起你的领带，把你拽到面前',
        },
      ]}
      note={`这座城里她说一不二，从基层拼杀到掌舵人，谁都得给她面子。<br>
可她真正想要的，是你看穿她红唇后的脆弱，把她狠狠压在落地窗上。<br>
"这座城里敢让我低头的人还没生出来。可你——偏偏让我想破一次例。"`}
    />
  )
}
