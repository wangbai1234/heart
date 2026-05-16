"""
Unit tests for LLM providers.

Tests provider interface with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from heart.infra.llm_providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    StreamChunk,
    Message,
    MessageRole,
    ProviderError,
)
from heart.infra.llm_providers.anthropic import DeepSeekV4ProProvider
from heart.infra.llm_providers.deepseek import DeepSeekV4FlashProvider
from heart.infra.llm_providers.registry import (
    ProviderRegistry,
    initialize_registry,
)


# Test fixtures
@pytest.fixture
def mock_deepseek_response():
    """Mock successful DeepSeek API response."""
    return {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "deepseek-reasoner",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def mock_deepseek_stream_chunks():
    """Mock streaming response chunks."""
    return [
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}\n',
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"content":" there"},"finish_reason":null}]}\n',
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}\n',
        'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}\n',
        'data: [DONE]\n',
    ]


@pytest.fixture
def sample_request():
    """Sample LLM request."""
    return LLMRequest(
        messages=[
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="Hello!"),
        ],
        model="deepseek-reasoner",
        temperature=0.7,
        max_tokens=100,
    )


# Tests for DeepSeekV4ProProvider
class TestDeepSeekV4ProProvider:
    """Test DeepSeek V4-pro provider."""

    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Test provider name property."""
        provider = DeepSeekV4ProProvider(api_key="test-key")
        assert provider.provider_name == "deepseek-v4-pro"

    @pytest.mark.asyncio
    async def test_call_success(self, sample_request, mock_deepseek_response):
        """Test non-streaming call with success."""
        provider = DeepSeekV4ProProvider(api_key="test-key")

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = mock_deepseek_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            response = await provider.call(sample_request)

            # Verify response
            assert isinstance(response, LLMResponse)
            assert response.content == "Hello! How can I help you today?"
            assert response.model == "deepseek-reasoner"
            assert response.finish_reason == "stop"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 20
            assert response.usage["total_tokens"] == 30

            # Verify API call
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/v1/chat/completions"
            assert call_args[1]["json"]["model"] == "deepseek-reasoner"
            assert call_args[1]["json"]["stream"] is False

    @pytest.mark.asyncio
    async def test_call_with_circuit_breaker(self, sample_request):
        """Test call respects circuit breaker."""
        mock_breaker = MagicMock()
        mock_breaker.is_open.return_value = True

        provider = DeepSeekV4ProProvider(
            api_key="test-key",
            circuit_breaker=mock_breaker,
        )

        with pytest.raises(ProviderError) as exc_info:
            await provider.call(sample_request)

        assert "Circuit breaker open" in str(exc_info.value)
        assert exc_info.value.retriable is True

    @pytest.mark.asyncio
    async def test_stream_success(self, sample_request, mock_deepseek_stream_chunks):
        """Test streaming call with success."""
        provider = DeepSeekV4FlashProvider(api_key="test-key")

        # Create async line iterator
        async def async_line_iter():
            for chunk in mock_deepseek_stream_chunks:
                yield chunk.rstrip("\n")

        # Mock streaming response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = async_line_iter
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            chunks = []
            async for chunk in provider.stream(sample_request):
                chunks.append(chunk)

            # Verify chunks
            assert len(chunks) > 0
            content_chunks = [c for c in chunks if c.content]
            assert len(content_chunks) == 3  # "Hello", " there", "!"

            # Verify final chunk has finish_reason
            final_chunk = chunks[-1]
            assert final_chunk.finish_reason == "stop"
            assert final_chunk.usage is not None

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        provider = DeepSeekV4ProProvider(api_key="test-key")

        cost = provider.estimate_cost(
            prompt_tokens=1000,
            estimated_completion_tokens=500,
            model="deepseek-reasoner",
        )

        # V4-pro pricing: $0.55 input, $2.19 output per 1M tokens
        expected_input = (1000 / 1_000_000) * 0.55
        expected_output = (500 / 1_000_000) * 2.19

        assert cost.prompt_tokens == 1000
        assert cost.estimated_completion_tokens == 500
        assert abs(cost.input_cost_usd - expected_input) < 0.0001
        assert abs(cost.output_cost_usd - expected_output) < 0.0001
        assert abs(cost.total_cost_usd - (expected_input + expected_output)) < 0.0001

    @pytest.mark.asyncio
    async def test_count_tokens(self):
        """Test token counting."""
        provider = DeepSeekV4ProProvider(api_key="test-key")

        text = "Hello world"  # 11 chars
        tokens = provider.count_tokens(text, "deepseek-reasoner")

        # Simple approximation: ~4 chars per token
        assert tokens == 11 // 4  # Should be 2


