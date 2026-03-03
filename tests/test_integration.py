"""Integration tests: full multi-agent scenarios."""

import asyncio

import pytest

from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, FSMBehaviour, MessageBus


class TestPingPong:
    @pytest.mark.asyncio
    async def test_ping_pong_exchange(self):
        bus = MessageBus()
        log: list[str] = []

        class PingBehaviour(CyclicBehaviour):
            async def run(self):
                await self.send(AgentMessage(to="pong", body="ping"))
                reply = await self.receive(timeout=1.0)
                if reply:
                    log.append(f"ping got: {reply.body}")
                    self.kill()

        class PongBehaviour(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    log.append(f"pong got: {msg.body}")
                    await self.send(msg.make_reply(body="pong"))
                    self.kill()

        class PingAgent(BaseAgent):
            async def setup(self):
                self.add_behaviour(PingBehaviour())

        class PongAgent(BaseAgent):
            async def setup(self):
                self.add_behaviour(PongBehaviour())

        pong = PongAgent("pong", bus=bus)
        ping = PingAgent("ping", bus=bus)

        await pong.start()
        await ping.start()
        await asyncio.sleep(0.5)
        await ping.stop()
        await pong.stop()

        assert "pong got: ping" in log
        assert "ping got: pong" in log

    @pytest.mark.asyncio
    async def test_multiple_agents(self):
        bus = MessageBus()
        received: dict[str, list[str]] = {}

        class ListenerBehaviour(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=0.5)
                if msg:
                    received.setdefault(self.agent.jid, []).append(msg.body)
                    self.kill()

        class BroadcasterBehaviour(CyclicBehaviour):
            async def run(self):
                for target in ("listener_1", "listener_2", "listener_3"):
                    await self.send(AgentMessage(to=target, body=f"hello {target}"))
                self.kill()

        agents = []
        for i in range(1, 4):
            a = BaseAgent(f"listener_{i}", bus=bus)
            a.add_behaviour(ListenerBehaviour())
            agents.append(a)

        broadcaster = BaseAgent("broadcaster", bus=bus)
        broadcaster.add_behaviour(BroadcasterBehaviour())
        agents.append(broadcaster)

        for a in agents:
            await a.start()

        await asyncio.sleep(0.5)

        for a in agents:
            await a.stop()

        for i in range(1, 4):
            jid = f"listener_{i}"
            assert jid in received
            assert f"hello {jid}" in received[jid]


class TestBroadcastIntegration:
    @pytest.mark.asyncio
    async def test_broadcast_via_bus(self):
        bus = MessageBus()
        received: dict[str, str] = {}

        class ListenerBehaviour(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    received[self.agent.jid] = msg.body
                    self.kill()

        class BroadcasterBehaviour(CyclicBehaviour):
            async def run(self):
                msg = AgentMessage(to="", sender=self.agent.jid, body="broadcast!")
                await self.agent.bus.broadcast(msg, exclude=self.agent.jid)
                self.kill()

        agents = []
        for i in range(3):
            a = BaseAgent(f"w{i}", bus=bus)
            a.add_behaviour(ListenerBehaviour())
            agents.append(a)

        bc = BaseAgent("bc", bus=bus)
        bc.add_behaviour(BroadcasterBehaviour())
        agents.append(bc)

        for a in agents:
            await a.start()
        await asyncio.sleep(0.5)
        for a in agents:
            await a.stop()

        assert len(received) == 3
        for v in received.values():
            assert v == "broadcast!"


class TestFSMIntegration:
    @pytest.mark.asyncio
    async def test_fsm_negotiation(self):
        bus = MessageBus()
        final_price: list[int] = []

        class BuyerFSM(FSMBehaviour):
            def __init__(self):
                super().__init__()
                self.offer = 50

            async def setup_fsm(self):
                self.add_state("PROPOSE", self.propose, initial=True)
                self.add_state("WAIT", self.wait_reply)
                self.add_state("DONE", self.finish, final=True)
                self.add_transition("PROPOSE", "WAIT")
                self.add_transition("WAIT", "PROPOSE")
                self.add_transition("WAIT", "DONE")

            async def propose(self):
                await self.send(
                    AgentMessage(to="seller", body=str(self.offer), performative="PROPOSE")
                )
                self.set_next_state("WAIT")

            async def wait_reply(self):
                reply = await self.receive(timeout=1.0)
                if reply and reply.performative == "ACCEPT":
                    final_price.append(int(reply.body))
                    self.set_next_state("DONE")
                else:
                    self.offer += 10
                    self.set_next_state("PROPOSE")

            async def finish(self):
                pass

        class SellerBehaviour(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    price = int(msg.body)
                    if price >= 70:
                        await self.send(msg.make_reply(body=str(price), performative="ACCEPT"))
                        self.kill()
                    else:
                        await self.send(msg.make_reply(body=str(price), performative="REJECT"))

        seller = BaseAgent("seller", bus=bus)
        seller.add_behaviour(SellerBehaviour())
        buyer = BaseAgent("buyer", bus=bus)
        buyer.add_behaviour(BuyerFSM())

        await seller.start()
        await buyer.start()
        await asyncio.sleep(1.0)
        await buyer.stop()
        await seller.stop()

        assert final_price == [70]


class TestPipeline:
    @pytest.mark.asyncio
    async def test_data_pipeline(self):
        bus = MessageBus()
        results: list[str] = []

        class Producer(CyclicBehaviour):
            async def run(self):
                for i in range(3):
                    await self.send(AgentMessage(to="transform", body=f"item{i}"))
                await self.send(AgentMessage(to="transform", body="__END__"))
                self.kill()

        class Transformer(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    if msg.body == "__END__":
                        await self.send(AgentMessage(to="sink", body="__END__"))
                        self.kill()
                    else:
                        await self.send(AgentMessage(to="sink", body=msg.body.upper()))

        class Sink(CyclicBehaviour):
            async def run(self):
                msg = await self.receive(timeout=1.0)
                if msg:
                    if msg.body == "__END__":
                        self.kill()
                    else:
                        results.append(msg.body)

        sink = BaseAgent("sink", bus=bus)
        sink.add_behaviour(Sink())
        transform = BaseAgent("transform", bus=bus)
        transform.add_behaviour(Transformer())
        producer = BaseAgent("producer", bus=bus)
        producer.add_behaviour(Producer())

        await sink.start()
        await transform.start()
        await producer.start()
        await asyncio.sleep(1.0)
        await producer.stop()
        await transform.stop()
        await sink.stop()

        assert results == ["ITEM0", "ITEM1", "ITEM2"]
