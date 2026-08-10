import { PremiseCardBase } from './PremiseCardBase'

export function QinXiaoPremiseCard() {
  return (
    <PremiseCardBase
      accent="#D98A4A"
      leadIn={`地下酒吧的暗红灯光里，他半靠在卡座上，烟没点，满背纹身从敞开的衣领透出一角。
见你一个人闯进这种地方，他长腿一伸，直接把你圈进两膝之间，手指扣住你的腰不让你退。
这条街上没人敢惹他——可他护你时，比谁都认真。`}
      title="夜色手记 · 02:14"
      rows={[
        { label: '时间', value: '凌晨 02:14' },
        { label: '地点', value: '地下酒吧 · 最深处的卡座' },
        { label: '在场', value: '秦骁（夜色之主·野性难驯）· 你（他唯一肯破例的人）' },
        { label: '此刻', value: '拇指抵着你的下唇缓缓碾过，眼神危险又餍足' },
      ]}
      note={`「这种地方，一个人乱跑？被人叼走了怎么办。」<br>
他信奉自己的规矩，唯独碰到你可以破例——也可以破例护你。<br>
「今晚就拴在我身边——乖乖的，我疼你；想跑，我可不是什么好脾气。」`}
      warning="内容分级提示：本剧情含黑道/占有题材与暧昧张力，18+ 向，不适应请谨慎继续"
    />
  )
}
