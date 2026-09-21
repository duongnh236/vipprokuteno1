"""Reconnect ownership for account, leader/member and maintenance outcomes."""


def force_supervisor(username, client, reason, *, services):
    if getattr(client, "_daily_use_selected_pet", False) and getattr(client, "running", False):
        client._daily_instance_blocked = True
        services.log.warning("[%s] Daily yêu cầu phục hồi (%s): giữ online, không ép reconnect",
                             username, reason)
        return False
    services.account_forced_reconnect.add(username)
    services.account_forced_reconnect_reason[username] = reason
    try:
        client.close()
    except Exception:
        pass
    return False


def stop_all_for_maintenance(trigger_username="", *, services):
    services.log.error("[BAO TRI] server gui ma 60 cho %s -> OFF TAT CA ACCOUNT, KHONG RECONNECT",
                       trigger_username or "mot account")
    for user, event in list(services.account_stops.items()):
        services.account_stop_reasons[user] = "Server bao tri (ma 60) - da off tat ca account"
        try:
            event.set()
        except Exception:
            pass
        services.account_reconnect[user] = False
        services.account_forced_reconnect.discard(user)
        services.account_forced_reconnect_reason.pop(user, None)
    for client in list(services.account_clients.values()):
        try:
            client.close()
        except Exception:
            pass
