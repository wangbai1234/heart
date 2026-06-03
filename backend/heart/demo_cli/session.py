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

    # ── Side panel refresh (stub) ──────────────────────────────

    async def refresh_side_panel(self) -> SidePanelState:
        """Refresh side-panel snapshot.  Currently a local stub."""
        msg_count = sum(1 for m in self.messages if m["role"] == "user")
        stages = [
            "STRANGER",
            "ACQUAINTANCE",
            "FRIEND",
            "CONFIDANT",
            "ROMANTIC_INTEREST",
            "LOVER",
            "BONDED",
        ]
        stage_idx = min(msg_count // 3, len(stages) - 1)
        self.side_panel.current_stage = stages[stage_idx]
        self.side_panel.current_stage_num = stage_idx + 1
        return self.side_panel

    # ── Dev actions ────────────────────────────────────────────

    async def dev_jump_stage(self, stage: str) -> str:
        """DEV ONLY: skip to a stage."""
        if not self.dev_mode:
            return "错误：/jump 仅在 --dev 模式下可用。"
        valid = {
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "stranger",
            "acquaintance",
            "friend",
            "confidant",
            "romantic_interest",
            "lover",
            "bonded",
        }
        key = stage.lower()
        if key not in valid:
            return f"无效 stage: {stage}。可用: 1-7 或阶段名。"
        stage_map = {
            "1": "STRANGER",
            "2": "ACQUAINTANCE",
            "3": "FRIEND",
            "4": "CONFIDANT",
            "5": "ROMANTIC_INTEREST",
            "6": "LOVER",
            "7": "BONDED",
        }
        target = stage_map.get(key, key.upper())
        self.side_panel.current_stage = target
        self.side_panel.current_stage_num = list(stage_map.values()).index(target) + 1
        return f"已跳过至阶段 {target} ({self.side_panel.current_stage_num}/7)。"

    def dev_toggle_cold_war(self) -> str:
        """DEV ONLY: toggle cold-war state."""
        if not self.dev_mode:
            return "错误：/coldwar 仅在 --dev 模式下可用。"
        self.side_panel.cold_war_active = not self.side_panel.cold_war_active
        status = "active" if self.side_panel.cold_war_active else "inactive"
        return f"冷战状态已切换为: {status}。"
