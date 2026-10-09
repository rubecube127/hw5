# Campus Customs MCP Server

This FastMCP server provides read-only tools that agents can use to inspect the Campus Customs operations database while working on shop tickets.

It uses `data/campus_customs_new.db`, resolved relative to `mcp_server/server.py`.

## Tools

- `check_inventory(sku, size)` — returns the matching product's quantity and location from `inventory`.
- `get_invoice_vendor(invoice_id)` — returns invoice status, amount, due date, description, and the linked vendor's specialty and lead time from `invoices` and `vendors`.
- `get_lease_rent_status(lease_id)` — returns lease and rent details together with `desk.date_today` from `leases` and `desk`.
- `list_open_tickets()` — returns the open operations-board tickets from `tickets`.
- `get_ticket(ticket_id)` — returns one complete ticket from `tickets`.
- `get_pricing(sku)` — returns unit cost and list price from `pricing`.
- `get_cash_status(account="checking")` — returns the current balance and date from `cash_accounts`.
- `get_vendor_open_invoices(vendor_id)` — returns open unpaid invoices for a vendor from `invoices`.

The server is intentionally not started or connected as part of this problem.
