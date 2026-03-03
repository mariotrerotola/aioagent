"""Broadcast example: one coordinator notifies all workers."""

import asyncio

from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, MessageBus, OneShotBehaviour


class CoordinatorBehaviour(OneShotBehaviour):
    """Broadcast a task to all registered workers."""

    async def run(self) -> None:
        msg = AgentMessage(
            sender=self.agent.jid,
            to="",  # filled by broadcast
            body="start processing",
            performative="INFORM",
        )
        count = await self.agent.bus.broadcast(msg, exclude=self.agent.jid)
        print(f"[coordinator] Broadcasted to {count} workers")


class WorkerBehaviour(CyclicBehaviour):
    """Wait for a task and acknowledge it."""

    async def run(self) -> None:
        msg = await self.receive(timeout=3.0)
        if msg:
            print(f"[{self.agent.jid}] Received: {msg.body}")
            self.kill()


async def main() -> None:
    bus = MessageBus()

    workers = [BaseAgent(f"worker_{i}", bus=bus) for i in range(4)]
    for w in workers:
        w.add_behaviour(WorkerBehaviour())

    coordinator = BaseAgent("coordinator", bus=bus)
    coordinator.add_behaviour(CoordinatorBehaviour())

    for w in workers:
        await w.start()
    await coordinator.start()

    await asyncio.sleep(2)

    await coordinator.stop()
    for w in workers:
        await w.stop()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
