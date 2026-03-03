"""Common interaction patterns for agent communication."""

from __future__ import annotations

import uuid

from .message import AgentMessage


def request(
    to: str,
    body: str = "",
    *,
    thread: str | None = None,
    **metadata: str,
) -> AgentMessage:
    """Create a REQUEST message with an auto-generated thread id.

    Example::

        msg = request("worker", body="compute 42", priority="high")
        await self.send(msg)
        reply = await self.receive(timeout=5.0)
    """
    return AgentMessage(
        to=to,
        body=body,
        performative="REQUEST",
        thread=thread or uuid.uuid4().hex,
        metadata=dict(metadata),
    )


def inform(
    to: str,
    body: str = "",
    *,
    thread: str | None = None,
    **metadata: str,
) -> AgentMessage:
    """Create an INFORM message."""
    return AgentMessage(
        to=to,
        body=body,
        performative="INFORM",
        thread=thread or uuid.uuid4().hex,
        metadata=dict(metadata),
    )


def agree(original: AgentMessage, body: str = "") -> AgentMessage:
    """Reply to a request with an AGREE performative."""
    return original.make_reply(body=body, performative="AGREE")


def refuse(original: AgentMessage, body: str = "") -> AgentMessage:
    """Reply to a request with a REFUSE performative."""
    return original.make_reply(body=body, performative="REFUSE")
