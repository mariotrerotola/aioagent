"""FSM example: a simple negotiation between a buyer and a seller."""

import asyncio

from aioagent import AgentMessage, BaseAgent, CyclicBehaviour, FSMBehaviour, MessageBus


class BuyerFSM(FSMBehaviour):
    """Buyer negotiates a price using a finite-state machine."""

    def __init__(self) -> None:
        super().__init__()
        self.offer = 50

    async def setup_fsm(self) -> None:
        self.add_state("PROPOSE", self.propose, initial=True)
        self.add_state("WAIT", self.wait_reply)
        self.add_state("DONE", self.done_state, final=True)

        self.add_transition("PROPOSE", "WAIT")
        self.add_transition("WAIT", "PROPOSE")
        self.add_transition("WAIT", "DONE")

    async def propose(self) -> None:
        print(f"[buyer] Offering ${self.offer}")
        await self.send(
            AgentMessage(to="seller", body=str(self.offer), performative="PROPOSE")
        )
        self.set_next_state("WAIT")

    async def wait_reply(self) -> None:
        reply = await self.receive(timeout=2.0)
        if reply is None:
            print("[buyer] No reply, giving up")
            self.set_next_state("DONE")
        elif reply.performative == "ACCEPT":
            print(f"[buyer] Deal closed at ${reply.body}")
            self.set_next_state("DONE")
        else:
            self.offer += 10
            if self.offer > 100:
                print("[buyer] Too expensive, walking away")
                self.set_next_state("DONE")
            else:
                print(f"[buyer] Rejected, raising offer to ${self.offer}")
                self.set_next_state("PROPOSE")


    async def done_state(self) -> None:
        pass


class SellerBehaviour(CyclicBehaviour):
    """Seller accepts offers above $70."""

    async def run(self) -> None:
        msg = await self.receive(timeout=2.0)
        if msg is None:
            return
        price = int(msg.body)
        if price >= 70:
            print(f"[seller] Accepting ${price}")
            await self.send(msg.make_reply(body=str(price), performative="ACCEPT"))
            self.kill()
        else:
            print(f"[seller] Rejecting ${price}")
            await self.send(msg.make_reply(body=str(price), performative="REJECT"))


class BuyerAgent(BaseAgent):
    async def setup(self) -> None:
        self.add_behaviour(BuyerFSM())


class SellerAgent(BaseAgent):
    async def setup(self) -> None:
        self.add_behaviour(SellerBehaviour())


async def main() -> None:
    bus = MessageBus()
    async with SellerAgent("seller", bus=bus), BuyerAgent("buyer", bus=bus):
        await asyncio.sleep(3)
    print("Negotiation complete.")


if __name__ == "__main__":
    asyncio.run(main())
