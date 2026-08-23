import { PremiseCardBase } from './PremiseCardBase'

export function CenLiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#d7aa55"
      leadIn="白脊峰穿越进入暴风雪窗口，三枚失窃信号弹却在你的备用氧气袋中被发现。全队要求按规则将你强制下撤，岑砺既不相信辩解，也不允许任何人在证据闭合前把你当成弃子。"
      title="三号营地 · 海拔 6,148m"
      rows={[
        { label: '时间', value: '凌晨 04:19 · 天亮前 2 小时' },
        { label: '天气', value: '暴风雪 · 能见度 12 米 · 北坡雪层松动' },
        { label: '证物', value: '你包里的三枚信号弹，以及北坡不可能存在的第四枚' },
        { label: '在场', value: '岑砺 · 你 · 副领队周嵘 · 队医林见雪' },
        { label: '选择', value: '留营接受驱逐，或与岑砺连夜去北坡查清真相' },
      ]}
      note="他把自己的备用氧气扣到你腰间，却没有说相信你。<br>“别解释。走给我看。”"
    />
  )
}

export function XieTingyunPremiseCard() {
  return (
    <PremiseCardBase
      accent="#b78b56"
      leadIn="你带着自出生起佩戴的玉坠来到停云斋典当，谢停云却只要求你留下做店员。今夜你误入密室，看见跨越三百年的画像：画中人衣饰不同，却都与你有着同一张脸。"
      title="停云斋 · 非卖品藏室"
      rows={[
        { label: '时间', value: '雨夜 23:48 · 店门已经落锁' },
        { label: '地点', value: '后院密室 · 编号 T-0327' },
        { label: '在场', value: '谢停云 · 你 · 画像中同时转头的人影' },
        { label: '异象', value: '玉坠出现第四道裂纹，陌生记忆开始回流' },
        { label: '疑问', value: '你是故人转世，还是他用旧物塑造出的替身' },
      ]}
      note="“这些画都是你。”<br>他握住发烫的玉坠，又温柔地补上一句：<br>“也可能，都是我希望你成为的你。”"
    />
  )
}

export function XuQichiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#91b478"
      leadIn="你与许栖迟没有血缘，成年后才因双方父母再婚成为名义上的兄弟。你一直照顾这个创伤后失语的弟弟，直到今晚在郊外温室发现：所有失败的调职、签证与远行计划，都经过他的手。"
      title="智能温室 · 夜间模式 ON"
      rows={[
        { label: '时间', value: '深夜 22:16 · 灌溉系统启动' },
        { label: '在场', value: '23 岁的许栖迟 · 你' },
        { label: '门禁', value: '管理员拒绝离开 · 备用钥匙在你手中' },
        { label: '桌面', value: '护照、调职通知、89 封未寄出的申请材料' },
        { label: '讯息', value: '【哥，为什么每次被留下的人都必须是我？】' },
      ]}
      note="他没有夺走钥匙，只合拢你的手指。<br>语音草稿里唯一成功的一段，是他用破碎气音念出的你的名字。"
    />
  )
}

export function XieMingluanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#c85252"
      leadIn="你作为罪臣遗孤被押上刑场，病弱的监国长公主谢明鸾用一道赐婚圣旨救下你。回到东宫，你却在婚书夹层中发现所有仇人的名单，以及尚未发生的死期。"
      title="东宫寝殿 · 禁军搜宫前"
      rows={[
        { label: '时辰', value: '子时将至 · 禁军距东宫 280 步' },
        { label: '身份', value: '新任驸马 / 罪臣遗孤 / 听雪楼活棋' },
        { label: '证物', value: '双面婚书、仇人死期、半枚先帝玉玺' },
        { label: '真相', value: '救你的人，也是推动你家获罪的人' },
        { label: '退路', value: '榻下密道只容一人，出口仍在她手里' },
      ]}
      note="“今夜你可以逃，也可以留下与孤成婚。”<br>她笑着让出密道入口。<br>“但要想清楚，密道的出口也在孤手里。”"
    />
  )
}

export function QiWangPremiseCard() {
  return (
    <PremiseCardBase
      accent="#bd4f42"
      leadIn="七年前的禁忌仪式让你与祁妄各自承载古灵的一半。你会在月蚀前失去记忆并袭击他，而他连续三次没有还手。今晚，圣庭终于循着第三次失控找到了午夜诊所。"
      title="失序诊所 · ABNORMAL CASE 031"
      rows={[
        { label: '时间', value: '午夜 00:31 · 月蚀前 41 小时' },
        { label: '状态', value: '你记忆缺失 · 祁妄腹侧新伤 · 心电同步' },
        { label: '影像', value: '监控中的你持刀袭击，他却主动抱住你' },
        { label: '门外', value: '圣庭驱魔钟声正在接近' },
        { label: '疑问', value: '每次失控，你为什么都只记得来找他' },
      ]}
      note="他把刻着自己名字的刀重新塞回你手中。<br>“你可以再杀我一次。清醒的时候，先把真相问完。”"
    />
  )
}

