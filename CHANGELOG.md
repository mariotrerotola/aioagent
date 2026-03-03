# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-03-03

### Added
- `BaseAgent` with async lifecycle (`start`, `stop`, `setup`, context manager)
- `CyclicBehaviour`, `OneShotBehaviour`, `PeriodicBehaviour`
- `FSMBehaviour` for finite-state-machine agents
- `AgentMessage` dataclass with FIPA-style performatives and thread support
- `MessageTemplate` for filtering incoming messages
- `MessageBus` with per-agent queues and broadcast support
- `request`, `inform`, `agree`, `refuse` pattern helpers
- Custom exceptions: `AgentNotFoundError`, `AgentAlreadyRegisteredError`, `BehaviourNotBoundError`
- `py.typed` marker for PEP 561 compliance
- Examples: ping-pong, FSM negotiation, broadcast, pipeline, request/reply
- GitHub Actions CI with Python 3.11/3.12/3.13
