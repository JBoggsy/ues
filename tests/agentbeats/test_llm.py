"""Tests for LLM integration module.

Tests cover LLM configuration, providers, and response necessity checking.
"""

import hashlib
import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.green.llm import (
    AnthropicProvider,
    LLMConfig,
    LLMError,
    LLMProvider,
    MockLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    ResponseDecision,
    ResponseNecessityChecker,
)


# =============================================================================
# LLMConfig Tests
# =============================================================================


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_default_values(self):
        """Test default configuration."""
        config = LLMConfig()
        assert config.model == "gemma3:12b"
        assert config.host == "http://localhost:11434"
        assert config.timeout == 120.0
        assert config.seed is None
        assert config.temperature is None
        assert config.max_tokens is None
        assert config.extra == {}

    def test_custom_values(self):
        """Test custom configuration."""
        config = LLMConfig(
            model="llama3:8b",
            host="http://192.168.1.100:11434",
            timeout=60.0,
            seed=42,
            temperature=0.8,
            max_tokens=1000,
            extra={"custom": "value"},
        )
        assert config.model == "llama3:8b"
        assert config.host == "http://192.168.1.100:11434"
        assert config.timeout == 60.0
        assert config.seed == 42
        assert config.temperature == 0.8
        assert config.max_tokens == 1000
        assert config.extra["custom"] == "value"

    def test_get_temperature_explicit(self):
        """Explicit temperature is returned as-is."""
        config = LLMConfig(temperature=0.5)
        assert config.get_temperature() == 0.5
        assert config.get_temperature("some_hash") == 0.5

    def test_get_temperature_default_no_seed(self):
        """Without seed, default temperature is 0.7."""
        config = LLMConfig()
        assert config.get_temperature() == 0.7

    def test_get_temperature_seeded(self):
        """With seed, temperature is deterministically computed."""
        config = LLMConfig(seed=42)
        temp = config.get_temperature()
        # Should be in valid range
        assert 0.5 <= temp <= 0.9

    def test_get_temperature_seeded_with_hash(self):
        """With seed + prompt hash, temperature varies per call."""
        config = LLMConfig(seed=42)

        temp1 = config.get_temperature("hash1")
        temp2 = config.get_temperature("hash2")

        # Both should be in valid range
        assert 0.5 <= temp1 <= 0.9
        assert 0.5 <= temp2 <= 0.9

        # Should likely differ (extremely unlikely to be equal)
        # Not asserting inequality since it's theoretically possible

    def test_get_temperature_deterministic(self):
        """Same seed + hash should give same temperature."""
        config = LLMConfig(seed=42)

        temp1 = config.get_temperature("same_hash")
        temp2 = config.get_temperature("same_hash")

        assert temp1 == temp2


