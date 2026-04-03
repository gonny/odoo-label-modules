#!/usr/bin/env python3
"""Odoo XML-RPC client for the label_calculator module.

Usage:
    python scripts/odoo_rpc.py              # Run interactive demo
    python scripts/odoo_rpc.py --help       # Show help

Environment variables (optional):
    ODOO_URL      – Odoo URL        (default: http://localhost:8069)
    ODOO_DB       – Database name   (default: odoo_label)
    ODOO_USER     – Login           (default: admin)
    ODOO_PASSWORD – Password        (default: admin)
"""

import os
import sys
import time
import xmlrpc.client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo_label")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")


# ---------------------------------------------------------------------------
# OdooRPC helper class
# ---------------------------------------------------------------------------
class OdooRPC:
    """Thin wrapper around Odoo's XML-RPC interface."""

    def __init__(
        self, url=ODOO_URL, db=ODOO_DB, user=ODOO_USER, password=ODOO_PASSWORD
    ):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self._common = None
        self._object = None

    # -- connection ---------------------------------------------------------
    def connect(self, retries=12, delay=5):
        """Authenticate and return *uid*.  Retries on connection errors."""
        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common",
            allow_none=True,
        )
        self._object = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object",
            allow_none=True,
        )

        last_err: Exception = RuntimeError("Connection failed")
        for attempt in range(1, retries + 1):
            try:
                self.uid = self._common.authenticate(
                    self.db,
                    self.user,
                    self.password,
                    {},
                )
                if self.uid:
                    return self.uid
                last_err = RuntimeError(
                    f"Authentication failed for {self.user}@{self.db}"
                )
            except (ConnectionRefusedError, OSError, xmlrpc.client.Fault) as exc:
                last_err = exc
            print(
                f"  [attempt {attempt}/{retries}] waiting for Odoo … " f"({last_err})",
                file=sys.stderr,
            )
            time.sleep(delay)
        raise last_err

    # -- generic helpers ----------------------------------------------------
    def execute(self, model, method, *args, **kwargs):
        """Call *model.method* via ``execute_kw``."""
        if self.uid is None:
            raise RuntimeError("Not connected – call connect() first")
        return self._object.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            method,
            list(args),
            kwargs,
        )

    def search(self, model, domain, **kw):
        return self.execute(model, "search", domain, **kw)

    def read(self, model, ids, fields=None):
        if self.uid is None:
            raise RuntimeError("Not connected")
        return self._object.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            "read",
            [ids],
            {"fields": fields or []},
        )

    def search_read(self, model, domain, fields=None, **kw):
        kw["fields"] = fields or []
        return self.execute(model, "search_read", domain, **kw)

    def create(self, model, vals):
        result = self.execute(model, "create", [vals])
        # Odoo 19 @api.model_create_multi returns a list of IDs when the
        # input is a list (even for a single record).  Unwrap it so callers
        # always receive a plain integer for a single-create call.
        if isinstance(result, list):
            return result[0] if len(result) == 1 else result
        return result

    def write(self, model, ids, vals):
        return self.execute(model, "write", ids, vals)

    # -- convenience: sale orders -------------------------------------------
    def create_sale_order(self, partner_id, lines=None):
        """Create a quotation with optional *lines*.

        Each element of *lines* is a dict with keys accepted by
        ``sale.order.line`` (at minimum ``product_id``).

        Lines are embedded in the order's ``create`` call using the Odoo
        one2many command ``(0, 0, vals)`` so that ``order_id`` is properly
        set when Odoo computes precomputed fields such as ``name`` during
        record creation.  Creating lines in a separate RPC call raises
        ``ValueError: Expected singleton: sale.order()`` in Odoo 19.

        Returns the new sale order id.
        """
        order_vals = {"partner_id": partner_id}
        if lines:
            order_vals["order_line"] = [(0, 0, vals) for vals in lines]
        return self.create("sale.order", order_vals)

    def confirm_sale_order(self, order_id):
        """Confirm a sale order (quotation → sale)."""
        return self.execute("sale.order", "action_confirm", [order_id])

    # -- convenience: invoices ---------------------------------------------
    def create_invoice_from_sale(self, order_id):
        """Create and post an invoice from a confirmed sale order.

        Uses the ``sale.advance.payment.inv`` wizard (the public API for
        creating invoices from sale orders).  The private ``_create_invoices``
        method cannot be called remotely in Odoo 19.

        ``create_invoices`` returns an action dict that may contain ``None``
        values.  Odoo's XML-RPC marshaller runs with ``allow_none=False``, so
        the response serialisation raises a Fault even though the invoices
        were created successfully.  We catch that Fault and locate the invoice
        by reading ``invoice_ids`` from the sale order.

        Returns the invoice (account.move) id, or None if not found.
        """
        wizard_id = self.create(
            "sale.advance.payment.inv",
            {
                "advance_payment_method": "delivered",
                "sale_order_ids": [(6, 0, [order_id])],
            },
        )
        try:
            self.execute(
                "sale.advance.payment.inv",
                "create_invoices",
                [wizard_id],
            )
        except xmlrpc.client.Fault as exc:
            # The action dict returned by create_invoices may contain None
            # values that Odoo's XML-RPC serializer (allow_none=False) cannot
            # marshal.  The invoices are created before serialization, so we
            # ignore this specific error and read the invoice from the order.
            if "cannot marshal None" not in str(exc):
                raise
        # Find the invoice created for this order
        order_data = self.read("sale.order", [order_id], ["invoice_ids"])
        if order_data and order_data[0].get("invoice_ids"):
            return order_data[0]["invoice_ids"][0]
        return None

    def read_invoice(self, invoice_id, fields=None):
        """Read invoice fields."""
        default_fields = [
            "name",
            "state",
            "amount_total",
            "amount_residual",
            "label_variable_symbol",
            "partner_id",
            "currency_id",
        ]
        return self.read(
            "account.move",
            [invoice_id],
            fields or default_fields,
        )


