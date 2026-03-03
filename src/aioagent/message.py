"""Agent message type for inter-agent communication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMessage:
    """A message exchanged between agents.

    Attributes:
        to: Recipient agent identifier.
        sender: Sender agent identifier (set automatically by the framework).
        body: Message payload as a string.
        metadata: Arbitrary key-value pairs attached to the message.
        thread: Optional conversation thread identifier.
        performative: Optional FIPA-style performative
            (INFORM, REQUEST, AGREE, REFUSE, etc.).
    """

    to: str
    sender: str = ""
    body: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    thread: str | None = None
    performative: str | None = None

    def make_reply(self, *, body: str = "", performative: str | None = None) -> AgentMessage:
        """Create a reply to this message, swapping sender and recipient."""
        return AgentMessage(
            to=self.sender,
            sender=self.to,
            body=body,
            metadata=dict(self.metadata),
            thread=self.thread or uuid.uuid4().hex,
            performative=performative or self.performative,
        )

    def __repr__(self) -> str:
        parts = [f"to={self.to!r}", f"sender={self.sender!r}"]
        if self.body:
            preview = self.body[:40] + ("..." if len(self.body) > 40 else "")
            parts.append(f"body={preview!r}")
        if self.performative:
            parts.append(f"performative={self.performative!r}")
        if self.thread:
            parts.append(f"thread={self.thread!r}")
        return f"AgentMessage({', '.join(parts)})"
