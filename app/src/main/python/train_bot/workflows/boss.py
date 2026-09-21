"""Boss activities owned exclusively by the Daily workflow.

This module deliberately knows nothing about gathering, channels, parties, train or
Di Gioi. The caller supplies the active Daily session and cancellation predicate.
"""
from dataclasses import dataclass


ORDER = ("legion_boss", "world_boss")


@dataclass(frozen=True)
class BossResult:
    status: str
    message: str = ""

    @property
    def completed(self):
        return self.status == "completed"


def _cancel_reason(session, stopped):
    if stopped():
        return "user da bam Dung Daily"
    if session is not None and not session.active:
        return "workflow Daily khong con hieu luc"
    return None


def run_legion(client, *, session=None, stopped=lambda: False):
    reason = _cancel_reason(session, stopped)
    if reason:
        return BossResult("cancelled", reason)
    try:
        client.do_legion_boss(force=True)
        return BossResult("completed")
    except Exception as exc:
        return BossResult("failed", str(exc))


def run_world(client, *, session=None, stopped=lambda: False):
    reason = _cancel_reason(session, stopped)
    if reason:
        return BossResult("cancelled", reason)
    try:
        client.do_world_boss_all(cho_phep=lambda: _cancel_reason(session, stopped))
        return BossResult("completed")
    except Exception as exc:
        return BossResult("failed", str(exc))


def run_selected(client, task, *, session=None, stopped=lambda: False):
    """Execute exactly one explicitly selected Daily boss task."""
    if task == "legion_boss":
        return run_legion(client, session=session, stopped=stopped)
    if task == "world_boss":
        return run_world(client, session=session, stopped=stopped)
    return BossResult("unknown", "Boss task khong hop le: %s" % task)