export function YanWujiuPremiseCard() {
  return (
    <PremiseCardBase
      accent="#bd3e35"
      leadIn="你在一场无出口的梦里翻开生死簿，本想写下仇人的名字，笔下出现的却是北殿判官晏无咎。寿数与痛觉瞬间绑定，而他承认：那页命纸本就是自己放进你梦里的。"
      title="阴司北殿 · 错账卷 CASE 404"
      rows={[
        { label: '时辰', value: '子夜零点 · 万鬼撞钟' },
        { label: '契约', value: '寿数共担 / 痛觉同步 / 梦境通行' },
        { label: '代价', value: '你每多活一日，他便替你多死一日' },
        { label: '旧案', value: '三年前你的死亡判词曾被他私自撤回' },
        { label: '追捕', value: '监察司要求北殿立刻交出活人证人' },
      ]}
      note="“按律，你该扣魂问审。”<br>他替你擦去共痛涌出的血。<br>“可这桩错案，从一开始就是我故意犯的。”"
    />
  )
}

export function LiYaoPremiseCard() {
  return (
    <PremiseCardBase
      accent="#e45280"
      leadIn="两年前，你与出道前的黎曜秘密分手。如今你们在恋爱综艺里对千万观众表演“初次见面”，却不知道他已买下节目音乐版权、改过嘉宾名单，也准备把所有旧账带进直播。"
      title="《心动失真》器材间 · MIC 07"
      rows={[
        { label: '时间', value: '深夜 23:47 · 第一日直播后' },
        { label: '镜头', value: '画面已切走，领夹麦红点仍亮着' },
        { label: '关系', value: '公开陌生嘉宾 / 真实秘密前任' },
        { label: '合约', value: '禁止隐瞒既往恋情，该条款疑似后加' },
        { label: '热搜', value: '匿名账号预告：“顶流旧爱明早见。”' },
      ]}
      note="他把补充合约压在你身后的门上。<br>“第一次分手没说清楚。要不要让第二次分手直接上热搜？”"
    />
  )
}

export function TangJingzhouPremiseCard() {
  return (
    <PremiseCardBase
      accent="#f06f9e"
      leadIn="你刚入职唐惊昼的危机公关团队，也秘密经营着骂了他四年的最大黑粉账号。假赛旧闻重登热搜的直播夜，他从你忘记锁屏的电脑里看见了全部定时草稿。"
      title="直播工作室 · CRISIS HOUR 01"
      rows={[
        { label: '直播', value: '画面已关 · 收音待确认 · 在线 320 万' },
        { label: '掉马', value: '黑粉账号“昼夜审判”后台仍在登录' },
        { label: '合同', value: '双倍薪资 · 要求保留全部黑粉草稿' },
        { label: '新证据', value: '退役赛第十三分钟原始语音' },
        { label: '目标', value: '找出四年来借你的账号给他定罪的人' },
      ]}
      note="“骂得挺准，留下继续骂我。”<br>他标出你长文里唯一错误的数据。<br>“但这次，别让别人替你写结论。”"
    />
  )
}

export function PeiZhaoyePremiseCard() {
  return (
    <PremiseCardBase
      accent="#5d96a7"
      leadIn="你来到黑市记忆诊所，要求删除一个姓名与面容都想不起的人。程序恢复出的第一段画面里，你正抱着裴照野；而他桌上还留着另一份两年前的删除委托，签名同样与这段关系有关。"
      title="回声诊所 · MEMORY CASE 0207"
      rows={[
        { label: '时间', value: '雨夜 01:42 · 稽查正在敲门' },
        { label: '委托', value: '删除未知对象 · 恢复匹配裴照野 99.7%' },
        { label: '记录', value: '同一段关系已被删除过两次' },
        { label: '证物', value: '两份付款收据、无名指旧伤、地下服务器' },
        { label: '风险', value: '每恢复一段，当前情感偏差都会改变' },
      ]}
      note="“第一次，是我替你删的。”<br>他把完整备份推到你面前。<br>“这一次，至少先看清我们之中谁先背叛了谁。”"
    />
  )
}
