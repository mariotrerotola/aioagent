"""Base agent class."""

from __future__ import annotations

import asyncio
import logging
from typing import Self

from .behaviours import Behaviour
from .bus import MessageBus, get_default_bus
from .template import MessageTemplate

logger = logging.getLogger(__name__)

_STOP_TIMEOUT = 5.0  # seconds to wait for behaviours during stop()


class BaseAgent:
    """Minimal autonomous agent that hosts behaviours on an event loop.

    Subclass and override :meth:`setup` to register behaviours::

        class MyAgent(BaseAgent):
            async def setup(self):
                self.add_behaviour(MyCyclicBehaviour())
    """

    def __init__(self, jid: str, *, bus: MessageBus | None = None) -> None:
        self._jid = jid
        self._bus = bus or get_default_bus()
        self._behaviours: list[tuple[Behaviour, asyncio.Task[None] | None]] = []
        self._alive = False

    # -- properties ----------------------------------------------------

    @property
    def jid(self) -> str:
        """Agent identifier (analogous to a JID in XMPP)."""
        return self._jid

    @property
    def is_alive(self) -> bool:
        """``True`` while the agent is running."""
        return self._alive

    @property
    def bus(self) -> MessageBus:
        return self._bus

    # -- lifecycle -----------------------------------------------------

    async def setup(self) -> None:
        """Override to add behaviours and perform initialization."""

    async def start(self) -> None:
        """Register on the bus, call :meth:`setup`, and launch behaviours."""
        self._bus.register(self._jid)
        self._alive = True
        logger.info("Agent %s started", self._jid)
        await self.setup()
        # Start any behaviours that were added during setup.
        for behaviour, task in self._behaviours:
            if task is None:
                self._start_behaviour(behaviour)

    async def stop(self, *, timeout: float = _STOP_TIMEOUT) -> None:
        """Cancel all behaviours and unregister from the bus.

        Args:
            timeout: Maximum seconds to wait for behaviours to finish.
                If exceeded, a warning is logged but the agent still stops.
        """
        for behaviour, task in self._behaviours:
            behaviour.kill()
        # Wait for all tasks to finish (cancellation propagation).
        tasks = [t for _, t in self._behaviours if t is not None]
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "Agent %s: some behaviours did not stop within %.1fs",
                    self._jid,
                    timeout,
                )
        self._alive = False
        self._bus.unregister(self._jid)
        logger.info("Agent %s stopped", self._jid)

    # -- behaviour management ------------------------------------------

    def add_behaviour(
        self,
        behaviour: Behaviour,
        template: MessageTemplate | None = None,
    ) -> None:
        """Attach a behaviour to this agent.

        If the agent is already running the behaviour is started immediately.
        """
        behaviour._bind(self, self._bus, template)
        if self._alive:
            task = behaviour._start_task()
            self._behaviours.append((behaviour, task))
        else:
            self._behaviours.append((behaviour, None))

    def _start_behaviour(self, behaviour: Behaviour) -> asyncio.Task[None]:
        task = behaviour._start_task()
        # Update the stored tuple.
        for i, (b, _) in enumerate(self._behaviours):
            if b is behaviour:
                self._behaviours[i] = (b, task)
                break
        return task

    # -- async context manager -----------------------------------------

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    def __repr__(self) -> str:
        status = "alive" if self._alive else "stopped"
        return f"<{type(self).__name__} jid={self._jid!r} {status}>"
