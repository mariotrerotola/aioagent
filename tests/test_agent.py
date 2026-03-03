"""Tests for BaseAgent."""

import asyncio

import pytest

from aioagent import AgentAlreadyRegisteredError, BaseAgent, CyclicBehaviour, MessageBus, OneShotBehaviour


@pytest.fixture
def bus():
    return MessageBus()


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_start_stop(self, bus: MessageBus):
        agent = BaseAgent("a", bus=bus)
        assert not agent.is_alive
        await agent.start()
        assert agent.is_alive
        assert bus.is_registered("a")
        await agent.stop()
        assert not agent.is_alive
        assert not bus.is_registered("a")

    @pytest.mark.asyncio
    async def test_context_manager(self, bus: MessageBus):
        async with BaseAgent("a", bus=bus) as agent:
            assert agent.is_alive
        assert not agent.is_alive

    @pytest.mark.asyncio
    async def test_setup_called(self, bus: MessageBus):
        setup_called = {"v": False}

        class MyAgent(BaseAgent):
            async def setup(self):
                setup_called["v"] = True

        async with MyAgent("a", bus=bus):
            pass
        assert setup_called["v"]

    def test_jid_property(self, bus: MessageBus):
        agent = BaseAgent("test_id", bus=bus)
        assert agent.jid == "test_id"

    def test_repr(self, bus: MessageBus):
        agent = BaseAgent("a", bus=bus)
        assert "stopped" in repr(agent)

    @pytest.mark.asyncio
    async def test_repr_alive(self, bus: MessageBus):
        async with BaseAgent("a", bus=bus) as agent:
            assert "alive" in repr(agent)

    @pytest.mark.asyncio
    async def test_add_behaviour_while_running(self, bus: MessageBus):
        results: list[str] = []

        class Late(OneShotBehaviour):
            async def run(self):
                results.append("late")

        async with BaseAgent("a", bus=bus) as agent:
            agent.add_behaviour(Late())
            await asyncio.sleep(0.1)
        assert results == ["late"]

    @pytest.mark.asyncio
    async def test_default_bus(self):
        agent = BaseAgent("a")
        assert agent.bus is not None
        await agent.start()
        await agent.stop()

    @pytest.mark.asyncio
    async def test_double_start_raises(self, bus: MessageBus):
        agent = BaseAgent("a", bus=bus)
        await agent.start()
        with pytest.raises(AgentAlreadyRegisteredError):
            await agent.start()
        await agent.stop()

    @pytest.mark.asyncio
    async def test_stop_timeout(self, bus: MessageBus):
        class Stuck(CyclicBehaviour):
            async def run(self):
                await asyncio.sleep(100)

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(Stuck())
        await agent.start()
        # Should not hang — timeout triggers.
        await agent.stop(timeout=0.1)
        assert not agent.is_alive

    @pytest.mark.asyncio
    async def test_bus_property(self, bus: MessageBus):
        agent = BaseAgent("a", bus=bus)
        assert agent.bus is bus
