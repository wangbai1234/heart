"""
Session management for the Heart demo CLI.

Maintains session_id, conversation history, and bridges to the Heart API
via HTTP only — no direct subsystem imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx

# ── API Constants ──────────────────────────────────────────────────

API_PREFIX = "/api"
HEALTH_PATH = "/health/live"


@dataclass
class SidePanelState:
    """Snapshot of the side-panel data for one turn."""

    current_stage: str = "STRANGER"
    current_stage_num: int = 1
    vad_valence: float = 0.0
    vad_arousal: float = 0.3
    vad_dominance: float = 0.5
    active_emotions: list[str] = field(default_factory=list)
    cold_war_active: bool = False
    cold_war_started_at: Optional[str] = None
    last_anniversary: Optional[str] = None


@dataclass
class ClientSession:
    """Client-side session state.  Talks to the Heart API over HTTP only."""

    api_url: str
    character_id: str
    session_id: uuid.UUID = field(default_factory=uuid.uuid4)

    token: Optional[str] = None
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)

    messages: list[dict[str, str]] = field(default_factory=list)
    side_panel: SidePanelState = field(default_factory=SidePanelState)
    dev_mode: bool = False

    # ── helpers ────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def check_health(self) -> bool:
        """Ping /health/live.  Returns True if the API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.api_url}{HEALTH_PATH}")
                return resp.status_code == 200
        except httpx.ConnectError:
            return False
        except OSError:
            return False

    async def check_readiness(self) -> dict:
        """Check /health/ready for full subsystem readiness.

        Returns:
            Dict with status and component details.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.api_url}/health/ready")
                if resp.status_code >= 500:
                    return {"status": "error", "error": f"HTTP {resp.status_code}"}
                return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_emotion_api(self) -> bool:
        """Verify /api/state/emotion is accessible.

        Returns:
            True if emotion API responds successfully.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/state/emotion",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def login(self) -> str:
        """POST /api/auth/login and store the returned token."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self.api_url}{API_PREFIX}/auth/login",
                json={"user_id": str(self.user_id)},
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data["access_token"]
            return self.token

    async def send_message(self, user_message: str) -> str:
        """Send one chat turn via POST /api/chat (real LLM endpoint)."""
        self.messages.append({"role": "user", "content": user_message})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.api_url}{API_PREFIX}/chat",
                json={
                    "messages": self.messages,
                    "character_id": self.character_id,
                },
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        assistant_text = data.get("response", "")
        self.messages.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    # ── Side panel refresh (real API) ──────────────────────────

    async def refresh_side_panel(self) -> SidePanelState:
        """Refresh side-panel snapshot from real API endpoints."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Get emotion state
                emotion_resp = await client.get(
                    f"{self.api_url}/api/state/emotion",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if emotion_resp.status_code == 200:
                    data = emotion_resp.json()
                    vad = data.get("vad", {})
                    self.side_panel.vad_valence = vad.get("valence", 0.0)
                    self.side_panel.vad_arousal = vad.get("arousal", 0.3)
                    self.side_panel.vad_dominance = vad.get("dominance", 0.5)
                    self.side_panel.active_emotions = [
                        e.get("emotion", "") for e in data.get("active_emotions", [])
                    ]

                # Get relationship state
                rel_resp = await client.get(
                    f"{self.api_url}/api/state/relationship",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if rel_resp.status_code == 200:
                    data = rel_resp.json()
                    self.side_panel.current_stage = data.get("phase", "stranger").upper()
                    stage_map = {
                        "stranger": 1,
                        "acquaintance": 2,
                        "friend": 3,
                        "confidant": 4,
                        "romantic_interest": 5,
                        "lover": 6,
                        "bonded": 7,
                    }
                    self.side_panel.current_stage_num = stage_map.get(
                        data.get("phase", "stranger"), 1
                    )

        except Exception:
            pass  # Keep existing state on error

        return self.side_panel

    # ── State inspection (real API) ────────────────────────────

    async def get_emotion_state(self) -> str:
        """Get emotion state from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/state/emotion",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    vad = data.get("vad", {})
                    emotions = data.get("active_emotions", [])
                    lines = [
                        f"  VAD: V={vad.get('valence', 0):+.2f} A={vad.get('arousal', 0):.2f} D={vad.get('dominance', 0):.2f}",
                    ]
                    if emotions:
                        emotion_strs = [
                            f"{e.get('emotion', '')}({e.get('intensity', 0):.1f})"
                            for e in emotions[:3]
                        ]
                        lines.append(f"  active_emotions: {', '.join(emotion_strs)}")
                    return "\n".join(lines)
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def get_relationship_state(self) -> str:
        """Get relationship state from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/state/relationship",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return (
                        f"  phase: {data.get('phase', 'stranger')} ({data.get('phase', 'stranger')}/7)\n"
                        f"  trust: {data.get('trust', 0):.2f}  attachment: {data.get('attachment', 'secure')}  "
                        f"intimacy: {data.get('intimacy', 0):.2f}"
                    )
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def get_inner_state(self) -> str:
        """Get inner state from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/state/inner",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return (
                        f"  mood: {data.get('mood', 0.5):.2f}  energy: {data.get('energy', 0.6):.2f}\n"
                        f"  ticks_today: {data.get('ticks_today', 0)}  "
                        f"proactives_today: {data.get('proactives_today', 0)}"
                    )
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def get_recent_memories(self) -> str:
        """Get recent memories from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/memory/recent",
                    params={
                        "user_id": str(self.user_id),
                        "character_id": self.character_id,
                        "limit": 10,
                    },
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    episodes = data.get("episodes", [])
                    facts = data.get("facts", [])

                    lines = ["  最近 L2 episodes:"]
                    if episodes:
                        for ep in episodes[:5]:
                            lines.append(f"    - {ep.get('summary', '(无)')}")
                    else:
                        lines.append("    (空)")

                    lines.append("  检索到的 L3 facts:")
                    if facts:
                        for f in facts[:5]:
                            lines.append(
                                f'    - "{f.get("subject", "")} {f.get("predicate", "")} {f.get("object", "")}" '
                                f"(importance {f.get('importance', 0):.1f})"
                            )
                    else:
                        lines.append("    (空)")

                    return "\n".join(lines)
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def get_l4_identity(self) -> str:
        """Get L4 identity memories from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/memory/l4",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    memories = data.get("memories", [])

                    lines = ["  她记得的我:"]
                    if memories:
                        for m in memories[:10]:
                            lines.append(f"    - {m.get('key', '')}：{m.get('value', '')}")
                    else:
                        lines.append("    (空)")

                    return "\n".join(lines)
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def get_pending_proactive(self) -> str:
        """Get pending proactive messages from API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.api_url}/api/proactive/pending",
                    params={"user_id": str(self.user_id), "character_id": self.character_id},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    messages = data.get("messages", [])

                    if not messages:
                        return "  (没有待发消息)"

                    lines = []
                    for m in messages:
                        lines.append(f"  [{m.get('trigger_type', '')}] {m.get('content', '')}")
                    return "\n".join(lines)
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    # ── Dev actions (real API) ─────────────────────────────────

    async def dev_jump_stage(self, stage: str) -> str:
        """DEV ONLY: skip to a stage via API."""
        if not self.dev_mode:
            return "错误：/jump 仅在 --dev 模式下可用。"

        stage_num_map = {
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "stranger": 1,
            "acquaintance": 2,
            "friend": 3,
            "confidant": 4,
            "romantic_interest": 5,
            "lover": 6,
            "bonded": 7,
        }
        key = stage.lower()
        phase_num = stage_num_map.get(key)
        if phase_num is None:
            return f"无效 stage: {stage}。可用: 1-7 或阶段名。"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.api_url}/api/dev/jump_phase",
                    params={
                        "user_id": str(self.user_id),
                        "character_id": self.character_id,
                        "phase": phase_num,
                    },
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "error" in data:
                        return f"  错误: {data['error']}"
                    return f"  已跳到 {data.get('jumped_to', '?')} ({phase_num}/7)"
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def dev_sleep(self, hours: int = 24) -> str:
        """DEV ONLY: fast-forward time via API."""
        if not self.dev_mode:
            return "错误：/sleep 仅在 --dev 模式下可用。"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.api_url}/api/dev/sleep",
                    params={
                        "user_id": str(self.user_id),
                        "character_id": self.character_id,
                        "hours": hours,
                    },
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "error" in data:
                        return f"  错误: {data['error']}"
                    return f"  时间快进 {hours}h，decay 已触发，inner loop tick 1 次"
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"

    async def dev_toggle_cold_war(self, active: bool = True) -> str:
        """DEV ONLY: toggle cold-war state via API."""
        if not self.dev_mode:
            return "错误：/coldwar 仅在 --dev 模式下可用。"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.api_url}/api/dev/coldwar",
                    params={
                        "user_id": str(self.user_id),
                        "character_id": self.character_id,
                        "active": active,
                    },
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "error" in data:
                        return f"  错误: {data['error']}"
                    status = "激活" if active else "解除"
                    return f"  冷战已{status}"
                return f"  错误: {resp.status_code}"
        except Exception as e:
            return f"  错误: {e}"
