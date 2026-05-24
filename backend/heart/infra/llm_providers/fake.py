"""
Fake LLM Provider for Tier B integration tests.

100% deterministic — no API calls. Returns pre-configured responses
based on (system_prompt_hash, user_msg_hash) lookup in fixtures.

Design per integration_test_pyramid.md:
- Strict mode: cache miss -> test FAILS immediately (no fallback)
- Developer must add fixture for each new test path
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

from heart.infra.llm_providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    StreamChunk,
    CostEstimate,
    CircuitBreakerInterface,
)


class FakeLLMProvider(LLMProvider):
    """Deterministic fake LLM provider for integration tests."""

    def __init__(
        self,
        fixtures_dir: Optional[Path] = None,
        api_key: str = "fake-key",
        base_url: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreakerInterface] = None,
    ):
        super().__init__(api_key=api_key, base_url=base_url, circuit_breaker=circuit_breaker)

        if fixtures_dir is None:
            current_dir = Path(__file__)
            repo_root = current_dir.parent.parent.parent.parent
            fixtures_dir = repo_root / "tests" / "integration" / "fixtures" / "fake_llm_responses"

        self.fixtures_dir = Path(fixtures_dir)
        self._fixtures: Dict[str, dict] = {}
        self._hash_index: Dict[str, str] = {}
        self._load_fixtures()

    def _load_fixtures(self):
        if not self.fixtures_dir.exists():
            return

        for json_file in self.fixtures_dir.glob("*.json"):
            with open(json_file, "r") as f:
                data = json.load(f)
            fixture_id = data.get("fixture_id", json_file.stem)
            self._fixtures[fixture_id] = data

        for fixture_id, data in self._fixtures.items():
            for scenario in data.get("scenarios", []):
                key = self._make_key(
                    scenario.get("system_prompt_hint", ""),
                    scenario.get("user_msg_hint", ""),
                )
                self._hash_index[key] = fixture_id

    @staticmethod
    def _make_key(system_hint: str, user_hint: str) -> str:
        sys_hash = hashlib.sha256(system_hint.encode()).hexdigest()[:8]
        user_hash = hashlib.sha256(user_hint.encode()).hexdigest()[:8]
        return "{}|{}".format(sys_hash, user_hash)

    def _lookup_response(self, messages: list) -> dict:
        system_content = ""
        user_content = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            elif msg.get("role") == "user":
                user_content = msg.get("content", "")

        key = self._make_key(system_content, user_content)
        fixture_id = self._hash_index.get(key)

        if fixture_id is None:
            sys_hash = hashlib.sha256(system_content.encode()).hexdigest()[:8]
            user_hash = hashlib.sha256(user_content.encode()).hexdigest()[:8]
            raise KeyError(
                "FakeLLM: no fixture for system_hash={} user_hash={}. "
                "Add a fixture to {}/. "
                "System (first 100): {}. "
                "User (first 100): {}.".format(
                    sys_hash, user_hash, self.fixtures_dir,
                    system_content[:100], user_content[:100]
                )
            )

        fixture = self._fixtures[fixture_id]
        return fixture.get("default_response", {"content": fixture.get("content", "")})

    def _build_response(self, response_data: dict, request: LLMRequest) -> LLMResponse:
        content = response_data.get("content", "")
        return LLMResponse(
            content=content,
            model=request.model or "fake-model",
            finish_reason=response_data.get("finish_reason", "stop"),
            usage={
                "prompt_tokens": response_data.get("prompt_tokens", 100),
                "completion_tokens": len(content) // 4,
                "total_tokens": 100 + len(content) // 4,
            },
            provider=self.provider_name,
            metadata={"fixture_id": response_data.get("fixture_id", "unknown")},
        )

    @property
    def provider_name(self) -> str:
        return "fake"

    async def call(self, request: LLMRequest) -> LLMResponse:
        raw_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        response_data = self._lookup_response(raw_messages)
        return self._build_response(response_data, request)

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        raw_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        response_data = self._lookup_response(raw_messages)
        content = response_data.get("content", "")
        words = content.split()
        chunk_size = 5
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            if i + chunk_size >= len(words):
                yield StreamChunk(
                    content=chunk_text,
                    finish_reason="stop",
                    usage={"prompt_tokens": 100, "completion_tokens": len(content) // 4},
                )
            else:
                yield StreamChunk(content=chunk_text + " ")

    def estimate_cost(
        self,
        prompt_tokens: int,
        estimated_completion_tokens: int,
        model: str,
    ) -> CostEstimate:
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            input_cost_usd=0.0,
            output_cost_usd=0.0,
            total_cost_usd=0.0,
            model=model,
            provider=self.provider_name,
        )

    def count_tokens(self, text: str, model: str) -> int:
        return max(1, len(text) // 4)

    async def close(self) -> None:
        pass


__all__ = ["FakeLLMProvider"]
