from datetime import datetime, timedelta, timezone

from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, AuthorizedProjectionReader, ConsentLedger, G3Service, PolicyRequest, ServerSidePDP
from carehub.core.projections import Projections


class Clock:
    def __init__(self): self.now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    def __call__(self): return self.now


def test_pdp_uses_server_relationships_and_live_consent(tmp_path):
    clock = Clock(); store = EventStore(tmp_path / "policy.db"); ledger = ConsentLedger(store, clock); pdp = ServerSidePDP(store, ledger)
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:bob", role="FAMILY")
    request = PolicyRequest("home:a", "user:alice", "read_authorized_view", "memory", "SENSITIVE", "TERMINAL", "timeline")
    bob = AuthContext("user:bob", "tenant:a", "token-bob")
    # Token only identifies Bob: no client-provided household/role/consent can turn this allow.
    assert pdp.authorize(bob, request).reason == "CONSENT_OR_ABAC_DENIED"
    consent = ledger.grant(owner="user:alice", grantee="user:bob", household_id="home:a", scope="timeline", purpose="memory", expires_at=clock() + timedelta(minutes=1), tenant_id="tenant:a")
    consent = ledger.activate(consent["consent_id"], actor="user:alice", expected_version=1)
    assert pdp.authorize(bob, request).allowed
    ledger.revoke(consent["consent_id"], actor="user:alice", expected_version=2)
    assert pdp.authorize(bob, request).reason == "CONSENT_OR_ABAC_DENIED"
    assert pdp.authorize(bob, PolicyRequest("home:a", "user:alice", "database_write", "memory", "SENSITIVE", "TERMINAL", "timeline")).reason == "CAPABILITY_DENIED"
    store.close()


def test_pdp_denies_cross_scope_and_unknown_actor(tmp_path):
    store = EventStore(tmp_path / "scope.db"); ledger = ConsentLedger(store); pdp = ServerSidePDP(store, ledger)
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    request = PolicyRequest("home:b", "user:alice", "read_authorized_view", "memory", "SENSITIVE", "TERMINAL", "timeline")
    assert pdp.authorize(AuthContext("user:mallory", "tenant:a"), request).reason == "UNKNOWN_SCOPE"
    store.close()


def test_g3_entry_path_uses_pdp_not_client_claimed_role(tmp_path):
    clock = Clock(); store = EventStore(tmp_path / "entry.db"); service = G3Service(store, clock)
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:bob", role="FAMILY")
    request = PolicyRequest("home:a", "user:alice", "read_authorized_view", "memory", "SENSITIVE", "TERMINAL", "timeline")
    # Bob cannot escalate by supplying a SELF role; the method has no role argument.
    assert service.authorized_active_memories(AuthContext("user:bob", "tenant:a"), request) == []
    store.close()


def test_expired_consent_is_persisted_as_expired_and_denied(tmp_path):
    clock = Clock(); store = EventStore(tmp_path / "expired.db"); ledger = ConsentLedger(store, clock)
    consent = ledger.grant(owner="user:alice", grantee="user:bob", household_id="home:a", scope="chat", purpose="chat", expires_at=clock() + timedelta(seconds=1), tenant_id="tenant:a")
    consent = ledger.activate(consent["consent_id"], actor="user:alice", expected_version=1)
    clock.now += timedelta(seconds=2)
    from carehub.g3 import PrivacyAccessRequest
    assert not ledger.allows(PrivacyAccessRequest("user:bob", "user:alice", "home:a", "FAMILY", "chat", "chat", "SENSITIVE", "TERMINAL", "tenant:a"))
    assert ledger.get(consent["consent_id"])["status"] == "EXPIRED"
    store.close()


def test_protected_projection_is_minimized_and_includes_allowed_actions(tmp_path):
    store = EventStore(tmp_path / "views.db"); ledger = ConsentLedger(store); pdp = ServerSidePDP(store, ledger)
    store.register_scope(tenant_id="tenant:a", household_id="home:a", subject_id="user:alice", principal_id="user:alice", role="SELF")
    projections = Projections(tasks={("tenant:a", "user:alice", "home:a", "task:1"): {"task_ref": "task:1", "status": "DUE", "evidence_state": "UNKNOWN", "raw_secret": "must-not-leak"}})
    view = AuthorizedProjectionReader(pdp, projections).read(context=AuthContext("user:alice", "tenant:a"), household_id="home:a", subject_id="user:alice", kind="tasks", purpose="view", resource_version="v7")
    assert view["items"] == [{"task_ref": "task:1", "status": "DUE", "evidence_state": "UNKNOWN"}]
    assert "read_authorized_view" in view["allowed_actions"] and view["resource_version"] == "v7"
    denied = AuthorizedProjectionReader(pdp, projections).read(context=AuthContext("user:alice", "tenant:a"), household_id="home:b", subject_id="user:alice", kind="tasks", purpose="view")
    assert denied == {"items": [], "reason_code": "POLICY_DENIED", "allowed_actions": []}
    store.close()
