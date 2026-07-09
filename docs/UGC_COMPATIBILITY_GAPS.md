# UGC 角色系统兼容性缺口分析

> 创建：2026-07-09 · 基于 C1–C5b 合并后的代码精读（非凭记忆）  
> 范围：用户通过 `POST /api/characters` 创建的 UGC 角色，与内置 rin/dorothy 的功能对比

---

## 1. 完全适配（行为与内置角色相同）

| 功能 | 代码位置 | 原因 |
|------|----------|------|
| 核心聊天 / identity 注入 | SS01 `AnchorInjector`、SS05 composer | SoulSpec 从 registry 读取（C3a 接通 DB→registry），完整注入 system prompt |
| 情绪 VAD 变化 | SS03 全链路 | 全程只用 `character_id` 作 key，无任何 rin/dorothy 分支 |
| 关系阶段推进 | SS04 `StagePhaseEngine` | 阈值从 SoulSpec `relational_template` 读取，由 spec_builder 填充 |
| 记忆写入 L1–L4 | SS02 写路径 | `(user_id, character_id)` 作 key，无硬编码 |
| 主动消息 persona/templates | SS06 proactive | C5a 写入 `character_content` 表，`get_proactive_persona/templates()` 走 overlay 缓存 |
| 早晚安仪式问候 | SS06 ritual | 同一 overlay 机制，UGC 有自己的问候语 |

---

## 2. 功能可用，质量降级（有 else 分支，但缺少角色口吻）

这类问题**不会 crash、不会返回错误**，但 UGC 角色的体验比内置角色粗糙。

### 2.1 SS04 冷战 / 和解 / 重聚覆盖层

**文件**：`backend/heart/ss04_relationship/cold_war.py:443`

```python
else:
    overlay = f"有未解决的冲突：{cause}\n"
    overlay += "表现：短句、冷淡、不主动延续话题。\n"
    overlay += "等待用户修复行为。"
```

**差距**：rin/dorothy 有角色专属口吻（"你们之间有一件事没解决……"），UGC 角色得到通用描述文字，不带人物风格。

**影响等级**：轻度降级。冷战机制功能正常，只是措辞平淡。

---

### 2.2 SS02 记忆遗忘感覆盖层

**文件**：`backend/heart/ss02_memory/forgetting_affect.py`

内置角色有专属遗忘口吻（rin：克制省略，dorothy：自我调侃）。UGC 角色走通用中文兜底。

**影响等级**：轻度降级。

---

## 3. 实质性退化（代码已确认，需修复）

### 3.1 SS02 记忆召回 voice 变换失效

**文件**：`backend/heart/ss02_memory/service.py:437–457`

```python
def _get_reconstructor(self, character_id: str):
    specs_dir = Path(__file__).parent.parent.parent.parent / "soul_specs"
    spec_file = specs_dir / character_id / "v1.0.0.yaml"
    if spec_file.exists():
        ...  # ✅ rin/dorothy 正常
    else:
        logger.warning("reconstructor_spec_not_found", character_id=character_id)
        self._reconstructor_cache[character_id] = None  # ❌ UGC 返回 None
```

**后果**：`reconstructor.reconstruct(sm)` → `AttributeError: 'NoneType'…reconstruct` → `except Exception` 捕获 → `_fallback_text(sm.memory)`（原始文本，无角色声音）。

**用户感知**：记忆可被召回，但措辞是中性通用语气，不带角色特色。

**修复方案**（已在 `fix/ugc-compatibility-gaps` 实施）：
1. 当文件不存在时，从 `get_soul_registry().get_soul(character_id)` 取 spec
2. 创建 `reconstruction_templates/_generic.yaml` 通用模板
3. `Reconstructor.__init__` 当角色专属模板不存在时 fall back 到 `_generic.yaml`

---

### 3.2 SS06 主动消息系统 prompt 用 character_id 而非 display_name

**文件**：`backend/heart/ss06_inner_state/proactive_message.py:508–515`

