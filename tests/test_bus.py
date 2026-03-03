"""Tests for MessageBus."""

import asyncio

import pytest

from aioagent import AgentAlreadyRegisteredError, AgentMessage, AgentNotFoundError, MessageBus


@pytest.fixture
def bus():
    return MessageBus()


class TestRegistration:
    def test_register_and_unregister(self, bus: MessageBus):
        bus.register("a")
        assert bus.is_registered("a")
        bus.unregister("a")
        assert not bus.is_registered("a")

    def test_double_register_raises(self, bus: MessageBus):
        bus.register("a")
        with pytest.raises(AgentAlreadyRegisteredError):
            bus.register("a")

    def test_unregister_unknown_is_noop(self, bus: MessageBus):
        bus.unregister("nonexistent")

    def test_agents_list(self, bus: MessageBus):
        bus.register("a")
        bus.register("b")
        assert sorted(bus.agents) == ["a", "b"]

    def test_agents_list_empty(self, bus: MessageBus):
        assert bus.agents == []


class TestSendReceive:
    @pytest.mark.asyncio
    async def test_send_and_receive(self, bus: MessageBus):
        bus.register("bob")
        msg = AgentMessage(to="bob", sender="alice", body="hi")
        await bus.send(msg)
        received = await bus.receive("bob", timeout=1.0)
        assert received is not None
        assert received.body == "hi"
        assert received.sender == "alice"

    @pytest.mark.asyncio
    async def test_fifo_ordering(self, bus: MessageBus):
        bus.register("bob")
        for i in range(5):
            await bus.send(AgentMessage(to="bob", sender="alice", body=str(i)))
        for i in range(5):
            msg = await bus.receive("bob", timeout=0.1)
            assert msg is not None
            assert msg.body == str(i)

    @pytest.mark.asyncio
    async def test_send_to_unknown_raises(self, bus: MessageBus):
        with pytest.raises(AgentNotFoundError):
            await bus.send(AgentMessage(to="nobody", sender="alice"))

    @pytest.mark.asyncio
    async def test_receive_from_unknown_raises(self, bus: MessageBus):
        with pytest.raises(AgentNotFoundError):
            await bus.receive("nobody")

    @pytest.mark.asyncio
    async def test_receive_timeout(self, bus: MessageBus):
        bus.register("bob")
        result = await bus.receive("bob", timeout=0.05)
        assert result is None

    @pytest.mark.asyncio
    async def test_receive_timeout_zero(self, bus: MessageBus):
        bus.register("bob")
        result = await bus.receive("bob", timeout=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_send_to_self(self, bus: MessageBus):
        bus.register("alice")
        await bus.send(AgentMessage(to="alice", sender="alice", body="self"))
        msg = await bus.receive("alice", timeout=0.1)
        assert msg is not None
        assert msg.body == "self"

    def test_pending_count(self, bus: MessageBus):
        bus.register("a")
        assert bus.pending("a") == 0
        assert bus.pending("unknown") == 0

    @pytest.mark.asyncio
    async def test_pending_after_send(self, bus: MessageBus):
        bus.register("bob")
        await bus.send(AgentMessage(to="bob", sender="alice", body="1"))
        await bus.send(AgentMessage(to="bob", sender="alice", body="2"))
        assert bus.pending("bob") == 2


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, bus: MessageBus):
        bus.register("a")
        bus.register("b")
        bus.register("c")
        msg = AgentMessage(to="", sender="sender", body="hello")
        count = await bus.broadcast(msg)
        assert count == 3
        for agent_id in ("a", "b", "c"):
            received = await bus.receive(agent_id, timeout=0.1)
            assert received is not None
            assert received.body == "hello"
            assert received.to == agent_id

    @pytest.mark.asyncio
    async def test_broadcast_exclude_string(self, bus: MessageBus):
        bus.register("a")
        bus.register("b")
        msg = AgentMessage(to="", sender="a", body="hi")
        count = await bus.broadcast(msg, exclude="a")
        assert count == 1
        assert bus.pending("a") == 0
        assert bus.pending("b") == 1

    @pytest.mark.asyncio
    async def test_broadcast_exclude_set(self, bus: MessageBus):
        bus.register("a")
        bus.register("b")
        bus.register("c")
        msg = AgentMessage(to="", sender="a", body="hi")
        count = await bus.broadcast(msg, exclude={"a", "b"})
        assert count == 1
        assert bus.pending("c") == 1

    @pytest.mark.asyncio
    async def test_broadcast_empty_bus(self, bus: MessageBus):
        msg = AgentMessage(to="", sender="x", body="hi")
        count = await bus.broadcast(msg)
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_metadata_isolation(self, bus: MessageBus):
        bus.register("a")
        bus.register("b")
        msg = AgentMessage(to="", sender="x", body="hi", metadata={"k": "v"})
        await bus.broadcast(msg)
        m1 = await bus.receive("a", timeout=0.1)
        m2 = await bus.receive("b", timeout=0.1)
        assert m1 is not None and m2 is not None
        m1.metadata["new"] = "val"
        assert "new" not in m2.metadata


class TestBusIsolation:
    @pytest.mark.asyncio
    async def test_separate_buses_do_not_crosspollinate(self):
        bus1 = MessageBus()
        bus2 = MessageBus()
        bus1.register("a")
        bus2.register("a")
        await bus1.send(AgentMessage(to="a", sender="x", body="bus1"))
        result = await bus2.receive("a", timeout=0.05)
        assert result is None
        result = await bus1.receive("a", timeout=0.05)
        assert result is not None
        assert result.body == "bus1"
