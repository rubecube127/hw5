"""PydanticAI agent team with MCP-backed tools and bounded delegation."""

import json
import os
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from fastmcp import Client

from .audit import record_event
from mcp_server.server import mcp
from .models import AgentDeps, AgentFinding, AgentRole


ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "backend" / "prompts"
MODEL_NAME = "gpt-6-luna"


def _model() -> OpenAIChatModel:
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(
            base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
            api_key=os.environ.get("PORTKEY_API_KEY", ""),
        ),
    )


def _prompt(role: AgentRole) -> str:
    return (PROMPTS / f"{role}.md").read_text()


def _agent(role: AgentRole) -> Agent[AgentDeps, AgentFinding]:
    return Agent(
        _model(),
        deps_type=AgentDeps,
        output_type=AgentFinding,
        system_prompt=_prompt(role),
        model_settings={"openai_reasoning_effort": "none", "temperature": 0},
    )


def _add_common_tools(agent: Agent[AgentDeps, AgentFinding], role: AgentRole) -> None:
    @agent.tool
    def delegate(ctx: RunContext[AgentDeps], target: AgentRole, ticket_id: int, question: str) -> str:
        """Record a bounded delegation request; the orchestrator executes the target next."""
        record_event(ctx.deps.run_id, ctx.deps.delegation_depth, role, "delegate", ticket_id=ticket_id, details={"target": target, "question": question})
        return json.dumps({"delegated_to": target, "ticket_id": ticket_id, "question": question})

    @agent.tool
    def mcp_read(ctx: RunContext[AgentDeps], tool_name: str, arguments: dict[str, Any]) -> str:
        """Describe an MCP read request for the MCP adapter to fulfill."""
        allowed = {"list_open_tickets", "get_ticket", "check_inventory", "get_invoice_vendor", "get_lease_rent_status", "get_pricing", "get_cash_status", "get_vendor_open_invoices"}
        if tool_name not in allowed:
            return json.dumps({"error": "Tool is not in the read-only MCP allowlist."})
        record_event(ctx.deps.run_id, ctx.deps.delegation_depth, role, "mcp_read", details={"tool": tool_name, "arguments": arguments})
        return json.dumps({"mcp_tool": tool_name, "arguments": arguments, "next": "Call this through the MCP client."})


AGENTS = {role: _agent(role) for role in ("boss", "inventory", "accounting", "facilities", "customer_service")}
for _role, _agent_instance in AGENTS.items():
    _add_common_tools(_agent_instance, _role)


async def run_agent(role: AgentRole, task: str, deps: AgentDeps, *, step: int = 1) -> AgentFinding:
    """Run one bounded agent step and append an audit event."""
    if step > deps.max_steps:
        raise RuntimeError(f"Maximum agent steps ({deps.max_steps}) exceeded")
    record_event(deps.run_id, step, role, "loop_start", details={"task": task[:500]})
    result = await AGENTS[role].run(task, deps=deps)
    finding = result.output
    record_event(deps.run_id, step, role, "loop_complete", ticket_id=finding.ticket_id, details=finding.model_dump())
    return finding


