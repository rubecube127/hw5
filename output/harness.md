# Campus Customs Database Harness

## Tables and fields

### `cash_accounts`

| Field | Type |
|---|---|
| `name` | TEXT, primary key |
| `balance` | REAL, required |
| `date` | TEXT, required |

Tracks available cash so Accounting can check affordability and prevent negative balances.

### `desk`

| Field | Type |
|---|---|
| `date_today` | TEXT, required |
| `notes` | TEXT |

Defines the shop's current date, which agents use to determine whether invoices, rent, and other obligations are overdue.

### `inventory`

| Field | Type |
|---|---|
| `sku` | TEXT, required; part of primary key |
| `name` | TEXT, required |
| `size` | TEXT, required; part of primary key |
| `qty` | INTEGER, required |
| `location` | TEXT, required |

Lets Inventory check stock by SKU and size and identify shortages.

### `invoices`

| Field | Type |
|---|---|
| `id` | INTEGER, primary key |
| `vendor_id` | INTEGER, required; foreign key to `vendors.id` |
| `amount` | REAL, required |
| `due_date` | TEXT, required |
| `status` | TEXT, required |
| `description` | TEXT |

Shows vendor obligations, due dates, and unpaid status so Accounting can prepare or block payments and purchases.

### `leases`

| Field | Type |
|---|---|
| `id` | INTEGER, primary key |
| `space_name` | TEXT, required |
| `landlord` | TEXT, required |
| `monthly_rent` | REAL, required |
| `next_due` | TEXT, required |
| `notes` | TEXT |

Stores shop-space and rent details for Facilities and Accounting.

### `payments`

| Field | Type |
|---|---|
| `id` | INTEGER, primary key |
| `kind` | TEXT, required |
| `ref_id` | INTEGER |
| `amount` | REAL, required |
| `account` | TEXT, required |
| `paid_at` | TEXT, required |
| `approved_by` | TEXT, required |

Provides an audit trail for approved payments and links each payment to its related invoice, lease, or other reference.

### `pricing`

| Field | Type |
|---|---|
| `sku` | TEXT, primary key |
| `unit_cost` | REAL, required |
| `list_price` | REAL, required |

Enables Accounting and Boss to calculate margins and evaluate discounts.

### `tickets`

| Field | Type |
|---|---|
| `id` | INTEGER, primary key |
| `type` | TEXT, required |
| `requester` | TEXT, required |
| `subject` | TEXT, required |
| `sku` | TEXT |
| `size` | TEXT |
| `qty` | INTEGER |
| `lease_id` | INTEGER, foreign key to `leases.id` |
| `invoice_id` | INTEGER, foreign key to `invoices.id` |
| `status` | TEXT, required |
| `notes` | TEXT |
| `created_at` | TEXT, required |

Acts as the operations board that Boss reads and routes to Inventory, Accounting, Facilities, or Customer Service.

### `vendors`

| Field | Type |
|---|---|
| `id` | INTEGER, primary key |
| `name` | TEXT, required |
| `specialty` | TEXT, required |
| `lead_days` | INTEGER, required |

Identifies which vendor can restock a shortage and supplies the lead time for planning.

## Initial database state

- `desk.date_today` is `2026-08-31`.
- Cash account `checking` has `$3,400.00`.
- There are no recorded payments.
- Vendor invoice `501` is open for `$840.00`, due `2026-08-28`, from vendor `1`.
- Rent for lease `1` is `$2,400.00`, next due `2026-09-02`.

## Three open tickets and table relationships

### Ticket `101` — customer order

Tauhid Zaman needs one `CC-TEE-WHITE` in size `S`. Inventory shows quantity `0` for that SKU and size, so Inventory must identify a restock path. The ticket references invoice `501`; that invoice is an open `$840.00` rush reprint invoice from vendor `1`, Bulldog Print Co., whose lead time is 5 days. Pricing lists the tee at `$8.00` cost and `$28.00` list price.

Relationships: `tickets.invoice_id → invoices.id → vendors.id`; the SKU and size connect to `inventory` and `pricing`.

### Ticket `102` — rent notice

Elm City Properties reports that shop rent is due in two days. The ticket references lease `1`, which is for the Chapel Street shop and has `$2,400.00` rent due `2026-09-02`. With `desk.date_today` set to `2026-08-31`, this is not yet overdue. Accounting should check cash and prepare a payment for human approval; Facilities owns the lease context.

Relationships: `tickets.lease_id → leases.id`; due-date evaluation uses `desk.date_today`; an approved payment would be recorded in `payments` and reduce `cash_accounts`.

### Ticket `103` — price override

Yale AI Club wants 20 `CC-HOOD-NAVY` hoodies in size `M` with a bulk discount. Inventory has 8 units available, creating a shortfall of 12. Pricing lists a `$22.00` unit cost and `$58.00` list price, so Accounting can evaluate the margin before Boss approves a discount or purchase plan. The ticket has no lease or invoice reference.

