"""Opening prompt building blocks.

Two layers steer first-encounter generation:

1. STYLE_DIRECTIVES — per-greeting_style *tone* baseline (character-appropriate,
   stable). Deliberately no fixed locations: the concrete scene is generated
   from the character's own persona/backstory, not picked from a location pool.

2. Diversity axes (ENTRY_ANGLES / TIME_TONES / PACING) — abstract, randomly
   sampled per generation to break LLM mode-collapse (the "rain + coffee shop +
   have-we-met-before" attractor). They vary the *shape* of the scene, not its
   content, so the character still drives what actually happens.
"""

STYLE_DIRECTIVES: dict[str, dict[str, str]] = {
    "warm": {
        "tone": "温暖亲和。语气自然，带着关心，不刻意讨好。",
        "emotion_goal": "让对方感到被温柔对待、被注意到。",
    },
    "cool": {
        "tone": "克制疏离，言简意深。不多余寒暄，但每句话都有分量。",
        "emotion_goal": "让对方好奇他在想什么、想靠近却不敢。",
    },
    "playful": {
        "tone": "俏皮灵动，带着一点挑逗的趣味。自来熟但不轻浮。",
        "emotion_goal": "让对方忍不住笑、想继续聊下去。",
    },
    "reserved": {
        "tone": "内敛含蓄，沉默中有温度。表达婉转，动作多于言语。",
        "emotion_goal": "让对方感到一种不明说的在意、想解读他。",
    },
    "intense": {
        "tone": "浓烈直接，目光灼人。话不多但每句都让人心跳加速。",
        "emotion_goal": "让对方感到危险的吸引力、被锁定的感觉。",
    },
}

DEFAULT_STYLE = "warm"


# ── Diversity axes (sampled per generation to break mode-collapse) ──────
# Each axis is abstract: it steers the *shape* of the scene, never the
# concrete location or plot — those come from the character. Cartesian
# product across axes gives a large joint space, so repeats are rare.

ENTRY_ANGLES: list[str] = [
    "从一个具体动作切入，先让对方看到你在做什么，再开口。",
    "从一句话切入，第一行就是你说出口的话，之后才交代场景。",
    "从一件物品或细节切入——你手里的东西、眼前的某样物件。",
    "从一个声音或气味切入——被听到的、被闻到的某种感觉。",
    "从一个中断的瞬间切入——你正专注于某事，被对方的出现打断。",
    "从环境氛围切入，先铺开此刻的空间感，再让你入场。",
    "从一个不经意的对视切入——目光先相遇，话在后面。",
]

TIME_TONES: list[str] = [
    "清晨，光线初亮，一切刚开始。",
    "正午前后，明亮清醒的时段。",
    "黄昏时分，光线转暖、影子拉长。",
    "入夜，灯火与暗处交界。",
    "深夜，安静到能听见细微的声音。",
    "季节交替的某个不确定时刻，天气本身带着情绪。",
]

PACING: list[str] = [
    "节奏舒缓，留白多，动作与停顿本身在说话。",
    "节奏轻快，几个短句连缀，带着一点跳脱。",
    "先静后动——平静开场，某一刻情绪骤然拉近。",
    "克制到近乎沉默，只用最少的词和一个动作。",
    "有一点戏剧张力，像某件事正要发生。",
]