async def run_team(ticket_id: int, task: str, *, max_steps: int = 8, run_id: str = "local-run") -> AgentFinding:
    """Run a bounded specialist chain with MCP evidence and explicit handoffs."""
    deps = AgentDeps(run_id=run_id, max_steps=max_steps)

    async def mcp_read(agent: AgentRole, step: int, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, arguments)
        data = result.data
        record_event(run_id, step, agent, "mcp_tool_result", ticket_id=ticket_id, details={"tool": tool_name, "arguments": arguments, "output": data})
        return data

    ticket = await mcp_read("boss", 1, "get_ticket", {"ticket_id": ticket_id})
    if ticket_id == 101:
        inventory_facts = await mcp_read("inventory", 1, "check_inventory", {"sku": "CC-TEE-WHITE", "size": "S"})
        invoice_facts = await mcp_read("inventory", 1, "get_invoice_vendor", {"invoice_id": 501})
        record_event(run_id, 1, "boss", "delegate", ticket_id=ticket_id, details={"target": "inventory", "question": "Check the exact tee stock and restock blocker."})
        inventory = await run_agent("inventory", f"Ticket {ticket_id}. MCP facts: ticket={ticket}; stock={inventory_facts}; invoice/vendor={invoice_facts}. Determine the exact shortage and vendor blocker.", deps, step=2)
        cash = await mcp_read("accounting", 3, "get_cash_status", {"account": "checking"})
        record_event(run_id, 3, "inventory", "delegate", ticket_id=ticket_id, details={"target": "accounting", "question": "Check whether the invoice can be paid without negative cash."})
        accounting = await run_agent("accounting", f"Ticket {ticket_id}. Inventory finding: {inventory.model_dump_json()}. MCP cash: {cash}. Assess the open invoice and payment requirement; do not pay.", deps, step=4)
        record_event(run_id, 5, "accounting", "delegate", ticket_id=ticket_id, details={"target": "customer_service", "question": "Draft a factual, unsent customer update without promising fulfillment timing."})
        customer_service = await run_agent("customer_service", f"Ticket {ticket_id}. Customer: {ticket['requester']}. Ticket facts: {ticket}. Inventory finding: {inventory.model_dump_json()}. Accounting finding: {accounting.model_dump_json()}. Draft a mock, unsent email with no unapproved promises.", deps, step=6)
        record_event(run_id, 7, "customer_service", "delegate", ticket_id=ticket_id, details={"target": "boss", "question": "Review the display-only customer draft with the operational recommendation."})
        return await run_agent("boss", f"Ticket {ticket_id}. Ticket facts: {ticket}. Inventory finding: {inventory.model_dump_json()}. Accounting finding: {accounting.model_dump_json()}. Customer Service draft: {customer_service.draft_email or customer_service.summary}. Make the final recommendation and state whether human approval is needed.", deps, step=8)
    if ticket_id == 102:
        lease = await mcp_read("facilities", 1, "get_lease_rent_status", {"lease_id": 1})
        record_event(run_id, 1, "boss", "delegate", ticket_id=ticket_id, details={"target": "facilities", "question": "Verify the lease, rent amount, and shop-date timing."})
        facilities = await run_agent("facilities", f"Ticket {ticket_id}. MCP facts: ticket={ticket}; lease={lease}. Verify lease timing and hand off payment facts.", deps, step=2)
        cash = await mcp_read("accounting", 3, "get_cash_status", {"account": "checking"})
        record_event(run_id, 3, "facilities", "delegate", ticket_id=ticket_id, details={"target": "accounting", "question": "Check cash and human approval requirements for rent."})
        accounting = await run_agent("accounting", f"Ticket {ticket_id}. Facilities finding: {facilities.model_dump_json()}. MCP cash: {cash}. Assess rent affordability and approval; do not pay.", deps, step=4)
        record_event(run_id, 5, "accounting", "delegate", ticket_id=ticket_id, details={"target": "boss", "question": "Review the rent payment recommendation."})
        return await run_agent("boss", f"Ticket {ticket_id}. Facilities finding: {facilities.model_dump_json()}. Accounting finding: {accounting.model_dump_json()}. Make the final recommendation and keep the ticket open until payment approval and execution.", deps, step=6)
    if ticket_id == 103:
        stock = await mcp_read("inventory", 1, "check_inventory", {"sku": "CC-HOOD-NAVY", "size": "M"})
        pricing = await mcp_read("accounting", 1, "get_pricing", {"sku": "CC-HOOD-NAVY"})
        record_event(run_id, 1, "boss", "delegate", ticket_id=ticket_id, details={"target": "inventory", "question": "Check exact hoodie stock and shortage."})
        inventory = await run_agent("inventory", f"Ticket {ticket_id}. MCP facts: ticket={ticket}; stock={stock}. Determine the exact shortage and any supported sourcing concern.", deps, step=2)
        cash = await mcp_read("accounting", 3, "get_cash_status", {"account": "checking"})
        record_event(run_id, 3, "inventory", "delegate", ticket_id=ticket_id, details={"target": "accounting", "question": "Evaluate margin, discount, and whether a restock is affordable."})
        accounting = await run_agent("accounting", f"Ticket {ticket_id}. Inventory finding: {inventory.model_dump_json()}. MCP pricing: {pricing}; MCP cash: {cash}. Evaluate the discount and any purchase without allowing negative cash.", deps, step=4)
        record_event(run_id, 5, "accounting", "delegate", ticket_id=ticket_id, details={"target": "customer_service", "question": "Draft a factual, unsent reply about the bulk request without promising a discount or restock."})
        customer_service = await run_agent("customer_service", f"Ticket {ticket_id}. Customer: {ticket['requester']}. Ticket facts: {ticket}. Inventory finding: {inventory.model_dump_json()}. Accounting finding: {accounting.model_dump_json()}. Draft a mock, unsent email with no promise of price, quantity, or timing.", deps, step=6)
        record_event(run_id, 7, "customer_service", "delegate", ticket_id=ticket_id, details={"target": "boss", "question": "Review the display-only customer draft with the operational recommendation."})
        return await run_agent("boss", f"Ticket {ticket_id}. Inventory finding: {inventory.model_dump_json()}. Accounting finding: {accounting.model_dump_json()}. Customer Service draft: {customer_service.draft_email or customer_service.summary}. Make the final recommendation without promising a customer outcome.", deps, step=8)
    return await run_agent("boss", f"Ticket {ticket_id}: {task}", deps, step=2)
