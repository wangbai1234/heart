"""
Contract: Model Router must satisfy RouterProviderProtocol.
per runtime_specs/08_engineering_architecture.md §3

Verifies that ModelRouter exposes call_main and call_cheap.
"""

import pytest

from heart.infra.llm.router import ModelRouter


@pytest.mark.contract
class TestRouterProviderProtocol:
    """ModelRouter must satisfy the RouterProviderProtocol."""

    def test_model_router_has_call_main(self):
        """ModelRouter must expose call_main method."""
        assert hasattr(ModelRouter, "call_main")

    def test_model_router_has_call_cheap(self):
        """ModelRouter must expose call_cheap method."""
        assert hasattr(ModelRouter, "call_cheap")

    def test_call_main_signature_matches_protocol(self):
        """call_main signature must match: (messages, temperature, max_tokens, agent_name) -> str."""
        import inspect

        sig = inspect.signature(ModelRouter.call_main)
        params = list(sig.parameters.keys())
        assert "messages" in params
        assert "temperature" in params
        assert "max_tokens" in params
        assert "agent_name" in params

    def test_call_cheap_signature_matches_protocol(self):
        """call_cheap signature must match: (messages, temperature, max_tokens, json_mode, agent_name) -> str."""
        import inspect

        sig = inspect.signature(ModelRouter.call_cheap)
        params = list(sig.parameters.keys())
        assert "messages" in params
        assert "json_mode" in params
        assert "agent_name" in params
