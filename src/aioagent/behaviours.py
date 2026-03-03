"""Behaviour building blocks for agents."""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import TYPE_CHECKING

from .exceptions import BehaviourNotBoundError
from .message import AgentMessage
from .template import MessageTemplate

if TYPE_CHECKING:
    from .agent import BaseAgent
    from .bus import MessageBus

logger = logging.getLogger(__name__)


class Behaviour(abc.ABC):
    """Base class for all behaviours.

    A behaviour encapsulates a unit of work that an agent performs.
    Subclasses must implement :meth:`run`.
    """

    def __init__(self) -> None:
        self._agent: BaseAgent | None = None
        self._bus: MessageBus | None = None
        self._template: MessageTemplate | None = None
        self._task: asyncio.Task[None] | None = None
        self._done_flag = False

    # -- wiring (called by BaseAgent.add_behaviour) --------------------

    def _bind(
        self,
        agent: BaseAgent,
        bus: MessageBus,
        template: MessageTemplate | None = None,
    ) -> None:
        self._agent = agent
        self._bus = bus
        self._template = template

    # -- public API ----------------------------------------------------

    @property
    def agent(self) -> BaseAgent:
        """The agent that owns this behaviour."""
        if self._agent is None:
            raise BehaviourNotBoundError
        return self._agent

    @abc.abstractmethod
    async def run(self) -> None:
        """Execute the behaviour's logic.  Implement in subclasses."""

    async def on_start(self) -> None:
        """Hook called once before the first :meth:`run` invocation."""

    async def on_end(self) -> None:
        """Hook called after the behaviour finishes (or is killed)."""

    def done(self) -> bool:
        """Return ``True`` if the behaviour has completed."""
        return self._done_flag

    def kill(self) -> None:
        """Cancel the underlying task."""
        if self._task is not None and not self._task.done():
            self._task.cancel()

    # -- messaging shortcuts -------------------------------------------

    async def send(self, msg: AgentMessage) -> None:
        """Send *msg*, automatically filling in the sender field."""
        if self._bus is None:
            raise BehaviourNotBoundError
        msg.sender = self.agent.jid
        await self._bus.send(msg)

    async def receive(self, timeout: float | None = None) -> AgentMessage | None:
        """Receive the next message, optionally filtered by the template.

        If a :class:`MessageTemplate` is associated with this behaviour,
        non-matching messages are re-queued and the wait continues until
        *timeout* expires.
        """
        if self._bus is None:
            raise BehaviourNotBoundError
        if self._template is None:
            return await self._bus.receive(self.agent.jid, timeout=timeout)

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout if timeout is not None else None
        requeued: list[AgentMessage] = []
        try:
            while True:
                remaining = None
                if deadline is not None:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        return None
                msg = await self._bus.receive(self.agent.jid, timeout=remaining)
                if msg is None:
                    return None
                if self._template.match(msg):
                    return msg
                requeued.append(msg)
        finally:
            # Re-queue messages that did not match the template so other
            # behaviours (or a future receive) can still consume them.
            for m in requeued:
                await self._bus.send(
                    AgentMessage(
                        to=self.agent.jid,
                        sender=m.sender,
                        body=m.body,
                        metadata=m.metadata,
                        thread=m.thread,
                        performative=m.performative,
                    )
                )

    # -- internal scheduling -------------------------------------------

    async def _execute(self) -> None:
        """Wrapper executed as an :class:`asyncio.Task`."""
        try:
            await self.on_start()
            await self._run_loop()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Behaviour %s raised an exception", type(self).__name__)
        finally:
            self._done_flag = True
            try:
                await self.on_end()
            except Exception:
                logger.exception("on_end() of %s raised an exception", type(self).__name__)

    @abc.abstractmethod
    async def _run_loop(self) -> None:
        """Internal loop strategy — implemented by concrete subclasses."""

    def _start_task(self) -> asyncio.Task[None]:
        self._task = asyncio.create_task(self._execute(), name=type(self).__name__)
        return self._task


class OneShotBehaviour(Behaviour):
    """A behaviour that runs its :meth:`run` method exactly once."""

    async def _run_loop(self) -> None:
        await self.run()