# ---------------------------------------------------------------------------
# Interactive demo
# ---------------------------------------------------------------------------
def _demo():
    """Demonstrate XML-RPC workflow: create SO → confirm → invoice."""
    rpc = OdooRPC()
    print(f"Connecting to {rpc.url} (db={rpc.db}) …")
    uid = rpc.connect()
    print(f"  ✓ Authenticated as uid={uid}\n")

    # 1. Find / create a customer
    partners = rpc.search_read(
        "res.partner",
        [("name", "=", "RPC Test Customer")],
        ["id", "name"],
    )
    if partners:
        partner_id = partners[0]["id"]
        print(f"Using existing partner id={partner_id}")
    else:
        partner_id = rpc.create(
            "res.partner",
            {
                "name": "RPC Test Customer",
                "email": "rpc-test@example.com",
            },
        )
        print(f"Created partner id={partner_id}")

    # 2. Find a calculator product
    products = rpc.search_read(
        "product.template",
        [("pricing_type", "=", "calculator")],
        ["id", "name", "label_material_group_id", "label_default_material_id"],
        limit=1,
    )
    if not products:
        print("ERROR: No calculator product found. Is the module installed?")
        sys.exit(1)

    tmpl = products[0]
    product_ids = rpc.search(
        "product.product",
        [("product_tmpl_id", "=", tmpl["id"])],
        limit=1,
    )
    product_id = product_ids[0]
    mat_id = tmpl["label_default_material_id"][0]
    print(
        f"Product: {tmpl['name']} (id={tmpl['id']}, "
        f"variant={product_id}, material={mat_id})"
    )

    # 3. Create a sale order
    order_id = rpc.create_sale_order(
        partner_id,
        lines=[
            {
                "product_id": product_id,
                "product_template_id": tmpl["id"],
                "label_material_id": mat_id,
                "label_width_mm": 30,
                "label_height_mm": 40,
                "product_uom_qty": 100,
            }
        ],
    )
    order = rpc.read("sale.order", [order_id], ["name", "state", "amount_total"])[0]
    print(
        f"\nCreated sale order {order['name']} "
        f"(id={order_id}, total={order['amount_total']})"
    )

    # 4. Read order lines with breakdown
    sol_ids = rpc.search("sale.order.line", [("order_id", "=", order_id)])
    lines = rpc.read(
        "sale.order.line",
        sol_ids,
        [
            "name",
            "product_uom_qty",
            "price_unit",
            "label_calculated_price",
            "label_material_cost_only",
            "label_price_breakdown",
        ],
    )
    for ln in lines:
        print(
            f"  Line: qty={ln['product_uom_qty']} "
            f"price={ln['price_unit']} "
            f"calc={ln['label_calculated_price']}"
        )

    # 5. Confirm order
    rpc.confirm_sale_order(order_id)
    order = rpc.read("sale.order", [order_id], ["state"])[0]
    print(f"\nOrder state after confirm: {order['state']}")

    # 6. Create invoice
    inv_id = rpc.create_invoice_from_sale(order_id)
    if inv_id:
        inv = rpc.read_invoice(inv_id)[0]
        print(
            f"\nInvoice: {inv['name']}  "
            f"total={inv['amount_total']}  "
            f"VS={inv.get('label_variable_symbol', 'N/A')}"
        )
    else:
        print("\nNo invoice created (may need manual invoicing).")

    print("\n✓ Demo complete.")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    _demo()
