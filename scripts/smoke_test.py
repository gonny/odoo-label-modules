#!/usr/bin/env python3
"""End-to-end smoke test for the label_calculator module via XML-RPC.

Exit codes:
    0 – all checks passed
    1 – one or more checks failed

Environment variables (optional):
    ODOO_URL      – Odoo URL        (default: http://localhost:8069)
    ODOO_DB       – Database name   (default: odoo_label)
    ODOO_USER     – Login           (default: admin)
    ODOO_PASSWORD – Password        (default: admin)
"""

import sys
import os

# Allow importing odoo_rpc from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from odoo_rpc import OdooRPC  # noqa: E402


# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------
_passed = 0
_failed = 0


def check(description, condition, detail=""):
    """Assert *condition* and track pass/fail counts."""
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  ✓ {description}")
    else:
        _failed += 1
        msg = f"  ✗ {description}"
        if detail:
            msg += f"  ({detail})"
        print(msg)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------
def run(rpc):
    """Execute all smoke-test steps against a running Odoo instance."""

    # ── 1. Seed data checks ───────────────────────────────────────────
    print("\n── Seed data ──")

    groups = rpc.search_read(
        "label.material.group", [], ["name"],
    )
    group_names = [g["name"] for g in groups]
    check("Material groups exist", len(groups) >= 5,
          f"found {len(groups)}")
    for expected in ["Koženka Royal", "Satén", "TTR pásky",
                     "Heat press", "Komponenty"]:
        check(f"Group '{expected}' present", expected in group_names)

    products = rpc.search_read(
        "product.template",
        [("pricing_type", "=", "calculator")],
        ["name"],
    )
    product_names = [p["name"] for p in products]
    check("Calculator products exist", len(products) >= 2,
          f"found {len(products)}")
    for expected in ["Gravírovaný štítek", "Textilní etiketa"]:
        check(f"Product '{expected}' present", expected in product_names)

    machines = rpc.search_read("label.machine", [], ["name"])
    check("Machines exist", len(machines) >= 2,
          f"found {len(machines)}")

    tiers = rpc.search_read("label.production.tier", [], ["name"])
    check("Production tiers exist", len(tiers) >= 6,
          f"found {len(tiers)}")

    # ── 2. Create a customer ──────────────────────────────────────────
    print("\n── Customer ──")

    partner_name = "Smoke Test Customer"
    existing = rpc.search("res.partner", [("name", "=", partner_name)])
    if existing:
        rpc.write("res.partner", existing, {"active": True})
        partner_id = existing[0]
    else:
        partner_id = rpc.create("res.partner", {
            "name": partner_name,
            "email": "smoke@test.local",
        })
    check("Customer created/found", partner_id,
          f"id={partner_id}")

    # ── 3. Create a sale order with calculator product ────────────────
    print("\n── Sale order ──")

    tmpl = products[0]
    product_ids = rpc.search(
        "product.product",
        [("product_tmpl_id", "=", tmpl["id"])],
        limit=1,
    )
    check("Product variant found", len(product_ids) > 0)
    product_id = product_ids[0]

    # Find default material
    tmpl_full = rpc.read("product.template", [tmpl["id"]],
                         ["label_default_material_id"])[0]
    mat_id = tmpl_full["label_default_material_id"]
    if isinstance(mat_id, (list, tuple)):
        mat_id = mat_id[0]
    check("Default material found", mat_id, f"id={mat_id}")

    order_id = rpc.create_sale_order(partner_id, lines=[{
        "product_id": product_id,
        "product_template_id": tmpl["id"],
        "label_material_id": mat_id,
        "label_width_mm": 30,
        "label_height_mm": 40,
        "product_uom_qty": 100,
    }])
    check("Sale order created", order_id, f"id={order_id}")

    order = rpc.read("sale.order", [order_id],
                     ["name", "state", "amount_total"])[0]
    check("Order is in draft", order["state"] == "draft",
          f"state={order['state']}")

    # ── 4. Verify price calculation ───────────────────────────────────
    print("\n── Price calculation ──")

    sol_ids = rpc.search("sale.order.line",
                         [("order_id", "=", order_id)])
    check("Order line exists", len(sol_ids) > 0)

    line = rpc.read("sale.order.line", sol_ids, [
        "price_unit", "label_calculated_price",
        "label_material_cost_only", "label_price_breakdown",
    ])[0]
    check("Price > 0", line["price_unit"] > 0,
          f"price_unit={line['price_unit']}")
    check("Calculated price > 0", line["label_calculated_price"] > 0,
          f"calc={line['label_calculated_price']}")
    check("Material cost > 0", line["label_material_cost_only"] > 0,
          f"cost={line['label_material_cost_only']}")
    check("Breakdown populated",
          bool(line["label_price_breakdown"]),
          f"len={len(line['label_price_breakdown'] or '')}")

    # ── 5. Confirm order ──────────────────────────────────────────────
    print("\n── Confirm order ──")

    rpc.confirm_sale_order(order_id)
    order = rpc.read("sale.order", [order_id], ["state"])[0]
    check("Order confirmed", order["state"] == "sale",
          f"state={order['state']}")

    # ── 6. Create invoice ─────────────────────────────────────────────
    print("\n── Invoice ──")

    inv_id = rpc.create_invoice_from_sale(order_id)
    check("Invoice created", inv_id, f"id={inv_id}")

    if inv_id:
        inv = rpc.read("account.move", [inv_id], [
            "name", "state", "amount_total",
            "label_variable_symbol",
        ])[0]
        check("Invoice total > 0", inv["amount_total"] > 0,
              f"total={inv['amount_total']}")

        # Variable symbol may only appear after posting
        vs = inv.get("label_variable_symbol", "")
        check("Variable symbol field exists", "label_variable_symbol" in inv)

        # Read invoice lines for material info
        inv_line_ids = rpc.search(
            "account.move.line",
            [("move_id", "=", inv_id),
             ("display_type", "=", "product")],
        )
        if inv_line_ids:
            inv_line = rpc.read("account.move.line", inv_line_ids[:1], [
                "label_material_id", "label_price_breakdown",
            ])[0]
            check("Invoice line has material",
                  bool(inv_line.get("label_material_id")))
            check("Invoice line has breakdown",
                  bool(inv_line.get("label_price_breakdown")))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    rpc = OdooRPC()
    print(f"Smoke test: {rpc.url}  db={rpc.db}")
    print("Connecting …")
    try:
        uid = rpc.connect()
    except Exception as exc:
        print(f"\nFATAL: Cannot connect to Odoo – {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ Authenticated as uid={uid}")

    run(rpc)

    print(f"\n{'─' * 40}")
    print(f"Passed: {_passed}   Failed: {_failed}")
    if _failed:
        print("SMOKE TEST FAILED")
        sys.exit(1)
    else:
        print("SMOKE TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