Relationships: the SKU and size connect to `inventory` and the SKU connects to `pricing`; any future vendor purchase would use `vendors` and create or reference an `invoices` record.

## MCP tools

### `check_inventory(sku, size)`

- Tables read: `inventory`
- Ticket unlocked: `103`
- Why: Ticket 103 requests 20 `CC-HOOD-NAVY` hoodies in size M, and this tool returns the exact stock quantity and location needed to identify its shortage.

### `get_invoice_vendor(invoice_id)`

- Tables read: `invoices`, `vendors`
- Ticket unlocked: `101`
- Why: Ticket 101 references invoice 501, and this tool reveals that invoice's open status, due date, vendor, specialty, and five-day lead time for the tee restock decision.

### `get_lease_rent_status(lease_id)`

- Tables read: `leases`, `desk`
- Ticket unlocked: `102`
- Why: Ticket 102 references lease 1, and this tool combines the rent due date with `Desk.date_today` so agents can determine its timing and prepare the correct approval request.

## Problem 4 MCP smoke-test prompts

The following prompts can be used to test each configured MCP tool:

- `check_inventory`: “Use the Campus Customs MCP server to check inventory for SKU `CC-HOOD-NAVY` in size `M`.”
- `get_invoice_vendor`: “Use the Campus Customs MCP server to retrieve invoice `501` and its linked vendor.”
- `get_lease_rent_status`: “Use the Campus Customs MCP server to retrieve lease `1` and its rent status.”

## Problem 5 agent team and MCP tools

### Agents

| Agent | Scope |
|---|---|
| Boss | Reads tickets, delegates across all roles, and makes final recommendations without bypassing human approvals. |
| Inventory | Checks SKU-and-size stock, identifies shortages, and evaluates vendor specialty, lead time, and invoice blockers. |
| Accounting | Checks cash, invoices, rent, costs, margins, discounts, and payment or purchase proposals for human approval. |
| Facilities | Handles leases, rent timing, landlord records, and shop-space issues. |
| Customer Service | Drafts factual, nonbinding customer messages for human review; it never sends them. |

### Complete MCP tool inventory

| Tool | Tables used | Primary agent/ticket use |
|---|---|---|
| `check_inventory(sku, size)` | `inventory` | Inventory checks exact stock for tickets 101 and 103. |
| `get_invoice_vendor(invoice_id)` | `invoices`, `vendors` | Inventory and Accounting inspect ticket 101's invoice, vendor, status, and lead time. |
| `get_lease_rent_status(lease_id)` | `leases`, `desk` | Facilities and Accounting evaluate ticket 102 rent timing. |
| `list_open_tickets()` | `tickets` | Boss reads the operations board before routing work. |
| `get_ticket(ticket_id)` | `tickets` | Every agent retrieves the authoritative ticket fields and links. |
| `get_pricing(sku)` | `pricing` | Accounting evaluates ticket 103's hoodie cost, price, margin, and discount. |
| `get_cash_status(account)` | `cash_accounts` | Accounting checks whether an approved payment can avoid a negative balance. |
| `get_vendor_open_invoices(vendor_id)` | `invoices` | Inventory and Accounting enforce the rule that unpaid invoices block new vendor purchases. |

All listed tools are read-only database access through MCP. No second shop-tools layer is used.

## Safety and token guardrails

- Require explicit human approval before any payment, purchase order, discount exception, customer commitment, or external message; record who approved it.
- Keep customer and vendor communication in drafts only. Never email customers or call real vendors automatically.
- Verify every amount, date, SKU, size, invoice, lease, and vendor against MCP data; surface missing or conflicting facts instead of guessing.
- Use an allowlist of MCP tools and reject unknown tools or arbitrary SQL. Keep payment writes separate, authenticated, and transactionally protected against negative balances.
- Reset the working database to its original values before a full-resolution run, and preserve an append-only audit trail for every agent step, delegation, tool request, and approval.
- Bound each run by a small maximum step count, limit delegation depth, avoid duplicate reads, truncate oversized task text, and return structured findings rather than unconstrained transcripts.
- Use one focused task per agent step, stop when a finding is complete, and require Boss to resolve or escalate rather than retrying indefinitely.

## Backend routes

- `GET /tickets` — returns all tickets with their current `open` or `resolved` state.
- `POST /tickets/{ticket_id}/run` — runs the bounded agent team for one ticket.
- `GET /events?limit=N` — returns the most recent append-only agent audit events.
- `POST /approvals` — executes a human-approved outgoing invoice, rent, or purchase payment and updates cash and related records.
- `GET /cash` — returns the current checking-account balance and date.
- `POST /reset` — restores `data/campus_customs_new.db` from the populated original database snapshot.

## Dashboard

The React/Vite dashboard in `frontend/` calls the FastAPI routes to list and select tickets, launch bounded agent runs, display compact audit activity and Boss summaries, show the checking balance, and submit human payment approvals. Its bulletin-board interface uses white, green, and pink styling; open tickets are pink/red and resolved tickets are green.
