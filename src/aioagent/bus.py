"""In-process message bus for agent communication."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .exceptions import AgentAlreadyRegisteredError, AgentNotFoundError

if TYPE_CHECKING:
    from .message import AgentMessage

logger = logging.getLogger(__name__)

# Module-level default bus instance (lazy-initialized).
_default_bus: MessageBus | None = None


class MessageBus:
    """Asynchronous message router.

    Each registered agent gets its own :class:`asyncio.Queue`.  Sending a
    message places it in the recipient's queue; receiving pops from the
    caller's queue.

    A single *default* bus is shared across the process unless an explicit
    bus is passed to agents.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent_id: str) -> None:
        """Create a mailbox for *agent_id*.

        Raises :class:`AgentAlreadyRegisteredError` if the agent is already registered.
        """
        if agent_id in self._queues:
            raise AgentAlreadyRegisteredError(agent_id)
        self._queues[agent_id] = asyncio.Queue()
        logger.debug("Registered agent %s", agent_id)

    def unregister(self, agent_id: str) -> None:
        """Remove the mailbox for *agent_id*."""
        self._queues.pop(agent_id, None)
        logger.debug("Unregistered agent %s", agent_id)

    def is_registered(self, agent_id: str) -> bool:
        """Return ``True`` if *agent_id* has a mailbox."""
        return agent_id in self._queues

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def send(self, msg: AgentMessage) -> None:
        """Deliver *msg* to the recipient's queue.

        Raises :class:`AgentNotFoundError` if the recipient is not registered.
        """
        queue = self._queues.get(msg.to)
        if queue is None:
            raise AgentNotFoundError(msg.to)
        await queue.put(msg)
        logger.debug("Delivered message from %s to %s", msg.sender, msg.to)

    async def broadcast(
        self,
        msg: AgentMessage,
        *,
        exclude: str | set[str] | None = None,
    ) -> int:
        """Send a copy of *msg* to every registered agent.

        Args:
            msg: The message to broadcast.  Each copy's ``to`` field is set
                to the recipient's id.
            exclude: Agent id(s) to skip (typically the sender).

        Returns:
            Number of agents the message was delivered to.
        """
        from .message import AgentMessage as Msg  # avoid circular at module level

        if isinstance(exclude, str):
            exclude = {exclude}
        skip = exclude or set()

        count = 0
        for agent_id, queue in self._queues.items():
            if agent_id in skip:
                continue
            copy = Msg(
                to=agent_id,
                sender=msg.sender,
                body=msg.body,
                metadata=dict(msg.metadata),
                thread=msg.thread,
                performative=msg.performative,
            )
            await queue.put(copy)
            count += 1
        logger.debug("Broadcast from %s delivered to %d agents", msg.sender, count)
        return count

    async def receive(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> AgentMessage | None:
        """Pop the next message for *agent_id*.

        Returns ``None`` if *timeout* elapses without a message.

        Raises :class:`AgentNotFoundError` if the agent is not registered.
        """
        queue = self._queues.get(agent_id)
        if queue is None:
            raise AgentNotFoundError(agent_id)
        try:
            if timeout is not None:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            return await queue.get()
        except TimeoutError:
            return None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def agents(self) -> list[str]:
        """List of currently registered agent identifiers."""
        return list(self._queues)

    def pending(self, agent_id: str) -> int:
        """Number of queued messages for *agent_id*."""
        queue = self._queues.get(agent_id)
        return queue.qsize() if queue is not None else 0


def get_default_bus() -> MessageBus:
    """Return the process-wide default :class:`MessageBus`, creating it if needed."""
    global _default_bus
    if _default_bus is None:
        _default_bus = MessageBus()
    return _default_bus
