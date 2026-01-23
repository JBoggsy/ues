"""A2A messaging utilities for communicating with purple agents.

This module provides helpers for sending messages to other A2A agents
and managing conversation context across multiple exchanges.
"""

import json
from uuid import uuid4

import httpx
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
    Consumer,
)
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    DataPart,
)


DEFAULT_TIMEOUT = 300  # 5 minutes


def create_message(
    *,
    role: Role = Role.user,
    text: str,
    context_id: str | None = None,
) -> Message:
    """Create an A2A message.

    Args:
        role: The role of the message sender.
        text: The text content of the message.
        context_id: Optional context ID for conversation continuity.

    Returns:
        A new Message object.
    """
    return Message(
        kind="message",
        role=role,
        parts=[Part(root=TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
        context_id=context_id,
    )


def merge_parts(parts: list[Part]) -> str:
    """Merge message parts into a single string.

    Args:
        parts: List of message parts.

    Returns:
        Combined string representation of all parts.
    """
    chunks = []
    for part in parts:
        if isinstance(part.root, TextPart):
            chunks.append(part.root.text)
        elif isinstance(part.root, DataPart):
            chunks.append(json.dumps(part.root.data, indent=2))
    return "\n".join(chunks)


async def send_message(
    message: str,
    base_url: str,
    context_id: str | None = None,
    streaming: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    consumer: Consumer | None = None,
) -> dict:
    """Send a message to an A2A agent and get the response.

    Args:
        message: The message text to send.
        base_url: The agent's base URL.
        context_id: Optional context ID for conversation continuity.
        streaming: Whether to use streaming mode.
        timeout: Request timeout in seconds.
        consumer: Optional event consumer for streaming.

    Returns:
        Dict with context_id, response text, and status (if available).
    """
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=streaming,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        if consumer:
            await client.add_event_consumer(consumer)

        outbound_msg = create_message(text=message, context_id=context_id)
        last_event = None
        outputs: dict = {"response": "", "context_id": None}

        async for event in client.send_message(outbound_msg):
            last_event = event

        match last_event:
            case Message() as msg:
                outputs["context_id"] = msg.context_id
                outputs["response"] += merge_parts(msg.parts)

            case (task, _update):
                outputs["context_id"] = task.context_id
                outputs["status"] = task.status.state.value
                msg = task.status.message
                if msg:
                    outputs["response"] += merge_parts(msg.parts)
                if task.artifacts:
                    for artifact in task.artifacts:
                        outputs["response"] += merge_parts(artifact.parts)

            case _:
                pass

        return outputs


class Messenger:
    """Manages A2A communication with other agents.

    Maintains conversation context across multiple message exchanges
    with the same agent.
    """

    def __init__(self):
        """Initialize with empty context ID registry."""
        self._context_ids: dict[str, str | None] = {}

    async def talk_to_agent(
        self,
        message: str,
        url: str,
        new_conversation: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """Send a message to another agent and get their response.

        Args:
            message: The message to send.
            url: The agent's URL endpoint.
            new_conversation: If True, start fresh; if False, continue existing.
            timeout: Timeout in seconds (default: 300).

        Returns:
            The agent's response message.

        Raises:
            RuntimeError: If the agent responds with a non-completed status.
        """
        outputs = await send_message(
            message=message,
            base_url=url,
            context_id=None if new_conversation else self._context_ids.get(url),
            timeout=timeout,
        )

        if outputs.get("status", "completed") != "completed":
            raise RuntimeError(f"{url} responded with: {outputs}")

        self._context_ids[url] = outputs.get("context_id")
        return outputs["response"]

    def reset(self):
        """Clear all conversation contexts."""
        self._context_ids = {}
