"""LLM integration interface for response generation.

This module provides an abstract interface for LLM providers, enabling the response
generator to work with different LLM backends (Ollama, OpenAI, Anthropic) and supports
testing with mock implementations.

Key features:
- Abstract LLMProvider base class
- Concrete providers: OllamaProvider, OpenAIProvider, AnthropicProvider
- MockLLMProvider for deterministic testing
- Seed-based temperature control for reproducibility
- API keys loaded from .env file via python-dotenv

Environment Variables:
    OPENAI_API_KEY: API key for OpenAI provider
    ANTHROPIC_API_KEY: API key for Anthropic provider

Example:
    >>> from agentbeats.green.llm import OpenAIProvider, LLMConfig
    >>> config = LLMConfig(model="gpt-4o", seed=42)
    >>> provider = OpenAIProvider(config)
    >>> response = await provider.generate(
    ...     prompt="Write a reply to this email...",
    ...     system_prompt="You are Jamie Walsh, a friendly person..."
    ... )
"""

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM providers.

    Attributes:
        model: Model name/identifier (e.g., "gemma3:12b", "gpt-4").
        host: API endpoint URL.
        timeout: Request timeout in seconds.
        seed: Random seed for reproducible outputs.
        temperature: Sampling temperature (0.0-1.0). If None, uses default.
        max_tokens: Maximum tokens to generate. If None, uses default.
        extra: Additional provider-specific options.
    """

    model: str = "gemma3:12b"
    host: str = "http://localhost:11434"
    timeout: float = 120.0
    seed: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def get_temperature(self, prompt_hash: str | None = None) -> float:
        """Get temperature, optionally seeded for reproducibility.

        If seed is set and temperature is not explicitly set, computes a
        deterministic temperature based on seed and optional prompt hash.

        Args:
            prompt_hash: Optional hash of the prompt for per-call variation.

        Returns:
            Temperature value between 0.0 and 1.0.
        """
        if self.temperature is not None:
            return self.temperature

        if self.seed is None:
            return 0.7  # Default temperature

        # Generate deterministic temperature from seed
        seed_str = str(self.seed)
        if prompt_hash:
            seed_str += prompt_hash

        hash_bytes = hashlib.sha256(seed_str.encode()).digest()
        # Map first 4 bytes to float in [0.5, 0.9] range for reasonable creativity
        hash_int = int.from_bytes(hash_bytes[:4], "big")
        return 0.5 + (hash_int % 1000) / 2500  # Range: 0.5-0.9


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Subclasses must implement the generate() method to call their
    respective LLM APIs.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the provider with configuration.

        Args:
            config: LLM configuration options.
        """
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user/main prompt containing context and instructions.
            system_prompt: Optional system prompt defining behavior/persona.

        Returns:
            Generated text response.

        Raises:
            LLMError: If the LLM call fails.
        """
        pass

    def _hash_prompt(self, prompt: str, system_prompt: str | None) -> str:
        """Create a hash of prompts for seeded temperature calculation."""
        combined = prompt + (system_prompt or "")
        return hashlib.md5(combined.encode()).hexdigest()[:8]


class LLMError(Exception):
    """Exception raised when LLM generation fails."""

    pass


class OllamaProvider(LLMProvider):
    """LLM provider using local Ollama server.

    Ollama provides local inference for models like Gemma, Llama, Mistral.
    See: https://ollama.ai/

    Example:
        >>> provider = OllamaProvider(LLMConfig(model="gemma3:12b"))
        >>> response = await provider.generate("Hello!", "You are a helpful assistant.")
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a response using Ollama.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.

        Returns:
            Generated text.

        Raises:
            LLMError: If the Ollama API call fails.
        """
        prompt_hash = self._hash_prompt(prompt, system_prompt)
        temperature = self.config.get_temperature(prompt_hash)

        request_body: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system_prompt:
            request_body["system"] = system_prompt

        if self.config.seed is not None:
            request_body["options"]["seed"] = self.config.seed

        if self.config.max_tokens is not None:
            request_body["options"]["num_predict"] = self.config.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.host}/api/generate",
                    json=request_body,
                )
                response.raise_for_status()
                return response.json()["response"]
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Ollama API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise LLMError(f"Ollama connection error: {e}") from e
        except (KeyError, ValueError) as e:
            raise LLMError(f"Ollama response parse error: {e}") from e


class OpenAIProvider(LLMProvider):
    """LLM provider using OpenAI API.

    Supports GPT-4, GPT-4o, GPT-3.5-turbo, and other OpenAI models.
    API key is loaded from OPENAI_API_KEY environment variable.

    Example:
        >>> provider = OpenAIProvider(LLMConfig(model="gpt-4o"))
        >>> response = await provider.generate("Hello!", "You are a helpful assistant.")
    """

    DEFAULT_HOST = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, config: LLMConfig):
        """Initialize the OpenAI provider.

        Args:
            config: LLM configuration. Model defaults to gpt-4o.

        Raises:
            LLMError: If OPENAI_API_KEY is not set.
        """
        super().__init__(config)
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError(
                "OPENAI_API_KEY environment variable not set. "
                "Add it to your .env file or set it in your environment."
            )

        # Use OpenAI defaults if not specified
        if config.model == "gemma3:12b":  # Default from LLMConfig
            self.config.model = self.DEFAULT_MODEL
        if config.host == "http://localhost:11434":  # Default from LLMConfig
            self.config.host = self.DEFAULT_HOST

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a response using OpenAI API.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.

        Returns:
            Generated text.

        Raises:
            LLMError: If the OpenAI API call fails.
        """
        prompt_hash = self._hash_prompt(prompt, system_prompt)
        temperature = self.config.get_temperature(prompt_hash)

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }

        if self.config.seed is not None:
            request_body["seed"] = self.config.seed

        if self.config.max_tokens is not None:
            request_body["max_tokens"] = self.config.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.host}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise LLMError(f"OpenAI API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise LLMError(f"OpenAI connection error: {e}") from e
        except (KeyError, ValueError, IndexError) as e:
            raise LLMError(f"OpenAI response parse error: {e}") from e


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic API.

    Supports Claude 3.5, Claude 3, and other Anthropic models.
    API key is loaded from ANTHROPIC_API_KEY environment variable.

    Example:
        >>> provider = AnthropicProvider(LLMConfig(model="claude-sonnet-4-20250514"))
        >>> response = await provider.generate("Hello!", "You are a helpful assistant.")
    """

    DEFAULT_HOST = "https://api.anthropic.com"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    API_VERSION = "2023-06-01"

    def __init__(self, config: LLMConfig):
        """Initialize the Anthropic provider.

        Args:
            config: LLM configuration. Model defaults to claude-sonnet-4-20250514.

        Raises:
            LLMError: If ANTHROPIC_API_KEY is not set.
        """
        super().__init__(config)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Add it to your .env file or set it in your environment."
            )

        # Use Anthropic defaults if not specified
        if config.model == "gemma3:12b":  # Default from LLMConfig
            self.config.model = self.DEFAULT_MODEL
        if config.host == "http://localhost:11434":  # Default from LLMConfig
            self.config.host = self.DEFAULT_HOST

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a response using Anthropic API.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.

        Returns:
            Generated text.

        Raises:
            LLMError: If the Anthropic API call fails.
        """
        prompt_hash = self._hash_prompt(prompt, system_prompt)
        temperature = self.config.get_temperature(prompt_hash)

        request_body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": self.config.max_tokens or 4096,  # Anthropic requires max_tokens
        }

        if system_prompt:
            request_body["system"] = system_prompt

        # Note: Anthropic doesn't support seed parameter directly
        # Temperature seeding is handled by LLMConfig.get_temperature()

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.host}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": self.API_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
                return response.json()["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Anthropic API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise LLMError(f"Anthropic connection error: {e}") from e
        except (KeyError, ValueError, IndexError) as e:
            raise LLMError(f"Anthropic response parse error: {e}") from e


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing.

    Returns pre-configured responses or generates deterministic responses
    based on the prompt content. Useful for unit testing without LLM calls.

    Example:
        >>> provider = MockLLMProvider(LLMConfig())
        >>> provider.add_response("invite", "Thanks for the invite! I'll be there!")
        >>> response = await provider.generate("You're invited to my party")
        >>> assert "Thanks" in response
    """

    def __init__(self, config: LLMConfig):
        """Initialize the mock provider.

        Args:
            config: LLM configuration (seed affects deterministic responses).
        """
        super().__init__(config)
        self._responses: dict[str, str] = {}
        self._response_queue: list[str] = []
        self._call_history: list[dict[str, str | None]] = []

    def add_response(self, keyword: str, response: str) -> None:
        """Add a keyword-triggered response.

        When the prompt contains the keyword, this response is returned.

        Args:
            keyword: Keyword to match in prompt (case-insensitive).
            response: Response to return when keyword matches.
        """
        self._responses[keyword.lower()] = response

    def queue_response(self, response: str) -> None:
        """Queue a response to return on next generate() call.

        Queued responses take priority over keyword matches.

        Args:
            response: Response to return next.
        """
        self._response_queue.append(response)

    def get_call_history(self) -> list[dict[str, str | None]]:
        """Get history of all generate() calls.

        Returns:
            List of dicts with 'prompt' and 'system_prompt' keys.
        """
        return list(self._call_history)

    def clear_history(self) -> None:
        """Clear the call history."""
        self._call_history.clear()

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a mock response.

        Checks in order:
        1. Queued responses (FIFO)
        2. Keyword matches in prompt
        3. Deterministic fallback based on seed

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.

        Returns:
            Mock response string.
        """
        self._call_history.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
        })

        # Check queue first
        if self._response_queue:
            return self._response_queue.pop(0)

        # Check keyword matches
        prompt_lower = prompt.lower()
        for keyword, response in self._responses.items():
            if keyword in prompt_lower:
                return response

        # Deterministic fallback
        return self._generate_fallback(prompt)

    def _generate_fallback(self, prompt: str) -> str:
        """Generate a deterministic fallback response.

        Args:
            prompt: The prompt to base the response on.

        Returns:
            A deterministic response.
        """
        prompt_hash = self._hash_prompt(prompt, None)

        # Use seed + hash to select from canned responses
        seed_val = self.config.seed or 0
        hash_int = int(prompt_hash, 16)
        index = (seed_val + hash_int) % len(_FALLBACK_RESPONSES)

        return _FALLBACK_RESPONSES[index]


