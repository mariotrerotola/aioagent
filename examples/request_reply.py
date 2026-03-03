"""Request/reply example using the patterns module."""

import asyncio

from aioagent import BaseAgent, CyclicBehaviour, MessageBus, OneShotBehaviour, agree, refuse, request


class ClientBehaviour(OneShotBehaviour):
    """Send requests and print replies."""

    async def run(self) -> None:
        # Request that will be accepted.
        msg = request("server", body="compute fibonacci(10)")
        await self.send(msg)
        reply = await self.receive(timeout=2.0)
        if reply:
            print(f"[client] Reply: {reply.performative} — {reply.body}")

        # Request that will be refused.
        msg = request("server", body="delete everything")
        await self.send(msg)
        reply = await self.receive(timeout=2.0)
        if reply:
            print(f"[client] Reply: {reply.performative} — {reply.body}")


class ServerBehaviour(CyclicBehaviour):
    """Handle incoming requests."""

    async def run(self) -> None:
        msg = await self.receive(timeout=3.0)
        if msg is None:
            return
        print(f"[server] Got request: {msg.body}")
        if "delete" in msg.body:
            await self.send(refuse(msg, body="Operation not permitted"))
        else:
            await self.send(agree(msg, body="Result: 55"))


async def main() -> None:
    bus = MessageBus()

    server = BaseAgent("server", bus=bus)
    server.add_behaviour(ServerBehaviour())

    client = BaseAgent("client", bus=bus)
    client.add_behaviour(ClientBehaviour())

    await server.start()
    await client.start()

    await asyncio.sleep(2)

    await client.stop()
    await server.stop()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
