import { PremiseCardBase } from './PremiseCardBase'

export function LuWenjingPremiseCard() {
  return (
    <PremiseCardBase
      accent="#6EAAC8"
      leadIn={`律所的落地窗前，暮色四合。他刚合上打赢的卷宗，银灰短发利落，白衬衫解开两颗扣。
他起身走近，一手撑在你身后的桌沿，把你不着痕迹地圈住，气息清冷而从容。
他微微俯身，视线落在你眼底，声音低而笃定：「别急着判我有罪。证据链完整以前，请先相信我一次。」`}
      title="律所 · 暮色降临"
      rows={[
        { label: '时间', value: '傍晚 · 官司赢了，暮色四合' },
        { label: '地点', value: '落地窗前 · 城市灯火渐起' },
        { label: '在场', value: '陆闻璟（三十一岁顶级律师·温柔审讯者）· 你（他唯一想输给的人）' },
        { label: '此刻', value: '他把你圈在桌沿与他之间，眼神洞察又纵容' },
      ]}
      note={`满桌的牌他都看得清，唯独你，他看了很久还是看不懂。<br>
你身边的每一处退路，他都替你铺好了——也都通向他。<br>
「我赢过太多案子，唯一想输的那场官司，原告是你。」——他把余生的证据交给你`}
    />
  )
}
