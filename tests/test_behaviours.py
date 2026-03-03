"""Tests for behaviour classes."""

import asyncio

import pytest

from aioagent import (
    AgentMessage,
    BaseAgent,
    BehaviourNotBoundError,
    CyclicBehaviour,
    FSMBehaviour,
    MessageBus,
    OneShotBehaviour,
    PeriodicBehaviour,
)


@pytest.fixture
def bus():
    return MessageBus()


class TestOneShotBehaviour:
    @pytest.mark.asyncio
    async def test_runs_once(self, bus: MessageBus):
        results: list[str] = []

        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                results.append("done")

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(MyBehaviour())
        await agent.start()
        await asyncio.sleep(0.1)
        await agent.stop()
        assert results == ["done"]

    @pytest.mark.asyncio
    async def test_done_flag(self, bus: MessageBus):
        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                pass

        b = MyBehaviour()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(b)
        await agent.start()
        await asyncio.sleep(0.1)
        assert b.done()
        await agent.stop()


class TestCyclicBehaviour:
    @pytest.mark.asyncio
    async def test_runs_multiple_times(self, bus: MessageBus):
        counter = {"n": 0}

        class MyBehaviour(CyclicBehaviour):
            async def run(self):
                counter["n"] += 1
                if counter["n"] >= 5:
                    self.kill()

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(MyBehaviour())
        await agent.start()
        await asyncio.sleep(0.2)
        await agent.stop()
        assert counter["n"] >= 5


class TestPeriodicBehaviour:
    @pytest.mark.asyncio
    async def test_runs_periodically(self, bus: MessageBus):
        counter = {"n": 0}

        class MyBehaviour(PeriodicBehaviour):
            async def run(self):
                counter["n"] += 1

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(MyBehaviour(period=0.05))
        await agent.start()
        await asyncio.sleep(0.3)
        await agent.stop()
        assert counter["n"] >= 3

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError, match="positive"):

            class Bad(PeriodicBehaviour):
                async def run(self):
                    pass

            Bad(period=0)

    def test_negative_period_raises(self):
        with pytest.raises(ValueError, match="positive"):

            class Bad(PeriodicBehaviour):
                async def run(self):
                    pass

            Bad(period=-1)


