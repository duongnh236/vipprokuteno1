"""Solo/team dungeon state transitions. Packet-level dungeon actions remain on GameClient."""

TEAM_DUNGEON_MAX_TRIES = 2


def clear_client_flags(client, *, services):
    active = (services.time.time() < getattr(client, "_team_dungeon_until", 0.0)
              or getattr(client.state, "quest_mode", False))
    client._team_dungeon_until = 0.0
    client.state.quest_mode = False
    return active


def selected_levels(party_config, *, services):
    normalize = getattr(services.config, "normalize_team_dungeons", lambda value: value)
    values = normalize(party_config.get("team_dungeons"))
    if not isinstance(values, dict):
        values = getattr(services.config, "DEFAULT_TEAM_DUNGEONS",
                         {20: True, 50: True, 80: True})
    return {int(level): bool(enabled) for level, enabled in values.items()}


def mark_broken(state, level):
    """One failure count per broken cycle; never count once per account."""
    fresh = not state.get("team_dungeon_need_redo")
    if fresh:
        tries = state.setdefault("team_dungeon_tries", {})
        tries[level] = tries.get(level, 0) + 1
        if tries[level] >= TEAM_DUNGEON_MAX_TRIES:
            state["team_dungeon_skip_all"] = True
    state.setdefault("team_dungeon_broke", {})[level] = True
    state["team_dungeon_need_redo"] = True
    state.setdefault("team_dungeon_state", {})[level] = "done"
