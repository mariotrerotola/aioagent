"""aioagent — Lightweight async multi-agent framework for Python."""

from .agent import BaseAgent
from .behaviours import (
    Behaviour,
    CyclicBehaviour,
    FSMBehaviour,
    OneShotBehaviour,
    PeriodicBehaviour,
)
from .bus import MessageBus, get_default_bus
from .exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
    AioagentError,
    BehaviourNotBoundError,
)
from .message import AgentMessage
from .patterns import agree, inform, refuse, request
from .template import MessageTemplate

__all__ = [
    "AgentAlreadyRegisteredError",
    "AgentMessage",
    "AgentNotFoundError",
    "AioagentError",
    "BaseAgent",
    "Behaviour",
    "BehaviourNotBoundError",
    "CyclicBehaviour",
    "FSMBehaviour",
    "MessageBus",
    "MessageTemplate",
    "OneShotBehaviour",
    "PeriodicBehaviour",
    "agree",
    "get_default_bus",
    "inform",
    "refuse",
    "request",
]

__version__ = "0.1.0"