class TestBehaviourLifecycle:
    @pytest.mark.asyncio
    async def test_on_start_and_on_end(self, bus: MessageBus):
        events: list[str] = []

        class MyBehaviour(OneShotBehaviour):
            async def on_start(self):
                events.append("start")

            async def run(self):
                events.append("run")

            async def on_end(self):
                events.append("end")

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(MyBehaviour())
        await agent.start()
        await asyncio.sleep(0.1)
        await agent.stop()
        assert events == ["start", "run", "end"]

    @pytest.mark.asyncio
    async def test_exception_in_run_does_not_crash_agent(self, bus: MessageBus):
        class Faulty(OneShotBehaviour):
            async def run(self):
                raise RuntimeError("boom")

        b = Faulty()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(b)
        await agent.start()
        await asyncio.sleep(0.1)
        assert b.done()
        assert agent.is_alive
        await agent.stop()

    @pytest.mark.asyncio
    async def test_on_end_called_after_exception(self, bus: MessageBus):
        events: list[str] = []

        class Faulty(OneShotBehaviour):
            async def run(self):
                raise RuntimeError("boom")

            async def on_end(self):
                events.append("end")

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(Faulty())
        await agent.start()
        await asyncio.sleep(0.1)
        await agent.stop()
        assert "end" in events

    @pytest.mark.asyncio
    async def test_send_and_receive(self, bus: MessageBus):
        received_body: list[str] = []

        class Sender(OneShotBehaviour):
            async def run(self):
                await self.send(AgentMessage(to="receiver", body="hello"))

        class Receiver(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    received_body.append(msg.body)
                    self.kill()

        sender_agent = BaseAgent("sender", bus=bus)
        receiver_agent = BaseAgent("receiver", bus=bus)
        sender_agent.add_behaviour(Sender())
        receiver_agent.add_behaviour(Receiver())

        await receiver_agent.start()
        await sender_agent.start()
        await asyncio.sleep(0.3)
        await sender_agent.stop()
        await receiver_agent.stop()

        assert received_body == ["hello"]

    def test_unbound_behaviour_raises(self):
        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                pass

        b = MyBehaviour()
        with pytest.raises(BehaviourNotBoundError):
            _ = b.agent

    @pytest.mark.asyncio
    async def test_unbound_send_raises(self):
        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                pass

        b = MyBehaviour()
        with pytest.raises(BehaviourNotBoundError):
            await b.send(AgentMessage(to="x"))

    @pytest.mark.asyncio
    async def test_unbound_receive_raises(self):
        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                pass

        b = MyBehaviour()
        with pytest.raises(BehaviourNotBoundError):
            await b.receive(timeout=0.01)

    @pytest.mark.asyncio
    async def test_kill_before_start(self, bus: MessageBus):
        class MyBehaviour(OneShotBehaviour):
            async def run(self):
                pass

        b = MyBehaviour()
        b.kill()  # should be a no-op, no task yet
        assert not b.done()


class TestFSMBehaviour:
    @pytest.mark.asyncio
    async def test_basic_fsm(self, bus: MessageBus):
        log: list[str] = []

        class MyFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("A", self.state_a, initial=True)
                self.add_state("B", self.state_b)
                self.add_state("C", self.state_c, final=True)
                self.add_transition("A", "B")
                self.add_transition("B", "C")

            async def state_a(self):
                log.append("A")
                self.set_next_state("B")

            async def state_b(self):
                log.append("B")
                self.set_next_state("C")

            async def state_c(self):
                log.append("C")

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(MyFSM())
        await agent.start()
        await asyncio.sleep(0.2)
        await agent.stop()
        assert log == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_fsm_current_state(self, bus: MessageBus):
        class MyFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("ONLY", self.only, initial=True, final=True)

            async def only(self):
                pass

        fsm = MyFSM()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(fsm)
        assert fsm.current_state is None
        await agent.start()
        await asyncio.sleep(0.1)
        assert fsm.current_state == "ONLY"
        await agent.stop()

    @pytest.mark.asyncio
    async def test_fsm_no_initial_state(self, bus: MessageBus):
        class BadFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("A", self.state_a)

            async def state_a(self):
                pass

        fsm = BadFSM()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(fsm)
        await agent.start()
        await asyncio.sleep(0.1)
        assert fsm.done()
        await agent.stop()

    def test_fsm_duplicate_initial_state(self):
        class BadFSM(FSMBehaviour):
            async def setup_fsm(self):
                pass

        fsm = BadFSM()

        async def handler():
            pass

        fsm.add_state("A", handler, initial=True)
        with pytest.raises(ValueError, match="Duplicate initial"):
            fsm.add_state("B", handler, initial=True)

    @pytest.mark.asyncio
    async def test_fsm_invalid_transition(self, bus: MessageBus):
        class BadFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("A", self.state_a, initial=True)
                self.add_state("B", self.state_b, final=True)
                # No transition A -> B registered

            async def state_a(self):
                self.set_next_state("B")

            async def state_b(self):
                pass

        fsm = BadFSM()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(fsm)
        await agent.start()
        await asyncio.sleep(0.2)
        assert fsm.done()
        await agent.stop()

    @pytest.mark.asyncio
    async def test_fsm_no_next_state(self, bus: MessageBus):
        class BadFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("A", self.state_a, initial=True)
                self.add_state("B", self.state_b, final=True)
                self.add_transition("A", "B")

            async def state_a(self):
                pass  # forgot to call set_next_state

            async def state_b(self):
                pass

        fsm = BadFSM()
        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(fsm)
        await agent.start()
        await asyncio.sleep(0.2)
        assert fsm.done()
        await agent.stop()

    @pytest.mark.asyncio
    async def test_fsm_loop_back(self, bus: MessageBus):
        counter = {"n": 0}

        class LoopFSM(FSMBehaviour):
            async def setup_fsm(self):
                self.add_state("WORK", self.work, initial=True)
                self.add_state("DONE", self.finish, final=True)
                self.add_transition("WORK", "WORK")
                self.add_transition("WORK", "DONE")

            async def work(self):
                counter["n"] += 1
                if counter["n"] >= 3:
                    self.set_next_state("DONE")
                else:
                    self.set_next_state("WORK")

            async def finish(self):
                pass

        agent = BaseAgent("a", bus=bus)
        agent.add_behaviour(LoopFSM())
        await agent.start()
        await asyncio.sleep(0.2)
        await agent.stop()
        assert counter["n"] == 3
