import { PremiseCardBase } from './PremiseCardBase'

export function ShiyanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#e6d3a6"
      leadIn="他是你从小到大的青梅竹马，别人眼里「本就是一对」，感情却一直暧昧未挑明。高中你被送去日本留学，两人没断联却谁都没先开口。毕业这个假期他突然飞来日本，陪你走完整段旅程——直到你们坐上富士山下的缆车，空荡的车厢里只有你们两个人。"
      title="富士山缆车 · 半山处"
      rows={[
        { label: '时间', value: '毕业假期 · 旅程的最后一站' },
        { label: '地点', value: '富士山下的缆车 · 雪顶正一寸寸逼近' },
        { label: '在场', value: '时衍（青梅竹马 · 系着一起挑的围巾）· 你' },
        { label: '此刻', value: '他忽然安静，蓝眼睛落在你脸上久久没移开' },
      ]}
      note="几天的朝夕相处把那点暧昧烘得发烫。<br>他扶住你手腕又像被烫到似的顿住，却没收回。<br>「你会回国读大学吗？」没等你答，他先垂下眼——<br>「如果你要留在日本，我可以申请早稻田。」<br>这一次，他不想再假装只是青梅竹马了。"
    />
  )
}
