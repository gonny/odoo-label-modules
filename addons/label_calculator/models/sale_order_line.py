from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # === Kalkulační pole ===
    pricing_type = fields.Selection(
        related="product_template_id.pricing_type",
        store=True,
        readonly=True,
    )

    label_material_id = fields.Many2one(
        "label.material",
        string="Varianta",
        domain="[('group_id', '=', label_material_group_id), "
               "('group_id.is_addon', '=', False)]",
    )

    label_material_group_id = fields.Many2one(
        related="product_template_id.label_material_group_id",
        store=True,
        readonly=True,
    )

    label_width_mm = fields.Float(
        string="Šířka (mm)",
        digits=(8, 1),
    )
    label_height_mm = fields.Float(
        string="Výška/Délka (mm)",
        digits=(8, 1),
    )

    label_is_repeat_design = fields.Boolean(
        string="Opakovaný design",
        default=False,
    )

    label_ttr_material_id = fields.Many2one(
        "label.material",
        string="Potisk (TTR)",
        domain="[('group_id.is_addon', '=', True), "
               "('group_id.material_type', '=', 'length')]",
    )

    label_addon_ids = fields.Many2many(
        "label.material",
        "sale_line_addon_material_rel",
        "line_id",
        "material_id",
        string="Příplatky",
        domain="[('group_id.is_addon', '=', True), "
               "('group_id.material_type', '!=', 'length')]",
    )

    label_calculated_price = fields.Float(
        string="Kalkulovaná cena/ks",
        digits=(12, 2),
        readonly=True,
    )

    label_price_breakdown = fields.Text(
        string="Rozpad ceny",
        readonly=True,
    )

    label_last_price = fields.Float(
        string="Minulá cena/ks",
        digits=(12, 2),
        readonly=True,
    )
    label_last_order_ref = fields.Char(
        string="Minulá objednávka",
        readonly=True,
    )

    label_material_cost_only = fields.Float(
        string="Náklad materiálu/ks",
        digits=(12, 4),
        readonly=True,
        help="Čistý náklad na materiál jednoho štítku (bez práce a marže). "
             "Pod touto cenou dotujete materiál.",
    )

    # === Onchange: výběr produktu ===

    @api.onchange("product_template_id")
    def _onchange_product_template_label(self):
        if self.pricing_type == "calculator":
            tmpl = self.product_template_id
            if tmpl.label_default_material_id:
                self.label_material_id = tmpl.label_default_material_id
            else:
                self.label_material_id = False
            self.label_width_mm = 0
            self.label_height_mm = 0
            self.label_ttr_material_id = False
            self.label_addon_ids = [(5, 0, 0)]
            self.label_is_repeat_design = False
            self.label_calculated_price = 0
            self.label_price_breakdown = ""
            self.label_last_price = 0
            self.label_last_order_ref = ""
            self.label_material_cost_only = 0
        else:
            self.label_material_id = False
            self.label_width_mm = 0
            self.label_height_mm = 0
            self.label_ttr_material_id = False
            self.label_addon_ids = [(5, 0, 0)]
            self.label_is_repeat_design = False
            self.label_calculated_price = 0
            self.label_price_breakdown = ""
            self.label_material_cost_only = 0
    # === Onchange: výběr materiálu ===

    @api.onchange("label_material_id")
    def _onchange_material(self):
        if self.label_material_id:
            mat = self.label_material_id
            if mat.material_type == "length" and mat.roll_width_mm:
                self.label_width_mm = mat.roll_width_mm
            self._find_last_price()
        else:
            self.label_width_mm = 0
            self.label_height_mm = 0

    # === Onchange: auto-kalkulace ===

    @api.onchange(
        "label_material_id",
        "label_width_mm",
        "label_height_mm",
        "product_uom_qty",
        "label_is_repeat_design",
        "label_ttr_material_id",
        "label_addon_ids",
    )
    def _onchange_label_calculate(self):
        if self.pricing_type != "calculator":
            return
        if not self.label_material_id:
            self.label_calculated_price = 0
            self.label_price_breakdown = ""
            return
        if not self.label_height_mm or not self.product_uom_qty:
            return

        result = self._run_calculation()
        self.label_material_cost_only = result.get("material_cost_only", 0)
        if not result:
            return

        self.label_calculated_price = result["unit_price"]
        self.price_unit = result["unit_price"]
        self.label_price_breakdown = self._format_breakdown(result)

        desc = self._get_label_description()
        if desc:
            self.name = desc

    def _run_calculation(self):
        """Spustí kalkulaci a vrátí výsledek."""
        addon_ids = []
        if self.label_ttr_material_id:
            addon_ids.append(self.label_ttr_material_id.id)
        if self.label_addon_ids:
            addon_ids.extend(self.label_addon_ids.ids)

        calc = self.env["label.calculator"]
        return calc.compute_price(
            material_id=self.label_material_id.id,
            width_mm=self.label_width_mm or 0,
            height_mm=self.label_height_mm or 0,
            quantity=int(self.product_uom_qty or 1),
            is_repeat_design=self.label_is_repeat_design,
            addon_material_ids=addon_ids or None,
        )

    def _format_breakdown(self, result):
        """Formátuje rozpad ceny."""
        bd = result.get("breakdown", {})
        main = bd.get("main", {})
        lines = []

        mat_cost = main.get("material_cost", 0)
        labor_cost = main.get("labor_cost", 0)
        admin_cost = main.get("admin_cost", 0)
        machine_cost = main.get("machine_cost", 0)
        pcs_per_hour = main.get("pcs_per_hour", 0)
        machine_name = main.get("machine_name", "")

        lines.append(f"Materiál: {mat_cost:.4f} Kč")
        lines.append(f"Práce: {labor_cost:.4f} Kč ({pcs_per_hour:.0f} ks/hod)")
        if admin_cost > 0:
            lines.append(f"Admin: {admin_cost:.4f} Kč")
        if machine_cost > 0:
            lines.append(f"Stroj ({machine_name}): {machine_cost:.4f} Kč")

        for addon in bd.get("addons", []):
            lines.append(
                f"+ {addon['material_name']}: {addon.get('subtotal', 0):.4f} Kč"
            )

        lines.append(f"─────────────────")
        lines.append(f"CELKEM: {result['unit_price']:.2f} Kč/ks")
        lines.append(
            f"Tier: {result.get('tier_name', '?')} | "
            f"Marže: {result.get('margin_pct', 0):.0f}%"
        )

        warnings = result.get("warnings", [])
        for w in warnings:
            if w["type"] != "error":
                lines.append(f"⚠️ {w['message']}")

        return "\n".join(lines)

    def _find_last_price(self):
        if not self.label_material_id or not self.order_id.partner_id:
            return
        last_line = self.env["sale.order.line"].search(
            [
                ("order_id.partner_id", "=", self.order_id.partner_id.id),
                ("label_material_id", "=", self.label_material_id.id),
                ("order_id.state", "in", ["sale", "done"]),
                ("id", "!=", self._origin.id if self._origin else 0),
            ],
            order="create_date desc",
            limit=1,
        )
        if last_line:
            self.label_last_price = last_line.price_unit
            self.label_last_order_ref = last_line.order_id.name
        else:
            self.label_last_price = 0
            self.label_last_order_ref = ""

    def _get_label_description(self):
        self.ensure_one()
        if self.pricing_type != "calculator" or not self.label_material_id:
            return ""
        mat = self.label_material_id
        parts = [mat.display_name]
        w = self.label_width_mm
        h = self.label_height_mm
        if w and h:
            parts.append(f"{w:.0f}×{h:.0f}mm")
        elif h:
            parts.append(f"{h:.0f}mm")
        if self.label_ttr_material_id:
            parts.append(
                f"potisk: {self.label_ttr_material_id.color_name or self.label_ttr_material_id.name}"
            )
        for addon in self.label_addon_ids:
            parts.append(f"+ {addon.display_name}")
        return ", ".join(parts)