class CyclicBehaviour(Behaviour):
    """A behaviour that runs :meth:`run` in a loop until killed."""

    async def _run_loop(self) -> None:
        while True:
            await self.run()
            # Yield control to prevent a tight loop from starving other tasks.
            await asyncio.sleep(0)


class PeriodicBehaviour(Behaviour):
    """A behaviour that runs :meth:`run` at a fixed interval.

    Args:
        period: Interval in seconds between successive invocations.
    """

    def __init__(self, period: float) -> None:
        super().__init__()
        if period <= 0:
            raise ValueError("period must be positive")
        self.period = period

    async def _run_loop(self) -> None:
        while True:
            await self.run()
            await asyncio.sleep(self.period)


class FSMBehaviour(Behaviour):
    """Finite-state-machine behaviour.

    Register state handlers with :meth:`add_state` and transitions with
    :meth:`add_transition`.  The machine starts from *initial_state* and
    runs until it reaches a final state or is killed.

    Example::

        class NegotiationFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("PROPOSE", self.propose, initial=True)
                self.add_state("EVALUATE", self.evaluate)
                self.add_state("DONE", self.done_state, final=True)
                self.add_transition("PROPOSE", "EVALUATE")
                self.add_transition("EVALUATE", "PROPOSE")
                self.add_transition("EVALUATE", "DONE")

            async def propose(self):
                ...
                self.set_next_state("EVALUATE")

            async def evaluate(self):
                ...
                self.set_next_state("DONE")

            async def done_state(self):
                pass
    """

    def __init__(self) -> None:
        super().__init__()
        self._states: dict[str, _StateEntry] = {}
        self._transitions: dict[str, set[str]] = {}
        self._initial_state: str | None = None
        self._current_state: str | None = None
        self._next_state: str | None = None

    # -- FSM setup API -------------------------------------------------

    async def setup_fsm(self) -> None:
        """Override to register states and transitions."""

    def add_state(
        self,
        name: str,
        handler: _StateHandler,
        *,
        initial: bool = False,
        final: bool = False,
    ) -> None:
        """Register a state with its async handler function.

        Args:
            name: Unique state name.
            handler: Async callable invoked when the machine enters this state.
            initial: Mark as the starting state (exactly one required).
            final: Mark as a terminal state (machine stops when reached).
        """
        self._states[name] = _StateEntry(handler=handler, final=final)
        self._transitions.setdefault(name, set())
        if initial:
            if self._initial_state is not None:
                raise ValueError(
                    f"Duplicate initial state: {self._initial_state!r} and {name!r}"
                )
            self._initial_state = name

    def add_transition(self, source: str, dest: str) -> None:
        """Allow a transition from *source* to *dest*."""
        self._transitions.setdefault(source, set()).add(dest)

    def set_next_state(self, state: str) -> None:
        """Set the state the machine should move to after the current handler returns."""
        self._next_state = state

    @property
    def current_state(self) -> str | None:
        """The state currently being executed (or last executed)."""
        return self._current_state

    # -- internal ------------------------------------------------------

    async def run(self) -> None:
        # Not used directly — _run_loop drives the FSM.
        pass  # pragma: no cover

    async def _run_loop(self) -> None:
        await self.setup_fsm()
        if self._initial_state is None:
            raise ValueError("No initial state defined — call add_state(..., initial=True)")

        self._current_state = self._initial_state
        while self._current_state is not None:
            entry = self._states.get(self._current_state)
            if entry is None:
                raise ValueError(f"Unknown state {self._current_state!r}")

            self._next_state = None
            await entry.handler()

            if entry.final:
                break

            if self._next_state is None:
                raise ValueError(
                    f"State {self._current_state!r} did not call set_next_state()"
                )

            allowed = self._transitions.get(self._current_state, set())
            if self._next_state not in allowed:
                raise ValueError(
                    f"Transition {self._current_state!r} -> {self._next_state!r} is not allowed"
                )

            self._current_state = self._next_state
            await asyncio.sleep(0)


# -- helpers for FSMBehaviour -------------------------------------------------

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

_StateHandler = Callable[[], Coroutine[Any, Any, None]]


@dataclass(slots=True)
class _StateEntry:
    handler: _StateHandler
    final: bool = False
