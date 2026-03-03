"""Tests for interaction patterns."""

from aioagent import AgentMessage, agree, inform, refuse, request


class TestRequest:
    def test_creates_request_message(self):
        msg = request("worker", body="compute")
        assert msg.to == "worker"
        assert msg.body == "compute"
        assert msg.performative == "REQUEST"
        assert msg.thread is not None

    def test_with_custom_thread(self):
        msg = request("worker", thread="t1")
        assert msg.thread == "t1"

    def test_with_metadata(self):
        msg = request("worker", body="x", priority="high")
        assert msg.metadata["priority"] == "high"


class TestInform:
    def test_creates_inform_message(self):
        msg = inform("worker", body="update")
        assert msg.performative == "INFORM"
        assert msg.thread is not None


class TestAgree:
    def test_creates_agree_reply(self):
        original = AgentMessage(to="server", sender="client", thread="t1", performative="REQUEST")
        reply = agree(original, body="ok")
        assert reply.to == "client"
        assert reply.sender == "server"
        assert reply.performative == "AGREE"
        assert reply.body == "ok"
        assert reply.thread == "t1"


class TestRefuse:
    def test_creates_refuse_reply(self):
        original = AgentMessage(to="server", sender="client", thread="t1", performative="REQUEST")
        reply = refuse(original, body="denied")
        assert reply.to == "client"
        assert reply.sender == "server"
        assert reply.performative == "REFUSE"
        assert reply.body == "denied"
