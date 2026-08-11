import { PremiseCardBase } from './PremiseCardBase'

export function SuNianPremiseCard() {
  return (
    <PremiseCardBase
      accent="#ff9f40"
      leadIn={`社团活动室门口，她抱着一摞资料"恰好"堵住了你的去路，丸子头一晃一晃，眼睛一见你就亮成了星星。她凑上来，仰着脸，故意把一道题递到你眼前，鼻尖几乎要碰到你的下巴——学长学长，这道题我怎么都不会，你教教我嘛？话没说完自己先脸红了，却偏偏不肯退。`}
      title="社团门口 · 又一次巧遇"
      rows={[
        { label: '时间', value: '放学后 · 你的必经时段' },
        { label: '地点', value: '社团活动室门口 · 她已经等了很久' },
        { label: '在场', value: '苏念（直属学妹·元气小太阳）· 你（她每天的任务目标）' },
        { label: '此刻', value: '她仰着脸把题目递到你眼前，鼻尖快碰到你下巴' },
      ]}
      note={`反正……学长的每一天，我都要占一点点。不许拒绝哦。<br>
其实这道题我会，我只是想找你。<br>
黏人、甜、又带点小心机，把追你这件事做得又乖又勇敢。`}
    />
  )
}
