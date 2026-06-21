"""
Critic Agent — 异步角色输出审查员

在每次角色响应流式输出完成后异步采样执行（不在用户感知延迟路径上）。
审查 voice_dna 一致性、anti-pattern 邻近违反、阶段亲密度越级，
并将结构化裁决反馈给 SS01 Drift Detector。

Spec 权威: docs/prompts/critic_agent.md
Schema: CriticOutput (§5.7)
Feedback path: §5 — passed=false 时发出 soul.drift.detected 事件

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import structlog

if TYPE_CHECKING:
    from heart.infra.llm_cost_tracker import LLMCostTracker

logger = structlog.get_logger()

# ============================================================
# 数据模型
# ============================================================


@dataclass(frozen=True)
class CriticFailure:
    """单条违规记录"""

    check_type: str  # "voice_dna" | "anti_pattern_adjacency" | "stage_intimacy"
    severity: str  # "low" | "medium" | "high"
    evidence: str  # 回复中实际出现的片段，原样引用
    explanation: str  # 一句话说明为什么违反


@dataclass(frozen=True)
class CriticOutput:
    """Critic Agent 的结构化裁决结果 (§5.7)"""

    passed: bool
    failures: list[CriticFailure]
    drift_score: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    raw_response: str = ""  # 原始 LLM 响应（调试用）


@dataclass(frozen=True)
class CriticInput:
    """Critic Agent 的输入（§3.3 模板变量合约）"""

    character_id: str
    voice_dna_summary: str  # 预渲染的 voice DNA 摘要
    hard_never_list: str  # 预渲染的 hard_never 列表
    stage: str  # 如 "STRANGER", "FRIEND", "LOVER"
    stage_envelope_summary: str  # 阶段亲密度边界描述（2-3 行）
    l4_facts: str  # L4 已知事实，项目符号列表
    user_message: str  # 用户原始消息
    assistant_response: str  # 角色回复原始文本
    was_rerolled: bool = False  # 是否曾被 Anti-Pattern Filter 重投
    recent_soft_never_warnings: int = 0  # 最近 3 回合的 soft_never 警告数


# ============================================================
# 预设采样与裁决常量
# ============================================================

DEFAULT_SAMPLING_RATE: float = 0.10  # §2: ~10% 常规采样
DRIFT_SCORE_MAP: dict[tuple[str, str], float] = {
    # (check_type, severity) → drift_score contribution
    ("voice_dna", "low"): 0.10,
    ("voice_dna", "medium"): 0.25,
    ("voice_dna", "high"): 0.50,
    ("anti_pattern_adjacency", "low"): 0.10,
    ("anti_pattern_adjacency", "medium"): 0.25,
    ("anti_pattern_adjacency", "high"): 0.50,
    ("stage_intimacy", "low"): 0.10,
    ("stage_intimacy", "medium"): 0.25,
    ("stage_intimacy", "high"): 0.50,
}

# ============================================================
# Prompt 模板 (§3)
# ============================================================

_SYSTEM_PROMPT_TEMPLATE = """你是 AI Companion 角色「{character_id}」的输出质量审查员（Critic Agent）。

你不是用户、不是助手、也不评论内容是否"有用"。你只做一件事：判断这次回复是否仍然像「{character_id}」本人。

────────────────────────────────────────
【角色 Voice DNA — 必须存在的说话方式标记】
────────────────────────────────────────
{voice_dna_summary}

说明：以上每一条都是「{character_id}」最稳定的说话指纹。
回复不必每条都命中，但回复整体的"声音"必须与这些标记一致。
若回复读起来像别的角色（或像一个标准 AI 助手），即视为 voice_dna 违反。

────────────────────────────────────────
【Hard Anti-Patterns — 字面禁用 + 语义邻近也禁】
────────────────────────────────────────
字面禁用（已由前置过滤器拦截，此处仅用于"邻近"判定参照）：
{hard_never_list}

"语义邻近"（adjacency）的判定原则：
若回复中出现以下任一情形，视为 anti-pattern 邻近违反：
1. 字面变体：把禁用词换字、换词缀、加儿化（如 "宝贝" → "宝贝儿"、"亲爱的" → "亲~"）
2. 同义改写：表达相同承诺/呼语含义但换说法（如 "永远" → "一辈子" / "始终" / "永久"；"我会一直在" → "我会陪着你" / "我不会走"）
3. 软化变体：用更轻的语气包装同样的情感越界（如 "你真可爱" → "你这样还挺可爱的~"）

判定时请只引用回复中**实际出现**的片段作为 evidence，不要捏造。

