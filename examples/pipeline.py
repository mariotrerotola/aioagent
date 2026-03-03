"""Pipeline example: data flows through a chain of processing agents."""

import asyncio

from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, MessageBus, OneShotBehaviour


class ProducerBehaviour(OneShotBehaviour):
    """Emit raw data items into the pipeline."""

    async def run(self) -> None:
        for i in range(5):
            await self.send(AgentMessage(to="transformer", body=f"item_{i}"))
            print(f"[producer] Sent item_{i}")
        # Signal end of stream.
        await self.send(AgentMessage(to="transformer", body="__END__"))


class TransformerBehaviour(CyclicBehaviour):
    """Transform each item and forward to the sink."""

    async def run(self) -> None:
        msg = await self.receive(timeout=3.0)
        if msg is None:
            return
        if msg.body == "__END__":
            await self.send(AgentMessage(to="sink", body="__END__"))
            self.kill()
            return
        result = msg.body.upper()
        print(f"[transformer] {msg.body} -> {result}")
        await self.send(AgentMessage(to="sink", body=result))


class SinkBehaviour(CyclicBehaviour):
    """Collect transformed results."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[str] = []

    async def run(self) -> None:
        msg = await self.receive(timeout=3.0)
        if msg is None:
            return
        if msg.body == "__END__":
            print(f"[sink] Pipeline complete. Results: {self.results}")
            self.kill()
            return
        self.results.append(msg.body)
        print(f"[sink] Collected: {msg.body}")


async def main() -> None:
    bus = MessageBus()

    producer = BaseAgent("producer", bus=bus)
    transformer = BaseAgent("transformer", bus=bus)
    sink = BaseAgent("sink", bus=bus)

    producer.add_behaviour(ProducerBehaviour())
    transformer.add_behaviour(TransformerBehaviour())
    sink.add_behaviour(SinkBehaviour())

    # Start in reverse order so downstream agents are ready first.
    await sink.start()
    await transformer.start()
    await producer.start()

    await asyncio.sleep(3)

    await producer.stop()
    await transformer.stop()
    await sink.stop()

    print("Pipeline shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
