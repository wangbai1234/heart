import { PremiseCardBase } from './PremiseCardBase'

export function ShenYuchuanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#5B8FA3"
      leadIn={`训练室是他的王座，镜头前零下十度让全队都怕。可你敢在凌晨刚下播的时候溜进去，
他就会把耳机一摘，把你往腿边一勾——那道冰冷侧脸瞬间化成一滩甜，蹭你肩膀像只大狗。
今晚直播间他说完「我先走了」，转头就扣住了你的手腕。`}
      title="训练室 · 03:00 刚下播"
      rows={[
        { label: '时间', value: '凌晨 03:00 · 全队熄灯他独醒' },
        { label: '地点', value: '训练室蓝光 · 战队基地顶层' },
        { label: '在场', value: '沈屿川（场上人形灭火器·场下黏人大狗）· 你（他唯一卸下冰面的人）' },
        { label: '此刻', value: '他扣住你手腕 鼻尖抵着你下颌 耳朵悄悄红了' },
      ]}
      note={`队友失误时那道侧脸能让全队噤声，可他摘下耳机就往你身边蹭——「再陪我一局，就一局」。<br>
半年偷偷接三个代言省下机票钱，夺冠采访只说「想谢一个人，但不告诉你们」。<br>
「今晚我要听着你的心跳睡。」`}
    />
  )
}
