"""FastAPI backend for the Campus Customs operations dashboard."""

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent_team import run_team
from .audit import AUDIT_PATH, record_event

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "data" / "campus_customs_new.db"
ORIGINAL_DATABASE_PATH = ROOT / "data" / "campus_customs.db"
app = FastAPI(title="Campus Customs Operations API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ApprovalRequest(BaseModel):
    approved: bool = False
    approved_by: str = "dashboard_human"
    amount: float = Field(gt=0)
    kind: Literal["invoice", "rent", "purchase"]
    ref_id: int | None = None
    ticket_id: int | None = None
    account: str = "checking"


class PaymentProposal(BaseModel):
    ticket_id: int
    amount: float
    kind: Literal["invoice", "rent", "purchase"]
    ref_id: int | None = None
    label: str


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _read_events(limit: int) -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
        return []
    return json.loads(AUDIT_PATH.read_text())[-limit:]


def _payment_proposal(connection: sqlite3.Connection, ticket: sqlite3.Row) -> PaymentProposal | None:
    """Return the single approval request supported by a ticket, if still needed."""
    if ticket["status"] != "open":
        return None
    if ticket["invoice_id"] is not None:
        invoice = connection.execute("SELECT id, amount, status FROM invoices WHERE id = ?", (ticket["invoice_id"],)).fetchone()
        if invoice and invoice["status"] == "open":
            return PaymentProposal(ticket_id=ticket["id"], amount=invoice["amount"], kind="invoice", ref_id=invoice["id"], label=f"Pay invoice {invoice['id']}")
    if ticket["lease_id"] is not None:
        lease = connection.execute("SELECT id, monthly_rent FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
        if lease:
            return PaymentProposal(ticket_id=ticket["id"], amount=lease["monthly_rent"], kind="rent", ref_id=lease["id"], label=f"Pay rent for lease {lease['id']}")
    return None


@app.get("/tickets")
def get_tickets() -> list[dict[str, Any]]:
    """Return all ticket records and their current open/resolved status."""
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return [{**dict(row), "state": "resolved" if row["status"] == "resolved" else "open"} for row in rows]


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Run Boss for one ticket using the bounded agent-team loop."""
    with _connect() as connection:
        ticket = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    run_id = str(uuid4())
    finding = await run_team(ticket_id, f"Plan and coordinate work for this ticket: {dict(ticket)}", run_id=run_id)
    with _connect() as connection:
        proposal = _payment_proposal(connection, ticket)
        if proposal is None:
            connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
            connection.commit()
            record_event(run_id, 2, "boss", "ticket_resolved", ticket_id=ticket_id, details={"outcome": "No payment approval required"})
    return {"finding": finding.model_dump(), "approval_request": proposal.model_dump() if proposal else None}


@app.get("/events")
def get_events(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    """Return recent append-only agent events for dashboard refreshes."""
    return _read_events(limit)


@app.get("/tickets/{ticket_id}/approval")
def get_ticket_approval(ticket_id: int) -> PaymentProposal | None:
    """Return a pending, human-reviewable payment request for one open ticket."""
    with _connect() as connection:
        ticket = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket["status"] != "open":
            return None
        return _payment_proposal(connection, ticket)


@app.post("/approvals")
def approve_payment_or_purchase(request: ApprovalRequest) -> dict[str, Any]:
    """Execute an approved outgoing payment and update related records."""
    if not request.approved:
        raise HTTPException(status_code=400, detail="Explicit human approval is required")
    paid_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        account = connection.execute("SELECT balance FROM cash_accounts WHERE name = ?", (request.account,)).fetchone()
        if account is None:
            raise HTTPException(status_code=404, detail="Cash account not found")
        if account["balance"] < request.amount:
            raise HTTPException(status_code=409, detail="Payment refused: insufficient cash")
        if request.kind in {"invoice", "purchase"}:
            if request.ref_id is None:
                raise HTTPException(status_code=400, detail="ref_id is required for invoice or purchase payments")
            invoice = connection.execute("SELECT id, status FROM invoices WHERE id = ?", (request.ref_id,)).fetchone()
            if invoice is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            if invoice["status"] != "open":
                raise HTTPException(status_code=409, detail="Invoice is not open")
        payment = connection.execute(
            "INSERT INTO payments(kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (request.kind, request.ref_id, request.amount, request.account, paid_at, request.approved_by),
        )
        connection.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?", (request.amount, paid_at[:10], request.account))
        if request.kind in {"invoice", "purchase"}:
            connection.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (request.ref_id,))
        if request.ticket_id is not None:
            connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (request.ticket_id,))
        connection.commit()
        outcome = {"payment_id": payment.lastrowid, "kind": request.kind, "ref_id": request.ref_id, "amount": request.amount, "account": request.account, "new_balance": account["balance"] - request.amount, "approved_by": request.approved_by, "ticket_id": request.ticket_id}
        if request.ticket_id is not None:
            record_event("dashboard-approval", 1, "accounting", "payment_executed", ticket_id=request.ticket_id, details=outcome)
            record_event("dashboard-approval", 2, "boss", "ticket_resolved", ticket_id=request.ticket_id, details={"outcome": "Approved payment completed"})
        return outcome


@app.post("/approvals/deny")
def deny_payment_or_purchase(ticket_id: int) -> dict[str, Any]:
    """Keep a ticket open when its prepared payment is declined."""
    record_event("dashboard-approval", 1, "boss", "approval_denied", ticket_id=ticket_id, details={"outcome": "Human denied approval"})
    return {"ticket_id": ticket_id, "status": "open", "message": "Approval denied; the ticket remains open."}


@app.get("/cash")
def get_cash_balance() -> dict[str, Any]:
    """Return the current checking balance."""
    with _connect() as connection:
        row = connection.execute("SELECT * FROM cash_accounts WHERE name = 'checking'").fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Checking account not found")
    return dict(row)


@app.post("/reset")
def reset_database() -> dict[str, str]:
    """Restore the working database from the populated original snapshot."""
    if not ORIGINAL_DATABASE_PATH.exists() or ORIGINAL_DATABASE_PATH.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="Populated original database is unavailable")
    shutil.copy2(ORIGINAL_DATABASE_PATH, DATABASE_PATH)
    record_event("system-reset", 0, "boss", "system_reset", details={"outcome": "Working database restored; dashboard starts a fresh session."})
    return {"status": "reset", "database": str(DATABASE_PATH)}
