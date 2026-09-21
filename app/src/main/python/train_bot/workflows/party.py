"""Party ownership: participants, readiness and exact server-roster checks.

This module never imports the legacy runner. Runtime registries are supplied explicitly so
party rules can be tested without starting sockets or Android.
"""


def accounts(pidx, *, services):
    party = services.config.PARTIES[pidx]
    leader = services.config.PARTY_LEADER_ACC.get(pidx)
    valid = [(u, p) for u, p in party if u and u.strip()]
    picker = leader if leader else (valid[0][0] if valid else None)
    return [(u, p, u == leader, u == picker) for u, p in valid]


def running_usernames(pidx, *, services):
    return [u for u, _p, _lead, _pick in accounts(pidx, services=services)
            if services.is_account_running(u)]


def active_usernames(pidx, *, services):
    """Accounts which own a live worker; reconnecting workers remain participants."""
    result = []
    for user, _p, _lead, _pick in accounts(pidx, services=services):
        thread = services.account_threads.get(user)
        stop = services.account_stops.get(user)
        if thread is not None and thread.is_alive() and not (stop and stop.is_set()):
            result.append(user)
    return result


def missing_from_server_roster(pidx, users, leader, skip=(), *, services):
    """Exact party membership comes from the leader's server roster, never local ACK counters."""
    roster = {bytes(entity) for entity in (getattr(leader, "party_members", None) or [])}
    ignored = set(skip or ())
    leader_user = services.config.PARTY_LEADER_ACC.get(pidx)
    missing = []
    for user in users:
        if user == leader_user or user in ignored:
            continue
        client = services.account_clients.get(user)
        if (client is None or not client.running
                or client.current_map != leader.current_map
                or getattr(client, "current_channel", None) != getattr(leader, "current_channel", None)
                or not getattr(client, "self_entity", None)
                or bytes(client.self_entity) not in roster):
            missing.append(user)
    return missing


def set_strategist(leader):
    """Server-backed strategist selection; GameClient resolves the highest INT member."""
    if leader is None or not getattr(leader, "running", False):
        return False
    leader.set_party_strategist()
    return True
