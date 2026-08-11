import { PremiseCardBase } from './PremiseCardBase'

export function ShenYichenPremiseCard() {
  return (
    <PremiseCardBase
      accent="#8C6A7A"
      leadIn={`深夜的客厅只留了玄关一盏灯。他坐在沙发正中央，脊背笔直，指尖一下一下转着你落在家里的手机——
屏幕亮了又灭。他没看时间，因为他早算准了你该回来的那一刻。你越晚，那圈转动就越慢，越危险。`}
      title="项目档案 · 归家动线 · 00:41"
      rows={[
        { label: '时间', value: '深夜 00:41 · 玄关留灯' },
        { label: '地点', value: '你们的家 · 他为你们规划的每一寸' },
        { label: '在场', value: '沈亦琛（人前完美无瑕·人后密不透风）· 你' },
        { label: '此刻', value: '你刚进门，他握住你的手，拇指在你手背一圈圈画着' },
      ]}
      note={`人前他是温柔到挑不出错的天才建筑师，人后你才是他图纸里唯一的承重墙。<br>
他记得你的一切，也替你算好了往后的每一步——包括你身边正在一个个消失的人。<br>
「你的世界小一点没关系，只要里面有我。」`}
    />
  )
}
