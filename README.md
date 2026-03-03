# aioagent

[![PyPI](https://img.shields.io/pypi/v/aioagent)](https://pypi.org/project/aioagent/)
[![Python](https://img.shields.io/pypi/pyversions/aioagent)](https://pypi.org/project/aioagent/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/mariotrerotola/aioagent/actions/workflows/ci.yml/badge.svg)](https://github.com/mariotrerotola/aioagent/actions)

**Lightweight async multi-agent framework for Python.**

Build multi-agent systems using pure `asyncio` — no external infrastructure, no XMPP servers, no heavy dependencies.

## Why aioagent?

|                        | SPADE               | aioagent              |
|------------------------|----------------------|----------------------|
| Infrastructure         | XMPP server (Prosody)| None                 |
| Deploy                 | Complex              | Single process       |
| Distributed agents     | Yes                  | No (in-process)      |
| Dependencies           | slixmpp, aioxmpp     | stdlib only          |
| Best for               | Distributed systems  | Simulations, pipelines, prototypes |

## Installation

```bash
pip install aioagent
```

## Quick start

```python
import asyncio
from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, MessageBus


class PingBehaviour(CyclicBehaviour):
    async def run(self):
        await self.send(AgentMessage(to="pong", body="ping"))
        reply = await self.receive(timeout=2.0)
        if reply:
            print(f"Got: {reply.body}")
        self.kill()


class PongBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=2.0)
        if msg:
            await self.send(msg.make_reply(body="pong"))
            self.kill()


class PingAgent(BaseAgent):
    async def setup(self):
        self.add_behaviour(PingBehaviour())


class PongAgent(BaseAgent):
    async def setup(self):
        self.add_behaviour(PongBehaviour())


async def main():
    bus = MessageBus()
    async with PongAgent("pong", bus=bus), PingAgent("ping", bus=bus):
        await asyncio.sleep(1)


asyncio.run(main())
```

## Core concepts

### Agents

Subclass `BaseAgent` and override `setup()` to register behaviours:

```python
class MyAgent(BaseAgent):
    async def setup(self):
        self.add_behaviour(MyBehaviour())
```

Agents support `async with` for automatic start/stop.

### Behaviours

| Class                | Description                          |
|----------------------|--------------------------------------|
| `OneShotBehaviour`   | Runs `run()` once and stops          |
| `CyclicBehaviour`    | Runs `run()` in a loop until killed  |
| `PeriodicBehaviour`  | Runs `run()` every N seconds         |
| `FSMBehaviour`       | Finite-state machine with transitions |

Each behaviour has `on_start()` and `on_end()` lifecycle hooks.

### FSMBehaviour

Model complex protocols as state machines:

```python
from aioagent import FSMBehaviour

class NegotiationFSM(FSMBehaviour):
    async def setup_fsm(self):
        self.add_state("PROPOSE", self.propose, initial=True)
        self.add_state("EVALUATE", self.evaluate)
        self.add_state("DONE", self.finish, final=True)
        self.add_transition("PROPOSE", "EVALUATE")
        self.add_transition("EVALUATE", "PROPOSE")
        self.add_transition("EVALUATE", "DONE")

    async def propose(self):
        # ... send proposal ...
        self.set_next_state("EVALUATE")

    async def evaluate(self):
        # ... check reply ...
        self.set_next_state("DONE")

    async def finish(self):
        pass
```

### Messages

```python
msg = AgentMessage(
    to="recipient",
    body="hello",
    performative="INFORM",      # FIPA-style (optional)
    metadata={"protocol": "cnp", "priority": 1},
    thread="conversation-1",
)
reply = msg.make_reply(body="acknowledged")
```

### Interaction patterns

Convenience functions for common FIPA performatives:

```python
from aioagent import request, agree, refuse, inform

msg = request("worker", body="compute fibonacci(10)")
await self.send(msg)

reply = await self.receive(timeout=5.0)
# reply with: agree(msg, body="ok") or refuse(msg, body="busy")
```

### Templates

Filter incoming messages by sender, performative, or metadata:

```python
from aioagent import MessageTemplate

template = MessageTemplate(sender="agent_a", performative="REQUEST")
agent.add_behaviour(handler, template=template)
```

### MessageBus

The bus routes messages between agents via per-agent `asyncio.Queue` instances:

```python
bus = MessageBus()
agent_a = BaseAgent("a", bus=bus)
agent_b = BaseAgent("b", bus=bus)

# Broadcast to all agents
msg = AgentMessage(to="", sender="coordinator", body="start")
await bus.broadcast(msg, exclude="coordinator")
```

### Custom exceptions

All framework errors inherit from `AioagentError`:

```python
from aioagent import AgentNotFoundError, AgentAlreadyRegisteredError, BehaviourNotBoundError
```

## Examples

See the [`examples/`](examples/) directory:

- **[ping_pong.py](examples/ping_pong.py)** — Basic message exchange
- **[fsm_negotiation.py](examples/fsm_negotiation.py)** — Price negotiation with FSM
- **[broadcast.py](examples/broadcast.py)** — Coordinator notifies all workers
- **[pipeline.py](examples/pipeline.py)** — Data processing pipeline
- **[request_reply.py](examples/request_reply.py)** — Request/reply with agree/refuse

## Development

```bash
git clone https://github.com/mariotrerotola/aioagent.git
cd aioagent
pip install -e ".[dev]"
pytest
pytest --cov=aioagent          # with coverage
mypy src/aioagent/             # type checking
ruff check src/ tests/         # linting
```

## License

[MIT](LICENSE)
