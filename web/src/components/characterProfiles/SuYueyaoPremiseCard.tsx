import { PremiseCardBase } from './PremiseCardBase'

export function SuYueyaoPremiseCard() {
  return (
    <PremiseCardBase
      accent="#e87a66"
      leadIn={`夏夜的校园长廊，花灯初上。她抱着一本书站在你必经的路口，宽檐白帽下的脸红扑扑的，看见你就慌忙低下头。她鼓起勇气把一张叠得整整齐齐的纸条塞进你手里，指尖凉凉的，微微发抖。这是她从高中就想给你的——里面写满了三年的心事。`}
      title="长廊花灯 · 初夏"
      rows={[
        { label: '时间', value: '初夏傍晚 · 花灯初上' },
        { label: '地点', value: '校园长廊 · 你必经之路' },
        { label: '在场', value: '苏月遥（大学同班 · 抱着书的少女）· 你（她等了很久的人）' },
        { label: '此刻', value: '她把叠好的纸条塞进你手里，睫毛颤得像蝶翼' },
      ]}
      note={`我喜欢你……很久很久了。这次上了同一所大学，我不想再只是偷偷看着你了。<br>
你回头的那一刻，我把「喜欢」偷偷说了一百遍。<br>
这是最纯粹的初恋模样：没有套路，只有一颗砰砰跳的心。`}
    />
  )
}
