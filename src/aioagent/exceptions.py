"""Custom exceptions for the aioagent framework."""


class AioagentError(Exception):
    """Base exception for all aioagent errors."""


class AgentNotFoundError(AioagentError):
    """Raised when a message is sent to an unregistered agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent {agent_id!r} is not registered on this bus")


class AgentAlreadyRegisteredError(AioagentError):
    """Raised when registering an agent that already exists on the bus."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent {agent_id!r} is already registered on this bus")


class BehaviourNotBoundError(AioagentError):
    """Raised when accessing agent/bus on a behaviour that hasn't been bound."""

    def __init__(self) -> None:
        super().__init__("Behaviour is not bound to an agent — call add_behaviour() first")