# Canned fallback responses for mock provider
_FALLBACK_RESPONSES = [
    "Thanks for reaching out! I'll get back to you soon.",
    "Got it, thanks!",
    "Sounds good to me!",
    "I'll look into this and let you know.",
    "Thanks for the message! I appreciate it.",
    "Understood. I'll follow up shortly.",
    "Great, thanks for letting me know!",
    "I'm on it!",
]


class ResponseNecessityChecker:
    """Determines if a message warrants a character response.

    Uses LLM to analyze whether a message requires a reply or if the
    conversation has naturally concluded. This prevents infinite reply
    chains and models realistic conversation patterns.

    Example:
        >>> checker = ResponseNecessityChecker(llm_provider)
        >>> needs_reply = await checker.check(
        ...     message_content="Sounds good, see you Saturday!",
        ...     conversation_context="...",
        ... )
        >>> print(needs_reply)  # ResponseDecision(needs_response=False, ...)
    """

    SYSTEM_PROMPT = """You are analyzing a message to determine if it requires a response.

Evaluate whether the message warrants a reply or if the conversation has naturally ended.

Messages that NEED a response:
- Questions requiring an answer
- Requests for information or action
- Initial outreach (invitations, proposals)
- Ongoing negotiation or discussion
- Messages that leave something unresolved

Messages that do NOT need a response:
- Simple acknowledgments ("Got it", "Thanks!")
- Final confirmations ("Sounds good, see you then!")
- Closing statements ("Looking forward to it!")
- Expressions of gratitude at conversation end
- One-word affirmatives that conclude a thread

Respond with exactly one of:
NEEDS_RESPONSE: <brief reason>
NO_RESPONSE: <brief reason>
"""

    def __init__(self, llm_provider: LLMProvider):
        """Initialize the checker.

        Args:
            llm_provider: LLM provider for analysis.
        """
        self.llm = llm_provider

    async def check(
        self,
        message_content: str,
        conversation_context: str | None = None,
        sender_name: str | None = None,
    ) -> "ResponseDecision":
        """Check if a message needs a response.

        Args:
            message_content: The message text to analyze.
            conversation_context: Optional prior conversation for context.
            sender_name: Optional name of who we'd be responding as.

        Returns:
            ResponseDecision indicating if response is needed.
        """
        prompt_parts = []

        if conversation_context:
            prompt_parts.append(f"Conversation so far:\n{conversation_context}\n")

        prompt_parts.append(f"Latest message to analyze:\n{message_content}")

        if sender_name:
            prompt_parts.append(f"\n(You would be responding as: {sender_name})")

        prompt = "\n".join(prompt_parts)

        try:
            result = await self.llm.generate(prompt, self.SYSTEM_PROMPT)
            return self._parse_result(result)
        except LLMError:
            # On error, default to needing a response (safer)
            return ResponseDecision(
                needs_response=True,
                reason="LLM check failed, defaulting to respond",
            )

    def _parse_result(self, result: str) -> "ResponseDecision":
        """Parse LLM output into ResponseDecision.

        Args:
            result: Raw LLM output.

        Returns:
            Parsed ResponseDecision.
        """
        result_upper = result.upper().strip()

        if result_upper.startswith("NO_RESPONSE"):
            reason = result.split(":", 1)[1].strip() if ":" in result else "No reason"
            return ResponseDecision(needs_response=False, reason=reason)
        elif result_upper.startswith("NEEDS_RESPONSE"):
            reason = result.split(":", 1)[1].strip() if ":" in result else "No reason"
            return ResponseDecision(needs_response=True, reason=reason)
        else:
            # Ambiguous result, default to responding
            return ResponseDecision(
                needs_response=True,
                reason=f"Ambiguous LLM output: {result[:50]}...",
            )


@dataclass
class ResponseDecision:
    """Result of response necessity check.

    Attributes:
        needs_response: Whether the message warrants a reply.
        reason: Brief explanation of the decision.
    """

    needs_response: bool
    reason: str
