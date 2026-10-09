"""FastMCP server for the Campus Customs operations database."""

import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("Campus Customs MCP Server")


def _query_one(query: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
    """Run a read-only query and return one row as a dictionary."""
    with sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(query, parameters).fetchone()
        return dict(row) if row else None


def _query_all(query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a read-only query and return all rows as dictionaries."""
    with sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]


@mcp.tool
def check_inventory(sku: str, size: str) -> dict[str, Any]:
    """Return stock quantity and location for one SKU and size."""
    row = _query_one(
        """
        SELECT sku, name, size, qty, location
        FROM inventory
        WHERE sku = ? AND size = ?
        """,
        (sku, size),
    )
    return row or {"error": "No inventory record found for the requested SKU and size."}


@mcp.tool
def get_invoice_vendor(invoice_id: int) -> dict[str, Any]:
    """Return an invoice and its vendor, including status, due date, and lead time."""
    row = _query_one(
        """
        SELECT invoices.id AS invoice_id,
               invoices.vendor_id,
               invoices.amount,
               invoices.due_date,
               invoices.status,
               invoices.description,
               vendors.name AS vendor_name,
               vendors.specialty,
               vendors.lead_days
        FROM invoices
        JOIN vendors ON vendors.id = invoices.vendor_id
        WHERE invoices.id = ?
        """,
        (invoice_id,),
    )
    return row or {"error": "No invoice found for the requested invoice ID."}


@mcp.tool
def get_lease_rent_status(lease_id: int) -> dict[str, Any]:
    """Return lease rent details together with the shop's current operating date."""
    row = _query_one(
        """
        SELECT leases.id AS lease_id,
               leases.space_name,
               leases.landlord,
               leases.monthly_rent,
               leases.next_due,
               desk.date_today
        FROM leases
        CROSS JOIN desk
        WHERE leases.id = ?
        """,
        (lease_id,),
    )
    return row or {"error": "No lease found for the requested lease ID."}


@mcp.tool
def list_open_tickets() -> list[dict[str, Any]]:
    """Return every ticket currently marked open on the operations board."""
    return _query_all("SELECT * FROM tickets WHERE status = 'open' ORDER BY id")


@mcp.tool
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Return one ticket and its linked lease or invoice identifiers."""
    row = _query_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    return row or {"error": "No ticket found for the requested ticket ID."}


@mcp.tool
def get_pricing(sku: str) -> dict[str, Any]:
    """Return unit cost and list price for a SKU."""
    row = _query_one("SELECT * FROM pricing WHERE sku = ?", (sku,))
    return row or {"error": "No pricing record found for the requested SKU."}


@mcp.tool
def get_cash_status(account: str = "checking") -> dict[str, Any]:
    """Return the current cash balance and its as-of date."""
    row = _query_one("SELECT * FROM cash_accounts WHERE name = ?", (account,))
    return row or {"error": "No cash account found for the requested account."}


@mcp.tool
def get_vendor_open_invoices(vendor_id: int) -> list[dict[str, Any]]:
    """Return open unpaid invoices for a vendor before any new purchase is considered."""
    return _query_all(
        "SELECT * FROM invoices WHERE vendor_id = ? AND status = 'open' ORDER BY due_date, id",
        (vendor_id,),
    )
