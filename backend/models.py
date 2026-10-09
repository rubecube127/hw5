"""Shared Pydantic models for the Campus Customs agent team."""

from typing import Literal

from pydantic import BaseModel, Field


AgentRole = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]


class Ticket(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: str
    notes: str | None = None
    created_at: str


class AgentFinding(BaseModel):
    agent: AgentRole
    ticket_id: int
    summary: str
    facts: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommended_next_step: str
    requires_human_approval: bool = False
    delegated_to: list[AgentRole] = Field(default_factory=list)
    draft_email: str | None = None


class AuditEvent(BaseModel):
    timestamp: str
    run_id: str
    step: int
    agent: AgentRole
    action: str
    ticket_id: int | None = None
    details: dict[str, object] = Field(default_factory=dict)


class AgentDeps(BaseModel):
    run_id: str
    max_steps: int = Field(default=8, ge=1, le=20)
    delegation_depth: int = Field(default=0, ge=0, le=5)
