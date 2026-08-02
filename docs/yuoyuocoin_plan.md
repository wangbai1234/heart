yuoyuo 商业化体系设计方案 V1.0
目标：
你需要基于当前 yuoyuo 项目的实际代码架构，规划新前后端页面设计规划文档，并提供相应的prompt，前端我交给gpt执行，后端交给sonnet执行。
在不破坏现有 AI 陪伴核心功能的情况下，引入：

1. 会员订阅体系
2. yuoyuo币体系
3. AI能力消耗计费体系
4. 爱发电支付闭环
5. Grok / Claude / 多模型扩展能力

一、核心设计理念

yuoyuo 采用：

免费体验 + 会员解锁高级模型 + yuoyuo币消耗体系

目标：

免费用户可以长期使用，培养陪伴关系
会员用户获得更高质量 AI 陪伴体验
yuoyuo币作为高级能力消耗单位
避免高级模型无限调用导致成本失控

二、用户等级体系
1. 普通用户（免费）

名称：

体验用户

权益：

✓ DeepSeek 无限文字聊天

✓ MiMo TTS语音

✓ 永久记忆功能

✓ 新用户赠送100 yuoyuo币

❌不支持自建角色克隆音色
2. 进阶版

价格：

¥39 / 月

定位：

更聪明的yuoyuo，更自然的陪伴

权益：

✓ DeepSeek 无限聊天

✓ 解锁 Grok 高级聊天模型

✓ Fish Audio TTS语音

✓ 每月赠送400 yuoyuo币

✓ 高级模型优先调用

✓ 永久记忆功能

✓ 自建角色clone音色功能
3. 沉浸版

价格：

¥79 / 月

定位：

接近真人的深度陪伴体验

权益：

✓ DeepSeek 无限聊天

✓ 解锁 Claude 高级聊天模型

✓ Fish Audio TTS语音

✓ 每月赠送800 yuoyuo币

✓ 高级模型优先调用

✓ 永久记忆功能

✓ 自建角色clone音色功能
三、yuoyuo币规则
基础兑换比例

用户购买：

1元 = 10 yuoyuo币

套餐一：

¥39会员

赠送400 yuoyuo币

约等于40元体验额度

四、模型调用消耗设计
1. DeepSeek

成本：

接近0

策略：

免费无限使用

不消耗yuoyuo币

作用：

降低用户流失。

2. Grok模型

成本：

一次调用 ≈ 0.012元

实际售价换算：

如果：

1元=10币

成本：

0.012元 ≈ 0.12币

考虑利润和波动：

建议：

Grok聊天
3 yuoyuo币 / 次

利润空间：

足够。

3. Claude模型

你的成本：

一次调用 ≈ 0.8元

成本换算：

8币

建议：

Claude聊天
12 yuoyuo币 / 次

原因：

Claude成本高，需要保护。

4. MiMo TTS

你的成本：

差不多免费，当前估算低。

普通语音：

5 yuoyuo币 / 次
5. Fish Audio TTS

成本：

一次生成 ≈0.3元

换算：

3币成本

建议：

8 yuoyuo币 / 次
6. Fish Audio声音克隆

成本：

一次 ≈5元

换算：

50币成本

建议：

100 yuoyuo币 / 次

原因：

声音克隆属于高价值功能。



五、yuoyuo币购买商城
☕ 小份补给

价格：

¥6

获得：

60 yuoyuo币

适合：

偶尔使用。

🌙 陪伴补给

价格：

¥18

获得：

220 yuoyuo币

赠送：

20币。

⭐ 深度补给

价格：

¥48

获得：

650 yuoyuo币

赠送：

170币。

🌌 长期陪伴

价格：

¥128

获得：

2000 yuoyuo币

赠送：

720币。

六、邀请奖励体系

目标：

拉新，而不是刷积分。

新用户

注册：

赠送100 yuoyuo币
邀请奖励

有效邀请：

条件：

好友注册

+
完成首次聊天

奖励：

邀请人：

100 yuoyuo币

新人：

100 yuoyuo币
阶段奖励

邀请5人：

额外300 yuoyuo币

邀请10人：

额外1000 yuoyuo币
七、异常降级策略
LLM异常

优先级：

Claude

↓

Grok

↓

DeepSeek

如果高级模型失败：

调用：

DeepSeek回复


不要展示技术错误。

TTS异常

流程：

文本生成成功

↓

TTS生成

↓

失败

↓

直接返回LLM生成的文本内容

八、需要修改功能的页面
自建角色第三步页面的预制音色，现在的功能是根据男女性别分别提供三个minimax预制音色。现在功能修改为：根据男女性别分别提供五个不同风格的mimo预制音色，并且提供两种克隆音色：mimo的clone功能和fish audio的clone功能，注意fish audio普通用户要置灰并提示：升级会员可使用。
九、配置和要求
1.所有支付体系暂时使用爱发电实现
2.grok调用路径：openai：/v1/chat/completions   
3.claude调用路径：anthropic：/v1/messages  openai：/v1/chat/completions  
4.启动mimoTTS的导演模式，将minimax作为最后的兜底方案。mimo TTS文档地址：https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/audio/speech-synthesis-v2.5。 
5.fish audio的API文档：实时文字转语音：https://docs.fishaudio.org/zh/docs/api-reference/text-to-speech/realtime
声音克隆文档：https://docs.fishaudio.org/zh/docs/api-reference/voices/create
音色管理文档：https://docs.fishaudio.org/zh/docs/api-reference/voices
配音模型文档：https://docs.fishaudio.org/zh/docs/api-reference/text-to-speech/models
其他重要文档自行查看。