# Tests for DeepSeekV4FlashProvider
class TestDeepSeekV4FlashProvider:
    """Test DeepSeek V4-flash provider."""

    @pytest.mark.asyncio
    async def test_provider_name(self):
        """Test provider name property."""
        provider = DeepSeekV4FlashProvider(api_key="test-key")
        assert provider.provider_name == "deepseek-v4-flash"

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation for flash model."""
        provider = DeepSeekV4FlashProvider(api_key="test-key")

        cost = provider.estimate_cost(
            prompt_tokens=1000,
            estimated_completion_tokens=500,
            model="deepseek-chat",
        )

        # V4-flash pricing: $0.14 input, $0.28 output per 1M tokens
        expected_input = (1000 / 1_000_000) * 0.14
        expected_output = (500 / 1_000_000) * 0.28

        assert abs(cost.input_cost_usd - expected_input) < 0.0001
        assert abs(cost.output_cost_usd - expected_output) < 0.0001

    @pytest.mark.asyncio
    async def test_json_mode(self, mock_deepseek_response):
        """Test JSON mode request."""
        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="Return JSON")],
            model="deepseek-chat",
            json_mode=True,
        )

        provider = DeepSeekV4FlashProvider(api_key="test-key")

        # Mock client
        mock_response = MagicMock()
        mock_response.json.return_value = mock_deepseek_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            await provider.call(request)

            # Verify JSON mode in request
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["response_format"] == {"type": "json_object"}


# Tests for ProviderRegistry
class TestProviderRegistry:
    """Test provider registry."""

    def test_register_and_get_provider(self):
        """Test provider registration and retrieval."""
        registry = ProviderRegistry()

        registry.register_provider(
            provider_name="test-provider",
            provider_class=DeepSeekV4ProProvider,
            api_key="test-key",
            models=["test-model"],
        )

        # Get by provider name
        provider = registry.get_provider("test-provider")
        assert isinstance(provider, DeepSeekV4ProProvider)

        # Get by model name
        provider_by_model = registry.get_provider_for_model("test-model")
        assert provider_by_model is provider

    def test_get_nonexistent_provider(self):
        """Test getting nonexistent provider raises error."""
        registry = ProviderRegistry()

        with pytest.raises(KeyError):
            registry.get_provider("nonexistent")

    def test_get_provider_for_unmapped_model(self):
        """Test getting provider for unmapped model raises error."""
        registry = ProviderRegistry()

        with pytest.raises(KeyError):
            registry.get_provider_for_model("unknown-model")

    @pytest.mark.asyncio
    async def test_initialize_registry_from_env(self):
        """Test registry initialization from environment."""
        with patch.dict(
            "os.environ",
            {
                "DEEPSEEK_API_KEY": "test-key-123",
                "DEEPSEEK_BASE_URL": "https://test.api.com",
                "MAIN_LLM_MODEL": "deepseek-reasoner",
                "CHEAP_LLM_MODEL": "deepseek-chat",
            },
        ):
            registry = initialize_registry()

            # Verify providers registered
            assert registry.get_provider("deepseek-v4-pro") is not None
            assert registry.get_provider("deepseek-v4-flash") is not None

            # Verify model mappings
            pro_provider = registry.get_provider_for_model("deepseek-reasoner")
            assert isinstance(pro_provider, DeepSeekV4ProProvider)

            flash_provider = registry.get_provider_for_model("deepseek-chat")
            assert isinstance(flash_provider, DeepSeekV4FlashProvider)

    def test_initialize_registry_without_api_key(self):
        """Test registry initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                initialize_registry()

            assert "DEEPSEEK_API_KEY" in str(exc_info.value)


# Integration-style tests
class TestProviderIntegration:
    """Integration tests for provider usage patterns."""

    @pytest.mark.asyncio
    async def test_request_building(self):
        """Test building requests with different message types."""
        request = LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful."),
                Message(role=MessageRole.USER, content="Hello!"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!"),
                Message(role=MessageRole.USER, content="How are you?"),
            ],
            model="deepseek-chat",
            temperature=0.9,
            max_tokens=200,
        )

        assert len(request.messages) == 4
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[1].role == MessageRole.USER
        assert request.temperature == 0.9
        assert request.max_tokens == 200

    @pytest.mark.asyncio
    async def test_error_handling(self, sample_request):
        """Test error handling for HTTP failures."""
        provider = DeepSeekV4ProProvider(api_key="test-key")

        # Mock HTTP error
        from httpx import HTTPStatusError, Request, Response

        mock_request = Request("POST", "https://test.com")
        mock_response = Response(status_code=429, text="Rate limit exceeded")
        error = HTTPStatusError(
            "429 error",
            request=mock_request,
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=error)

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(ProviderError) as exc_info:
                await provider.call(sample_request)

            # Verify error details
            assert exc_info.value.status_code == 429
            assert exc_info.value.retriable is True
            assert exc_info.value.provider == "deepseek-v4-pro"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