```python
@staticmethod
def _resolve_character_name(character_id: str, soul: Optional[SoulSpec]) -> str:
    names = {"rin": "凛", "dorothy": "桃乐丝"}
    return names.get(cid.lower(), cid)  # ❌ UGC 返回 "xiaoxue_abc123" 这样的 slug
```

**后果**：LLM system prompt 变成 `"你是xiaoxue_abc123。你要给一个对你很重要的人发一条消息。"` — 语义奇怪，LLM 可能生成异常文本。

**修复方案**：读取 `soul.display_name.zh`（SoulSpec 中已有该字段）。

---

### 3.3 SS06 主动消息无风格约束（空 style guide）

**文件**：`backend/heart/ss06_inner_state/proactive_message.py:462–481`

```python
guides = {"rin": "...", "dorothy": "..."}
return guides.get(cid.lower(), "")  # ❌ UGC 返回 ""
```

**后果**：LLM 生成主动消息时缺少风格指引（短句/克制/特定语气词），质量完全依赖用户写的 persona 描述。

**修复方案**：从 SoulSpec `voice_dna` 提取第一条 `speech_sample` 作为风格示例，拼装简单的风格说明。

---

### 3.4 SS05 Reroll fallback 返回单省略号

**文件**：`backend/heart/ss05_composer/reroll.py:353–358`

```python
char_lib = _FALLBACK_LIBRARY.get(character_id)
if char_lib is None:
    return "……"  # ❌ UGC 角色只有一个省略号
```

**后果**：当 LLM 输出触发 anti-pattern filter 需要 reroll fallback 时，UGC 角色返回孤零零的省略号，体验突兀。

**修复方案**：读取 SoulSpec `voice_dna` 中的 `speech_samples`，或生成简单的通用兜底语。

---

### 3.5 SS07 错误兜底用英文

**文件**：`backend/heart/ss07_orchestration/orchestrator.py:43`

```python
_DEFAULT_FALLBACK = "I heard what you said. Can you tell me more?"
```

**后果**：UGC 角色在 composer 熔断时返回英文，与整个中文 UGC 体验严重不符。

**修复方案**：改为中文通用兜底语，不引用任何角色名。

---

## 4. 功能缺口（未实现，非回归）

| 缺口 | 说明 | 优先级 |
|------|------|--------|
| UGC 角色头像上传 | `CreateCharacterPage` 无头像字段；展示用 `resolveCharacterProfile` 通用 fallback | P2 |
| 公开角色内容审核 | C5 MVP 显式排除；`visibility=public` 功能可用但无人工审核/举报流 | P2（上线前必须） |
| 集成测试 `test_characters_ugc.py` | C5a 规划文档列出但未实现 | P1 |
| 主导航入口 `/my-characters` | `MyCharactersPage` 存在但无入口导航，用户无法发现 | P1 |

---

## 5. 修复状态追踪

| # | 问题 | 分支 | 状态 |
|---|------|------|------|
| FIX-1 | SS06 display_name | `fix/ugc-compatibility-gaps` | ✅ 已修 |
| FIX-2 | SS06 style guide | `fix/ugc-compatibility-gaps` | ✅ 已修 |
| FIX-3 | SS02 reconstructor + generic template | `fix/ugc-compatibility-gaps` | ✅ 已修 |
| FIX-4 | SS05 reroll fallback | `fix/ugc-compatibility-gaps` | ✅ 已修 |
| FIX-5 | SS07 英文 fallback | `fix/ugc-compatibility-gaps` | ✅ 已修 |
| FIX-6 | 集成测试 | `fix/ugc-compatibility-gaps` | ✅ 已添加 |
| FIX-7 | 主导航入口 | `fix/ugc-compatibility-gaps` | ✅ 已修 |

---

## 6. 不作为（设计如此）

以下降级行为**不修复**，记录在案：

- SS04 冷战/和解 generic overlay：冷战功能正常，口吻个性化属锦上添花，后续可通过 character_content 扩展
- SS02 forgetting_affect generic overlay：同上

---

*最后更新：2026-07-09*
