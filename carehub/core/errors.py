class EventConflictError(RuntimeError):
    """同一 event_id 携带不同 checksum，必须隔离而不能覆盖。"""
