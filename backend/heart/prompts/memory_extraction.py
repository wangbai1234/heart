"""
Memory Extraction Prompt Template - SS02 附录 A

Used by LLM Encoder Worker (阶段 2) to extract facts from conversation.

Author: 心屿团队
"""

MEMORY_EXTRACTION_PROMPT = """
你是一个记忆提取系统。从下面的对话中提取可记忆的信息。

【对话上下文】
最近 turns:
{recent_context}

当前 turn:
User: {user_text}
{character_id}: {assistant_text}

【提取任务】

提取以下信息（严格 JSON 格式）:

1. facts: 用户披露的具体事实（predicate-subject-object）
   - 仅提取明示信息，不推断
   - 必须引用原文（source_text）
   - confidence 严格反映把握度

2. emotion_peak: 本 turn 用户表达的情感峰值
3. importance_estimate: 本 turn 的重要性 [0, 1]
4. sacred_signals: 是否含"该被记住"信号
   - 用户明示 "记住这个"
   - 用户身份信息（姓名/生日/...）
   - 深度披露 (童年/创伤/失败/恋情)
   - 第一次事件
   - 承诺

【输出格式】
```json
{{
  "facts": [
    {{
      "predicate": "has_pet",
      "subject": "user",
      "object": "一只叫老铁的黑猫",
      "source_text": "我家那只叫老铁的猫……",
      "confidence": 0.95,
      "emotional_charge": 0.4,
      "emotional_label": "fond",
      "sacred_signal": false
    }}
  ],
  "emotion_peak": {{
    "valence": 0.3,
    "arousal": 0.4,
    "label": "calm"
  }},
  "importance_estimate": 0.5,
  "contains_sacred": false,
  "contains_promise": false,
  "contains_first_event": false
}}
```

【严格规则】
- 不提取推断信息
- confidence < 0.7 的 fact 不输出
- 同 predicate-subject 的重复信息不重复输出
- 不输出对话中没有的内容
- JSON 严格合法，无注释、无 trailing comma
"""
