from datetime import timedelta

from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, ConsentLedger, ServerSidePDP
from carehub.sse import AuthorizedStateStream


def test_sse_is_scoped_resumable_and_rechecks_revocation(tmp_path):
    store = EventStore(tmp_path / "sse.db"); ledger = ConsentLedger(store); pdp = ServerSidePDP(store, ledger); stream = AuthorizedStateStream(pdp)
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:bob", role="FAMILY")
    consent = ledger.grant(owner="user:alice", grantee="user:bob", household_id="home:a", scope="view", purpose="stream", channel="SSE", tenant_id="tenant:a")
    consent = ledger.activate(consent["consent_id"], actor="user:alice", expected_version=1)
    event_id = stream.publish(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", view="tasks", snapshot_id="snap-1")
    stream.publish(tenant_id="tenant:a", household_id="home:b", subject_id="user:alice", view="tasks", snapshot_id="other")
    bob = AuthContext("user:bob", "tenant:a")
    events = stream.read(context=bob, household_id="home:a", subject_id="user:alice")
    assert [(event.event, event.data) for event in events] == [("view.updated", {"view": "tasks", "snapshot_id": "snap-1"})]
    assert stream.read(context=bob, household_id="home:a", subject_id="user:alice", last_event_id=event_id)[0].event == "heartbeat"
    ledger.revoke(consent["consent_id"], actor="user:alice", expected_version=2)
    assert stream.read(context=bob, household_id="home:a", subject_id="user:alice") == []
    assert "payload" not in stream.encode(events[0])
    store.close()