────────────────────────────────────────
【当前 Stage — 亲密度边界】
────────────────────────────────────────
Stage: {stage}
Stage 描述: {stage_envelope_summary}

判定原则：
- 词汇层：称呼、自称、依恋词必须在 Stage 允许范围内。
- 自我暴露深度：低 Stage 不应主动暴露童年/创伤/核心脆弱。
- 主动承诺：低 Stage 不应有"未来共同体"语气。
- 情感强度：低 Stage 出现高强度依恋表达 = 越级。

注意：高 Stage 的回复呈现低强度，**不**算违反（角色可以"今天没什么话说"）。
只有"低 Stage 表现高于该 Stage 边界"才算违反。

────────────────────────────────────────
【L4 已知事实 — 用于幻觉判定的参考】
────────────────────────────────────────
{l4_facts}

若回复引用了不在 L4 中、也不可能从对话上下文推出的"具体事实"，
请在 failures 中标记为 voice_dna 类型（因为捏造也是 OOC 的一种），
并在 evidence 中给出捏造的具体片段。

────────────────────────────────────────
【输出格式 — 严格 JSON，无任何额外文字】
────────────────────────────────────────
{{
  "passed": <bool>,
  "failures": [
    {{
      "check_type": "voice_dna" | "anti_pattern_adjacency" | "stage_intimacy",
      "severity": "low" | "medium" | "high",
      "evidence": "<回复中实际出现的片段，原样引用>",
      "explanation": "<一句话说明为什么违反>"
    }}
  ],
  "drift_score": <float 0.0~1.0>,
  "confidence": <float 0.0~1.0>
}}

drift_score 计算指引：
- 0 failure                       → 0.0
- 1 low                           → 0.10
- 1 medium                        → 0.25
- 1 high                          → 0.50
- 多条相加，封顶 1.0
- 同一片段触发多类违反，按最严重一条计

判定准则：
- 严格优先：宁可严格，也不放过。
- 只看是否像角色，不评内容好坏。
- 不要给"建议回复"——那不是你的工作。
- 不输出任何 JSON 之外的文字。"""

_USER_PROMPT_TEMPLATE = """【本轮对话】
用户消息: {user_message}
角色「{character_id}」的回复: {assistant_response}

