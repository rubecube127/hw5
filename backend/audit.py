"""Append-only audit trail for agent loop activity."""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from .models import AgentRole, AuditEvent


AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_LOCK = Lock()


def record_event(run_id: str, step: int, agent: AgentRole, action: str, *, ticket_id: int | None = None, details: dict[str, object] | None = None) -> None:
    """Append one JSON event without replacing prior runs."""
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        step=step,
        agent=agent,
        action=action,
        ticket_id=ticket_id,
        details=details or {},
    ).model_dump()
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        existing: list[dict[str, object]] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
            existing = json.loads(AUDIT_PATH.read_text())
        existing.append(event)
        AUDIT_PATH.write_text(json.dumps(existing, indent=2) + "\n")
