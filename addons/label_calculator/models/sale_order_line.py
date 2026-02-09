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

    label_material_cost_only = fields.Float(
        string="Náklad materiálu/ks",
        digits=(12, 4),
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

    # === CRUD: přepočítat breakdown při uložení ===

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.pricing_type == "calculator" and line.label_material_id:
                line._recompute_label_fields()
        return lines

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {
            "label_material_id", "label_width_mm", "label_height_mm",
            "product_uom_qty", "label_is_repeat_design",
            "label_ttr_material_id", "label_addon_ids",
            "product_template_id",
        }
        if trigger_fields & set(vals.keys()):
            for line in self:
                if line.pricing_type == "calculator" and line.label_material_id:
                    line._recompute_label_fields()
        return res

    def _recompute_label_fields(self):
        """Přepočítá kalkulační pole a uloží do DB."""
        self.ensure_one()
        result = self._run_calculation()
        if not result or not result.get("breakdown"):
            return

        vals = {
            "label_calculated_price": result["unit_price"],
            "label_material_cost_only": result.get("material_cost_only", 0),
            "label_price_breakdown": self._format_breakdown(result),
            "price_unit": result["unit_price"],
        }

        desc = self._get_label_description()
        if desc:
            vals["name"] = desc

        # Přímý SQL update aby se vyhnul rekurzi
        super(SaleOrderLine, self).write(vals)

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
            self.label_material_cost_only = 0
            return
        if not self.label_height_mm or not self.product_uom_qty:
            return

        result = self._run_calculation()
        if not result:
            return

        self.label_calculated_price = result["unit_price"]
        self.price_unit = result["unit_price"]
        self.label_material_cost_only = result.get("material_cost_only", 0)
        self.label_price_breakdown = self._format_breakdown(result)

        desc = self._get_label_description()
        if desc:
            self.name = desc

    # === Pomocné metody ===

    def _run_calculation(self):
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
        bd = result.get("breakdown", {})
        main = bd.get("main", {})
        lines = []

        mat_cost = main.get("material_cost", 0)
        mat_cost_raw = main.get("material_cost_raw", 0)
        labor_cost = main.get("labor_cost", 0)
        admin_cost = main.get("admin_cost", 0)
        machine_cost = main.get("machine_cost", 0)
        pcs_per_hour = main.get("pcs_per_hour", 0)
        machine_name = main.get("machine_name", "")

        lines.append("═══ HLAVNÍ MATERIÁL ═══")
        lines.append(f"  Materiál (s marží): {mat_cost:.4f} Kč")
        lines.append(f"  Materiál (náklad):  {mat_cost_raw:.4f} Kč")
        lines.append(f"  Práce:              {labor_cost:.4f} Kč ({pcs_per_hour:.0f} ks/hod)")
        if admin_cost > 0:
            lines.append(f"  Admin overhead:     {admin_cost:.4f} Kč")
        if machine_cost > 0:
            lines.append(f"  Amortizace ({machine_name}): {machine_cost:.4f} Kč")

        addons = bd.get("addons", [])
        if addons:
            lines.append("")
            lines.append("═══ PŘÍPLATKY ═══")
            for addon in addons:
                addon_mat = addon.get("material_cost", 0)
                addon_mach = addon.get("machine_cost", 0)
                addon_sub = addon.get("subtotal", 0)
                lines.append(f"  {addon['material_name']}:")
                if addon.get("type") == "addon_time":
                    secs = addon.get("time_seconds", 0)
                    lines.append(f"    Čas: {secs:.0f}s × amortizace = {addon_mach:.4f} Kč")
                else:
                    if addon_mat > 0:
                        lines.append(f"    Materiál: {addon_mat:.4f} Kč")
                    if addon_mach > 0:
                        lines.append(f"    Amortizace: {addon_mach:.4f} Kč")
                lines.append(f"    Subtotal: {addon_sub:.4f} Kč")

        lines.append("")
        lines.append("═══ SOUHRN ═══")
        lines.append(f"  Tier:    {result.get('tier_name', '?')}")
        lines.append(f"  Marže:   {result.get('margin_pct', 0):.0f}%")
        lines.append(f"  Náklad:  {result.get('material_cost_only', 0):.4f} Kč/ks")
        lines.append(f"  ─────────────────")

        unit_raw = result.get("unit_price_raw", 0)
        unit_final = result["unit_price"]
        if unit_raw and abs(unit_raw - unit_final) > 0.001:
            lines.append(f"  Před zaokr.: {unit_raw:.4f} Kč/ks")
            lines.append(f"  CENA:        {unit_final:.2f} Kč/ks (↑ 10 hal.)")
        else:
            lines.append(f"  CENA:    {unit_final:.2f} Kč/ks")
        lines.append(f"  CELKEM:  {result['total_price']:.2f} Kč")

        warnings = result.get("warnings", [])
        if warnings:
            lines.append("")
            lines.append("═══ VAROVÁNÍ ═══")
            for w in warnings:
                if w["type"] != "error":
                    lines.append(f"  ⚠️ {w['message']}")

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
