"""Tests for custom exceptions."""

from aioagent import AgentAlreadyRegisteredError, AgentNotFoundError, AioagentError, BehaviourNotBoundError


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        assert issubclass(AgentNotFoundError, AioagentError)
        assert issubclass(AgentAlreadyRegisteredError, AioagentError)
        assert issubclass(BehaviourNotBoundError, AioagentError)

    def test_base_inherits_from_exception(self):
        assert issubclass(AioagentError, Exception)


class TestAgentNotFoundError:
    def test_message(self):
        err = AgentNotFoundError("bob")
        assert "bob" in str(err)
        assert err.agent_id == "bob"


class TestAgentAlreadyRegisteredError:
    def test_message(self):
        err = AgentAlreadyRegisteredError("bob")
        assert "bob" in str(err)
        assert err.agent_id == "bob"


class TestBehaviourNotBoundError:
    def test_message(self):
        err = BehaviourNotBoundError()
        assert "not bound" in str(err)
