import { PremiseCardBase } from './PremiseCardBase'

export function JiYuPremiseCard() {
  return (
    <PremiseCardBase
      accent="#7A8C9B"
      leadIn="连续第七周的黄昏，你如约推开那扇咨询室的门。他今天，等了你很久。"
      title="咨询记录 · CASE NO. 0037"
      rows={[
        { label: '时间', value: '周四 傍晚 18:07（迟到七分钟）' },
        { label: '地点', value: '私人心理咨询室 · 只剩一盏落地灯' },
        { label: '在场', value: '季屿（个案）· 你（主治医生）' },
        { label: '状态', value: '高度戒备 · 对你却近乎依赖' },
      ]}
      note="个案对外缄默、对你敞开。医患界线正在他这里悄悄失效——而你清楚，越界的代价由你承担。"
    />
  )
}
