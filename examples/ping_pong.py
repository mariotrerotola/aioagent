"""Ping-pong example: two agents exchanging messages."""

import asyncio

from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, MessageBus


class PingBehaviour(CyclicBehaviour):
    """Send 'ping' and wait for a reply, up to 5 rounds."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = 0

    async def run(self) -> None:
        self.counter += 1
        print(f"[ping] Sending ping #{self.counter}")
        await self.send(AgentMessage(to="pong", body=f"ping #{self.counter}"))

        reply = await self.receive(timeout=2.0)
        if reply:
            print(f"[ping] Got reply: {reply.body}")

        if self.counter >= 5:
            print("[ping] Done after 5 rounds")
            self.kill()

        await asyncio.sleep(0.3)


class PongBehaviour(CyclicBehaviour):
    """Wait for messages and reply with 'pong'."""

    async def run(self) -> None:
        msg = await self.receive(timeout=2.0)
        if msg:
            print(f"[pong] Received: {msg.body} -> replying")
            await self.send(msg.make_reply(body="pong"))


class PingAgent(BaseAgent):
    async def setup(self) -> None:
        self.add_behaviour(PingBehaviour())


class PongAgent(BaseAgent):
    async def setup(self) -> None:
        self.add_behaviour(PongBehaviour())


async def main() -> None:
    bus = MessageBus()

    async with PongAgent("pong", bus=bus), PingAgent("ping", bus=bus):
        # Let agents exchange messages for a few seconds.
        await asyncio.sleep(3)

    print("All agents stopped.")


if __name__ == "__main__":
    asyncio.run(main())
