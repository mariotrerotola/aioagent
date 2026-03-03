"""Message template for filtering incoming messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .message import AgentMessage


@dataclass(frozen=True)
class MessageTemplate:
    """Filter that matches incoming messages by sender, performative, or metadata.

    All specified fields must match for the template to accept a message.
    Unset fields (``None`` / empty) are ignored during matching.

    Example::

        template = MessageTemplate(sender="agent_a", performative="REQUEST")
        template.match(msg)  # True only if msg.sender == "agent_a" AND
                              #   msg.performative == "REQUEST"
    """

    sender: str | None = None
    performative: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def match(self, msg: AgentMessage) -> bool:
        """Return ``True`` if *msg* satisfies all template constraints."""
        if self.sender is not None and msg.sender != self.sender:
            return False
        if self.performative is not None and msg.performative != self.performative:
            return False
        for key, value in self.metadata.items():
            if msg.metadata.get(key) != value:
                return False
        return True