# =============================================================================
# MockLLMProvider Tests
# =============================================================================


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""

    def test_basic_init(self):
        """Initialize with config."""
        config = LLMConfig(seed=42)
        provider = MockLLMProvider(config)
        assert provider.config == config

    @pytest.mark.asyncio
    async def test_keyword_response(self):
        """Keyword match returns configured response."""
        provider = MockLLMProvider(LLMConfig())
        provider.add_response("party", "I'd love to come to the party!")

        response = await provider.generate("Are you coming to my party?")
        assert response == "I'd love to come to the party!"

    @pytest.mark.asyncio
    async def test_keyword_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        provider = MockLLMProvider(LLMConfig())
        provider.add_response("HELLO", "Hi there!")

        response = await provider.generate("hello world")
        assert response == "Hi there!"

    @pytest.mark.asyncio
    async def test_queued_response_priority(self):
        """Queued responses take priority over keywords."""
        provider = MockLLMProvider(LLMConfig())
        provider.add_response("hello", "Keyword response")
        provider.queue_response("Queued response")

        response = await provider.generate("hello")
        assert response == "Queued response"

        # Second call should use keyword
        response2 = await provider.generate("hello")
        assert response2 == "Keyword response"

    @pytest.mark.asyncio
    async def test_queued_responses_fifo(self):
        """Queued responses are returned in FIFO order."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("First")
        provider.queue_response("Second")
        provider.queue_response("Third")

        assert await provider.generate("any") == "First"
        assert await provider.generate("any") == "Second"
        assert await provider.generate("any") == "Third"

    @pytest.mark.asyncio
    async def test_fallback_response(self):
        """Fallback response when no keyword or queue match."""
        provider = MockLLMProvider(LLMConfig(seed=42))

        response = await provider.generate("something random")

        # Should be one of the canned responses
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_call_history_tracked(self):
        """All calls are tracked in history."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("response1")
        provider.queue_response("response2")

        await provider.generate("prompt1", "system1")
        await provider.generate("prompt2", None)

        history = provider.get_call_history()
        assert len(history) == 2
        assert history[0]["prompt"] == "prompt1"
        assert history[0]["system_prompt"] == "system1"
        assert history[1]["prompt"] == "prompt2"
        assert history[1]["system_prompt"] is None

    @pytest.mark.asyncio
    async def test_clear_history(self):
        """History can be cleared."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("response")

        await provider.generate("test")
        assert len(provider.get_call_history()) == 1

        provider.clear_history()
        assert len(provider.get_call_history()) == 0


# =============================================================================
# OllamaProvider Tests
# =============================================================================


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_init(self):
        """Initialize with config."""
        config = LLMConfig(model="mistral:7b", host="http://custom:11434")
        provider = OllamaProvider(config)
        assert provider.config.model == "mistral:7b"
        assert provider.config.host == "http://custom:11434"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful generation call."""
        config = LLMConfig(seed=42, max_tokens=100)
        provider = OllamaProvider(config)

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Hello there!"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.generate("Hello!", "You are helpful.")

            assert result == "Hello there!"

            # Verify call parameters
            call_args = mock_client.post.call_args
            assert "http://localhost:11434/api/generate" in str(call_args)
            json_body = call_args.kwargs["json"]
            assert json_body["model"] == "gemma3:12b"
            assert json_body["prompt"] == "Hello!"
            assert json_body["system"] == "You are helpful."
            assert json_body["options"]["seed"] == 42
            assert json_body["options"]["num_predict"] == 100

    @pytest.mark.asyncio
    async def test_generate_no_system_prompt(self):
        """Generation without system prompt."""
        config = LLMConfig()
        provider = OllamaProvider(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Response text"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await provider.generate("Hello!")

            json_body = mock_client.post.call_args.kwargs["json"]
            assert "system" not in json_body

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """HTTP error raises LLMError."""
        import httpx

        config = LLMConfig()
        provider = OllamaProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMError) as exc_info:
                await provider.generate("Hello!")

            assert "Ollama API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        """Connection error raises LLMError."""
        import httpx

        config = LLMConfig()
        provider = OllamaProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMError) as exc_info:
                await provider.generate("Hello!")

            assert "Ollama connection error" in str(exc_info.value)


# =============================================================================
# OpenAIProvider Tests
# =============================================================================


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_init_without_api_key_fails(self):
        """Initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure OPENAI_API_KEY is not set
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

            with pytest.raises(LLMError) as exc_info:
                OpenAIProvider(LLMConfig())

            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_init_with_api_key(self):
        """Initialization succeeds with API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider(LLMConfig())
            assert provider.api_key == "test-key"
            # Should use default model
            assert provider.config.model == "gpt-4o"
            assert provider.config.host == "https://api.openai.com/v1"

    def test_init_with_custom_model(self):
        """Custom model is preserved."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider(LLMConfig(model="gpt-4-turbo"))
            assert provider.config.model == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful generation call."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = LLMConfig(seed=42, max_tokens=100)
            provider = OpenAIProvider(config)

            # Mock httpx response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello there!"}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await provider.generate("Hello!", "You are helpful.")

                assert result == "Hello there!"

                # Verify call parameters
                call_args = mock_client.post.call_args
                assert "chat/completions" in str(call_args)
                json_body = call_args.kwargs["json"]
                assert json_body["model"] == "gpt-4o"
                assert json_body["messages"][0] == {"role": "system", "content": "You are helpful."}
                assert json_body["messages"][1] == {"role": "user", "content": "Hello!"}
                assert json_body["seed"] == 42
                assert json_body["max_tokens"] == 100

                # Verify headers
                headers = call_args.kwargs["headers"]
                assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_generate_without_system_prompt(self):
        """Generation without system prompt."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider(LLMConfig())

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await provider.generate("Hello!")

                json_body = mock_client.post.call_args.kwargs["json"]
                # Should only have user message
                assert len(json_body["messages"]) == 1
                assert json_body["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """HTTP error raises LLMError."""
        import httpx

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider(LLMConfig())

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Rate limited", request=MagicMock(), response=mock_response
                )
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(LLMError) as exc_info:
                    await provider.generate("Hello!")

                assert "OpenAI API error" in str(exc_info.value)


# =============================================================================
# AnthropicProvider Tests
# =============================================================================


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_init_without_api_key_fails(self):
        """Initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            if "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]

            with pytest.raises(LLMError) as exc_info:
                AnthropicProvider(LLMConfig())

            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_init_with_api_key(self):
        """Initialization succeeds with API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider(LLMConfig())
            assert provider.api_key == "test-key"
            # Should use default model
            assert provider.config.model == "claude-sonnet-4-20250514"
            assert provider.config.host == "https://api.anthropic.com"

    def test_init_with_custom_model(self):
        """Custom model is preserved."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider(LLMConfig(model="claude-3-opus-20240229"))
            assert provider.config.model == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful generation call."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            config = LLMConfig(max_tokens=100)
            provider = AnthropicProvider(config)

            # Mock httpx response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": [{"text": "Hello there!"}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await provider.generate("Hello!", "You are helpful.")

                assert result == "Hello there!"

                # Verify call parameters
                call_args = mock_client.post.call_args
                assert "v1/messages" in str(call_args)
                json_body = call_args.kwargs["json"]
                assert json_body["model"] == "claude-sonnet-4-20250514"
                assert json_body["messages"] == [{"role": "user", "content": "Hello!"}]
                assert json_body["system"] == "You are helpful."
                assert json_body["max_tokens"] == 100

                # Verify headers
                headers = call_args.kwargs["headers"]
                assert headers["x-api-key"] == "test-key"
                assert "anthropic-version" in headers

    @pytest.mark.asyncio
    async def test_generate_without_system_prompt(self):
        """Generation without system prompt."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider(LLMConfig())

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": [{"text": "Response"}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await provider.generate("Hello!")

                json_body = mock_client.post.call_args.kwargs["json"]
                # Should not have system field
                assert "system" not in json_body

    @pytest.mark.asyncio
    async def test_generate_default_max_tokens(self):
        """Default max_tokens is set for Anthropic."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider(LLMConfig())  # No max_tokens

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": [{"text": "Response"}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await provider.generate("Hello!")

                json_body = mock_client.post.call_args.kwargs["json"]
                # Anthropic requires max_tokens, should default to 4096
                assert json_body["max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """HTTP error raises LLMError."""
        import httpx

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider(LLMConfig())

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Unauthorized", request=MagicMock(), response=mock_response
                )
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(LLMError) as exc_info:
                    await provider.generate("Hello!")

                assert "Anthropic API error" in str(exc_info.value)


# =============================================================================
# ResponseDecision Tests
# =============================================================================


class TestResponseDecision:
    """Tests for ResponseDecision dataclass."""

    def test_creation(self):
        """Create response decision."""
        decision = ResponseDecision(
            needs_response=True,
            reason="Contains a question that needs answering",
        )
        assert decision.needs_response is True
        assert "question" in decision.reason

    def test_no_response(self):
        """No response decision."""
        decision = ResponseDecision(
            needs_response=False,
            reason="This is a closing statement",
        )
        assert decision.needs_response is False


# =============================================================================
# ResponseNecessityChecker Tests
# =============================================================================


class TestResponseNecessityChecker:
    """Tests for ResponseNecessityChecker."""

    def test_init(self):
        """Initialize with LLM provider."""
        provider = MockLLMProvider(LLMConfig())
        checker = ResponseNecessityChecker(provider)
        assert checker.llm == provider

    @pytest.mark.asyncio
    async def test_check_needs_response(self):
        """Check detects message needing response."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("NEEDS_RESPONSE: Question requires an answer")
        checker = ResponseNecessityChecker(provider)

        decision = await checker.check("Are you coming to the party?")

        assert decision.needs_response is True
        assert "Question requires an answer" in decision.reason

    @pytest.mark.asyncio
    async def test_check_no_response(self):
        """Check detects message not needing response."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("NO_RESPONSE: This is a closing statement")
        checker = ResponseNecessityChecker(provider)

        decision = await checker.check("Sounds good, see you then!")

        assert decision.needs_response is False
        assert "closing statement" in decision.reason

    @pytest.mark.asyncio
    async def test_check_with_context(self):
        """Check includes conversation context in prompt."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("NEEDS_RESPONSE: Follow-up question")
        checker = ResponseNecessityChecker(provider)

        await checker.check(
            message_content="What time?",
            conversation_context="Previous: Let's meet tomorrow.",
            sender_name="Jamie",
        )

        # Verify the prompt included context
        history = provider.get_call_history()
        assert len(history) == 1
        prompt = history[0]["prompt"]
        assert "Let's meet tomorrow" in prompt
        assert "What time?" in prompt
        assert "Jamie" in prompt

    @pytest.mark.asyncio
    async def test_check_ambiguous_response_defaults_to_respond(self):
        """Ambiguous LLM output defaults to needing response."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("I'm not sure what to make of this message.")
        checker = ResponseNecessityChecker(provider)

        decision = await checker.check("Some message")

        assert decision.needs_response is True
        assert "Ambiguous" in decision.reason

    @pytest.mark.asyncio
    async def test_check_llm_error_defaults_to_respond(self):
        """LLM error defaults to needing response."""
        provider = MockLLMProvider(LLMConfig())
        checker = ResponseNecessityChecker(provider)

        # Replace generate with error-raising version
        async def raise_error(*args, **kwargs):
            raise LLMError("Connection failed")

        provider.generate = raise_error

        decision = await checker.check("Some message")

        assert decision.needs_response is True
        assert "failed" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_system_prompt_content(self):
        """System prompt includes guidelines."""
        provider = MockLLMProvider(LLMConfig())
        provider.queue_response("NEEDS_RESPONSE: Test")
        checker = ResponseNecessityChecker(provider)

        await checker.check("Test message")

        history = provider.get_call_history()
        system_prompt = history[0]["system_prompt"]

        # Should include guidance categories
        assert "NEED a response" in system_prompt
        assert "NOT need a response" in system_prompt
        assert "Questions" in system_prompt
        assert "acknowledgments" in system_prompt.lower()


# =============================================================================
# LLMProvider Abstract Base Class Tests
# =============================================================================


class TestLLMProviderABC:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Cannot instantiate abstract class."""
        with pytest.raises(TypeError):
            LLMProvider(LLMConfig())

    def test_hash_prompt(self):
        """Test prompt hashing helper."""
        config = LLMConfig()
        provider = MockLLMProvider(config)

        # Access protected method for testing
        hash1 = provider._hash_prompt("prompt1", "system1")
        hash2 = provider._hash_prompt("prompt1", "system1")
        hash3 = provider._hash_prompt("prompt2", "system1")

        # Same inputs should give same hash
        assert hash1 == hash2
        # Different inputs should (likely) give different hash
        assert hash1 != hash3
        # Hash should be 8 characters
        assert len(hash1) == 8
