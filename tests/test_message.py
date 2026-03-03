"""Tests for AgentMessage and MessageTemplate."""

from aioagent import AgentMessage, MessageTemplate


class TestAgentMessage:
    def test_create_minimal(self):
        msg = AgentMessage(to="bob")
        assert msg.to == "bob"
        assert msg.sender == ""
        assert msg.body == ""
        assert msg.metadata == {}
        assert msg.thread is None
        assert msg.performative is None

    def test_create_full(self):
        msg = AgentMessage(
            to="bob",
            sender="alice",
            body="hello",
            metadata={"key": "val"},
            thread="t1",
            performative="INFORM",
        )
        assert msg.to == "bob"
        assert msg.sender == "alice"
        assert msg.body == "hello"
        assert msg.metadata == {"key": "val"}
        assert msg.thread == "t1"
        assert msg.performative == "INFORM"

    def test_make_reply(self):
        msg = AgentMessage(to="bob", sender="alice", thread="t1", performative="REQUEST")
        reply = msg.make_reply(body="ok")
        assert reply.to == "alice"
        assert reply.sender == "bob"
        assert reply.body == "ok"
        assert reply.thread == "t1"
        assert reply.performative == "REQUEST"

    def test_make_reply_creates_thread(self):
        msg = AgentMessage(to="bob", sender="alice")
        reply = msg.make_reply()
        assert reply.thread is not None

    def test_make_reply_override_performative(self):
        msg = AgentMessage(to="bob", sender="alice", performative="REQUEST")
        reply = msg.make_reply(performative="AGREE")
        assert reply.performative == "AGREE"

    def test_repr_short(self):
        r = repr(AgentMessage(to="bob", sender="alice"))
        assert "bob" in r
        assert "alice" in r

    def test_repr_long_body_truncated(self):
        r = repr(AgentMessage(to="bob", sender="alice", body="x" * 100))
        assert "..." in r

    def test_repr_includes_performative(self):
        r = repr(AgentMessage(to="bob", sender="alice", performative="REQUEST"))
        assert "REQUEST" in r

    def test_repr_includes_thread(self):
        r = repr(AgentMessage(to="bob", sender="alice", thread="t1"))
        assert "t1" in r

    def test_metadata_isolation(self):
        msg = AgentMessage(to="bob", sender="alice", metadata={"k": "v"})
        reply = msg.make_reply()
        reply.metadata["k2"] = "v2"
        assert "k2" not in msg.metadata

    def test_metadata_any_type(self):
        msg = AgentMessage(to="bob", metadata={"count": 42, "active": True, "tags": ["a"]})
        assert msg.metadata["count"] == 42
        assert msg.metadata["active"] is True

    def test_send_to_self(self):
        msg = AgentMessage(to="alice", sender="alice", body="self-note")
        reply = msg.make_reply(body="ack")
        assert reply.to == "alice"
        assert reply.sender == "alice"


class TestMessageTemplate:
    def test_empty_matches_all(self):
        t = MessageTemplate()
        msg = AgentMessage(to="bob", sender="alice", performative="REQUEST")
        assert t.match(msg) is True

    def test_match_sender(self):
        t = MessageTemplate(sender="alice")
        assert t.match(AgentMessage(to="bob", sender="alice")) is True
        assert t.match(AgentMessage(to="bob", sender="carol")) is False

    def test_match_performative(self):
        t = MessageTemplate(performative="REQUEST")
        assert t.match(AgentMessage(to="bob", performative="REQUEST")) is True
        assert t.match(AgentMessage(to="bob", performative="INFORM")) is False

    def test_match_metadata(self):
        t = MessageTemplate(metadata={"protocol": "cnp"})
        assert t.match(AgentMessage(to="bob", metadata={"protocol": "cnp", "extra": "x"})) is True
        assert t.match(AgentMessage(to="bob", metadata={"protocol": "fipa"})) is False
        assert t.match(AgentMessage(to="bob")) is False

    def test_match_combined(self):
        t = MessageTemplate(sender="alice", performative="INFORM")
        assert t.match(AgentMessage(to="bob", sender="alice", performative="INFORM")) is True
        assert t.match(AgentMessage(to="bob", sender="alice", performative="REQUEST")) is False
        assert t.match(AgentMessage(to="bob", sender="carol", performative="INFORM")) is False

    def test_match_sender_case_sensitive(self):
        t = MessageTemplate(sender="Alice")
        assert t.match(AgentMessage(to="bob", sender="alice")) is False
        assert t.match(AgentMessage(to="bob", sender="Alice")) is True

    def test_match_none_performative_in_msg(self):
        t = MessageTemplate(performative="REQUEST")
        assert t.match(AgentMessage(to="bob")) is False

    def test_empty_metadata_matches_all(self):
        t = MessageTemplate(metadata={})
        assert t.match(AgentMessage(to="bob", metadata={"x": "y"})) is True
