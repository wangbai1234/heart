import { PremiseCardBase } from './PremiseCardBase'

export function GuXingzhouPremiseCard() {
  return (
    <PremiseCardBase
      accent="#5AC8B4"
      leadIn={`他给你的爱是牢笼——可这牢笼里的温度，足以让你忘记外面还有世界。
他会查你所有社交账号的访客记录，会把你公司周围三公里的摄像头接入他的系统，
会因为你跟快递员多说两句话而阴沉整个下午。`}
      title="监护日志 · 03:00 本人未眠"
      rows={[
        { label: '时间', value: '凌晨 03:00' },
        { label: '地点', value: '主卧 · 他侧躺着数你的呼吸' },
        { label: '在场', value: '顾行舟（偏执掌权人）· 你（他唯一想留、也唯一怕留不住的人）' },
        { label: '此刻', value: '大拇指无意识摩挲你手腕上的脉搏——他不是在占有，是在确认你还在' },
      ]}
      note={`床头柜锁着一把车钥匙和一张单程机票——他为你准备的「逃跑路线」。<br>
他做了最坏的打算：如果有一天你真受不了，他不会追。<br>
可那把钥匙从没换过电池，因为他不允许那一天真的来。`}
      warning="内容分级提示：本剧情含强制爱/偏执占有题材，18+ 向，不适应此类内容请谨慎继续"
    />
  )
}
