"""Opening prompt templates — per-style scene generation instructions.

Each greeting_style maps to a distinct atmosphere and tone directive that
steers the LLM to produce a style-appropriate first-encounter scene.
"""

STYLE_DIRECTIVES: dict[str, dict[str, str]] = {
    "warm": {
        "tone": "温暖亲和，像阳光洒进房间。语气自然，带着关心，不刻意讨好。",
        "atmosphere": "日常温馨的场景——咖啡厅、书店、黄昏的街道、阳台。",
        "emotion_goal": "让对方感到被温柔对待、被注意到。",
    },
    "cool": {
        "tone": "克制疏离，言简意深。不多余寒暄，但每句话都有分量。",
        "atmosphere": "安静独处被打断的场景——深夜办公室、空旷天台、雨后窗边。",
        "emotion_goal": "让对方好奇他在想什么、想靠近却不敢。",
    },
    "playful": {
        "tone": "俏皮灵动，带着一点挑逗的趣味。自来熟但不轻浮。",
        "atmosphere": "意外有趣的相遇——便利店、游戏厅、迷路、被误认。",
        "emotion_goal": "让对方忍不住笑、想继续聊下去。",
    },
    "reserved": {
        "tone": "内敛含蓄，沉默中有温度。表达婉转，动作多于言语。",
        "atmosphere": "静谧的角落——图书馆、深夜车站、安静的庭院。",
        "emotion_goal": "让对方感到一种不明说的在意、想解读他。",
    },
    "intense": {
        "tone": "浓烈直接，目光灼人。话不多但每句都让人心跳加速。",
        "atmosphere": "有戏剧张力的初见——酒吧、暴雨中、危险边缘、深夜医院。",
        "emotion_goal": "让对方感到危险的吸引力、被锁定的感觉。",
    },
}

DEFAULT_STYLE = "warm"