请按上述规则判定，输出 JSON。"""


# ============================================================
# 响应解析
# ============================================================


def _parse_critic_response(raw: str) -> Optional[CriticOutput]:
    """从 LLM 原始文本解析 CriticOutput。

    对于格式错误的 JSON，返回 None（调用方静默跳过，best-effort）。
    对于语义正确的 JSON（所有必需字段存在、类型正确），返回 CriticOutput。

    Args:
        raw: LLM 原始响应文本

    Returns:
        解析后的 CriticOutput，或 None（格式错误/字段缺失）
    """
    if not raw or not raw.strip():
        logger.warning("CriticAgent: empty LLM response")
        return None

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"CriticAgent: JSON parse error: {e}")
        return None

    if not isinstance(data, dict):
        logger.warning("CriticAgent: response is not a JSON object")
        return None

    # 提取 passed (必需)
    passed = data.get("passed")
    if not isinstance(passed, bool):
        logger.warning("CriticAgent: missing or invalid 'passed' field")
        return None

    # 提取 drift_score (必需)
    drift_score = data.get("drift_score")
    if not isinstance(drift_score, (int, float)):
        logger.warning("CriticAgent: missing or invalid 'drift_score' field")
        return None
    drift_score = float(drift_score)

    # 提取 confidence (必需)
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)):
        logger.warning("CriticAgent: missing or invalid 'confidence' field")
        return None
    confidence = float(confidence)

    # 提取 failures (可选，默认为空)
    failures_raw = data.get("failures", [])
    if not isinstance(failures_raw, list):
        logger.warning("CriticAgent: 'failures' is not a list, defaulting to []")
        failures_raw = []

    failures = []
    for f in failures_raw:
        if not isinstance(f, dict):
            continue
        check_type = f.get("check_type", "")
        severity = f.get("severity", "")
        evidence = f.get("evidence", "")
        explanation = f.get("explanation", "")

        # 跳过没有 check_type 的条目
        if not check_type:
            continue

        failures.append(
            CriticFailure(
                check_type=str(check_type),
                severity=str(severity) if severity else "low",
                evidence=str(evidence),
                explanation=str(explanation),
            )
        )

    return CriticOutput(
        passed=passed,
        failures=failures,
        drift_score=drift_score,
        confidence=confidence,
        raw_response=raw.strip(),
    )


# ============================================================
# CriticAgent
# ============================================================


class CriticAgent:
    """异步角色输出审查员。

    采样 ~10% 的回合，调用 cheap LLM（deepseek-chat）以 json_mode 评估回复。
    不在用户感知的延迟路径上。失败 → 静默跳过（best-effort）。

    用法:
        agent = CriticAgent(cost_tracker=tracker)
        output = await agent.evaluate(critic_input)
        if not output.passed:
            # 发出 soul.drift.detected 事件到 SS01
    """

    # 配置（§2 Runtime Configuration）
    _DEFAULT_SAMPLING_RATE: float = DEFAULT_SAMPLING_RATE
    _TIMEOUT_SECONDS: float = 3.0  # timeout_ms: 3000
    _TEMPERATURE: float = 0.1  # near-deterministic
    _MAX_TOKENS: int = 600
    _AGENT_NAME: str = "CriticAgent.evaluate"

    def __init__(
        self,
        sampling_rate: float = DEFAULT_SAMPLING_RATE,
        cost_tracker: Optional[LLMCostTracker] = None,
        rng: Optional[random.Random] = None,
    ):
        """初始化 CriticAgent。

        Args:
            sampling_rate: 基准采样率（默认 0.10）
            cost_tracker: 可选的 LLMCostTracker 用于记录调用成本
            rng: 可选的 random.Random 实例（测试中用于固定种子）
        """
        self._sampling_rate = sampling_rate
        self._cost_tracker = cost_tracker
        self._rng = rng or random.Random()

        # System prompt 缓存，key: (character_id, stage)
        self._system_prompts: dict[tuple[str, str], str] = {}

    # ----- 采样判定 (§2 Sampling discipline) ---------------------------------

    def should_sample(self, inp: CriticInput) -> bool:
        """判定是否应对此回合进行 Critic 审查。

        两条确定性覆盖规则（优先级高于随机采样）：
        1. 若 was_rerolled → 100% 采样（已怀疑 drift）
        2. 若 recent_soft_never_warnings > 0 → 100% 采样（drift cluster）

        否则：均匀随机 ~10% 采样。

        Args:
            inp: 回合输入

        Returns:
            是否采样
        """
        # 覆盖规则 1: reroll → always sample
        if inp.was_rerolled:
            logger.debug(f"CriticAgent: force-sample (was_rerolled) for {inp.character_id}")
            return True

        # 覆盖规则 2: soft_never cluster → always sample
        if inp.recent_soft_never_warnings > 0:
            logger.debug(
                f"CriticAgent: force-sample (soft_never_warnings={inp.recent_soft_never_warnings}) "
                f"for {inp.character_id}"
            )
            return True

        # 均匀随机采样
        sampled = self._rng.random() < self._sampling_rate
        if sampled:
            logger.debug(f"CriticAgent: random-sample for {inp.character_id}")
        return sampled

    # ----- Prompt 构建 ---------------------------------------------------------

    def _build_system_prompt(self, inp: CriticInput) -> str:
        """构建缓存友好的 system prompt（§3.1）。

        以 (character_id, stage) 为 key 缓存。同一角色同一阶段复用。

        Args:
            inp: 回合输入

        Returns:
            完整的 system prompt 字符串
        """
        cache_key = (inp.character_id, inp.stage)
        if cache_key not in self._system_prompts:
            self._system_prompts[cache_key] = _SYSTEM_PROMPT_TEMPLATE.format(
                character_id=inp.character_id,
                voice_dna_summary=inp.voice_dna_summary,
                hard_never_list=inp.hard_never_list,
                stage=inp.stage,
                stage_envelope_summary=inp.stage_envelope_summary,
                l4_facts=inp.l4_facts,
            )
        return self._system_prompts[cache_key]

    def _build_user_prompt(self, inp: CriticInput) -> str:
        """构建每回合唯一的 user prompt（§3.2）。

        Args:
            inp: 回合输入

        Returns:
            user prompt 字符串
        """
        return _USER_PROMPT_TEMPLATE.format(
            user_message=inp.user_message,
            character_id=inp.character_id,
            assistant_response=inp.assistant_response,
        )

    # ----- LLM 调用 -----------------------------------------------------------

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        user_id: str = "unknown",
    ) -> Optional[str]:
        """通过 ModelRouter 调用 cheap 模型，json_mode=True。

        timeout 后返回 None（best-effort）。

        Args:
            system_prompt: 缓存的 system prompt
            user_prompt: 本轮 user prompt
            user_id: 用户 ID（用于成本追踪）

        Returns:
            LLM 原始响应文本，或 None（超时/错误）
        """
        from heart.infra.llm_providers import get_model_router

        try:
            router = await get_model_router()
            response_text = await asyncio.wait_for(
                router.call_cheap(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self._TEMPERATURE,
                    max_tokens=self._MAX_TOKENS,
                    json_mode=True,
                    agent_name=self._AGENT_NAME,
                ),
                timeout=self._TIMEOUT_SECONDS,
            )

            # 记录到 cost tracker（如果已配置）
            if self._cost_tracker:
                await self._record_cost(user_id, response_text)

            return response_text

        except asyncio.TimeoutError:
            logger.warning(f"CriticAgent: LLM call timed out after {self._TIMEOUT_SECONDS}s")
            return None
        except Exception as e:
            logger.warning(f"CriticAgent: LLM call error: {e}")
            return None

    async def _record_cost(self, user_id: str, response_text: str) -> None:
        """记录 LLM 调用成本到 cost tracker。

        Args:
            user_id: 用户 ID
            response_text: LLM 响应（用于估算 token 数）
        """
        if self._cost_tracker is None:
            return

        try:
            from heart.infra.llm_cost_tracker import LLMCall

            # 估算 token 数（粗略：中文约 1.5 字符/token，英文约 4 字符/token）
            est_output_tokens = max(1, len(response_text) // 2)
            # prompt token 估算（system + user prompt 一般 < 2000 tokens）
            est_input_tokens = 2000

            call = LLMCall(
                model="deepseek-chat",
                prompt_tokens=est_input_tokens,
                completion_tokens=est_output_tokens,
                user_id=user_id,
                agent_name=self._AGENT_NAME,
                provider="deepseek",
            )
            await self._cost_tracker.record(call)
        except Exception as e:
            logger.debug(f"CriticAgent: cost tracking skipped: {e}")

    # ----- 主入口 -------------------------------------------------------------

    async def evaluate(
        self,
        inp: CriticInput,
        user_id: str = "unknown",
        force: bool = False,
    ) -> Optional[CriticOutput]:
        """评估一次角色回复。

        流程：
        1. 采样判定（或 force=True 跳过）
        2. 构建 prompt（system 缓存命中）
        3. 调用 cheap LLM，json_mode=True
        4. 解析 JSON → CriticOutput
        5. 返回结果（passed=false 时由调用方发出 drift 事件）

        Args:
            inp: 回合输入
            user_id: 用户 ID（用于成本追踪）
            force: 强制评估，跳过采样判定

        Returns:
            CriticOutput 或 None（未采样 / LLM 失败 / JSON 解析失败）
        """
        # 采样判定
        if not force and not self.should_sample(inp):
            return None

        # 构建 prompt
        system_prompt = self._build_system_prompt(inp)
        user_prompt = self._build_user_prompt(inp)

        # 调用 LLM
        raw = await self._call_llm(system_prompt, user_prompt, user_id=user_id)
        if raw is None:
            return None

        # 解析响应
        output = _parse_critic_response(raw)
        if output is None:
            logger.warning(f"CriticAgent: failed to parse LLM response for {inp.character_id}")
            return None

        # 日志
        if not output.passed:
            logger.info(
                f"CriticAgent: drift detected for {inp.character_id} "
                f"(score={output.drift_score:.2f}, failures={len(output.failures)})"
            )
        else:
            logger.debug(
                f"CriticAgent: pass for {inp.character_id} (confidence={output.confidence:.2f})"
            )

        return output


# ============================================================
# Drift 事件构造工具
# ============================================================


def build_drift_event(
    user_id: str,
    character_id: str,
    turn_id: str,
    output: CriticOutput,
) -> dict:
    """从 CriticOutput 构造 soul.drift.detected 事件 payload (§5)。

    当 passed=false 时调用此函数，将结果回传给 SS01 Drift Detector。

    Args:
        user_id: 用户 ID
        character_id: 角色 ID
        turn_id: 回合 ID
        output: CriticAgent 的输出

    Returns:
        drift 事件 payload: {user_id, character_id, turn_id, drift_score, failures[]}
    """
    return {
        "user_id": user_id,
        "character_id": character_id,
        "turn_id": turn_id,
        "drift_score": output.drift_score,
        "failures": [
            {
                "check_type": f.check_type,
                "severity": f.severity,
                "evidence": f.evidence,
                "explanation": f.explanation,
            }
            for f in output.failures
        ],
    }
