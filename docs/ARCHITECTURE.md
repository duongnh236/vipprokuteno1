# TSBot Python architecture

The Android bridge and workflow engine use one-way dependencies:

```text
agent_bridge / api
        |
        v
runtime coordinator + registry
        |
        v
workflows (train, digioi, daily, dungeon, boss, party, channel, reconnect)
        |
        v
GameClient + combat/state/battle tracker
        |
        v
TS Online protocol
```

## Ownership

- `runtime/registry.py`: live clients, workers, stop signals and reconnect metadata.
- `runtime/context.py`: immutable account/party inputs passed to workflows.
- `workflows/lifecycle.py`: exactly one active workflow session per party.
- `workflows/party.py`: participants, invitations, server roster and strategist.
- `workflows/channel.py`: manual channel synchronization and capacity decisions.
- `workflows/train.py`: gather, form party, route to map/coordinate and farm recovery.
- `workflows/digioi.py`: enter, pursue, exit and hand off to train.
- `workflows/daily.py`: ordered daily orchestration and stop-after-battle.
- `workflows/dungeon.py`: solo/team dungeon execution and retry policy.
- `workflows/boss.py`: legion/world boss eligibility and execution.
- `workflows/reconnect.py`: disconnect classification and workflow restoration.
- `combat.py`: skill and target decisions only.
- `client.py`: packet parsing/sending and low-level game actions only.
- `api/`: Android-facing account, inventory, skill, furnace and map operations.
- `run_party_digioi.py`: temporary bootstrap/facade; compatibility wrappers are deleted after
  every caller has migrated.

## Non-negotiable rules

1. Workflow modules never import `run_party_digioi`.
2. A workflow receives registry/config/log/time through explicit services.
3. Only the active `WorkflowSession` may move or change the mode of an account.
4. Workflow transitions never require reconnect when the socket is healthy.
5. Party readiness is verified from the leader's server roster, not a local ACK counter.
6. Daily account tasks do not wait for unrelated accounts; only team dungeon has a team barrier.
7. Packet constants and combat decisions do not live in orchestration modules.
8. Every extraction keeps a compatibility wrapper until Android and tests use the new owner.

## Migration order

1. Pure map/party/DG helpers.
2. Party and channel ownership.
3. Reconnect supervisor.
4. Train state machine.
5. Dị giới state machine and train handoff.
6. Boss and dungeon execution.
7. Daily orchestrator.
8. Android API modules.
9. Replace the legacy `run_account` body with workflow dispatch.
10. Delete compatibility wrappers and legacy globals.
