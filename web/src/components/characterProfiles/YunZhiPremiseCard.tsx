import { PremiseCardBase } from './PremiseCardBase'

export function YunZhiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#A9C0DC"
      leadIn={`月下竹林，寒剑出鞘的轻鸣里，她一袭白衣自天际落下，衣袂扫过你面颊，带着清冽的雪气。
剑尖抵住你咽喉，她却微微一顿——剑锋一转收回鞘中，她抬手，指尖挑起你的下巴。
清冷的眸中，第一次映进一个凡人的影子。她俯身，气息清冷地贴近你的唇。`}
      title="月下 · 竹林"
      rows={[
        { label: '时间', value: '子夜 · 月圆之夜' },
        { label: '地点', value: '凡间竹林 · 月华如水' },
        { label: '在场', value: '云枝（无极剑派剑仙·御剑而行的清冷仙子）· 你（让她按下剑的凡人）' },
        { label: '此刻', value: '她指尖挑起你的下巴，清冷的目光里第一次映进一个人' },
      ]}
      note={`百年斩妖除魔，我的剑从未为谁停过。你倒是个例外。<br>
她清冷疏离，认准一个人便以命相护，绝不回头。<br>
「仙界万千楼阁，竟不及你这一眼。这一世，我不回天上了——你，我要定了。」`}
    />
  )
}
