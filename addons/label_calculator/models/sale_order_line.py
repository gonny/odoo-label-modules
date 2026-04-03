import logging

from odoo import api, fields, models

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
        string="Bez testovacích kusů",
        default=False,
        help="Zaškrtni pokud design už byl ověřen a není potřeba "
        "testovací kusy. Sníží náklad na materiál.",
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
        help="Čistý náklad na materiál jednoho štítku (bez práce a marže). "
        "Pod touto cenou dotujete materiál.",
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

    label_order_display = fields.Char(
        string="Objednávka",
        compute="_compute_order_display",
        store=True,
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
        # Skip recalculation when this write is triggered by a currency conversion
        # update from SaleOrder.write() – the CZK price doesn't change, only price_unit
        if self.env.context.get("label_currency_conversion_only"):
            return res
        trigger_fields = {
            "label_material_id",
            "label_width_mm",
            "label_height_mm",
            "product_uom_qty",
            "label_is_repeat_design",
            "label_ttr_material_id",
            "label_addon_ids",
            "product_template_id",
        }
        if trigger_fields & set(vals.keys()):
            for line in self:
                if line.pricing_type == "calculator" and line.label_material_id:
                    line._recompute_label_fields()
        return res

    def _get_pricelist_price(self):
        """Return the pricelist price for this line.

        For calculator lines that have been computed, return the stored CZK
        price converted to the order currency instead of looking up the product
        pricelist (which would return 0 because list_price = 0).

        This ensures the "Update Prices" button does not zero out calculator lines.
        Falls back to standard pricelist logic for non-calculator lines or when
        no calculation has been performed yet.
        """
        if (
            self.pricing_type == "calculator"
            and self.label_calculated_price
            and self.label_material_id
        ):
            return self._convert_price_to_order_currency(
                self.label_calculated_price,
            )
        return super()._get_pricelist_price()

    def _recompute_label_fields(self):
        """Přepočítá kalkulační pole a uloží do DB."""
        self.ensure_one()
        if not self.label_material_id or not self.label_height_mm:
            return

        result = self._run_calculation()
        if not result or not result.get("breakdown"):
            return

        vals = {
            # label_calculated_price always stores CZK value
            "label_calculated_price": result["unit_price"],
            "label_material_cost_only": result.get("material_cost_only", 0),
            "label_price_breakdown": self._format_breakdown(result),
            # price_unit stores value in order currency (converted if needed)
            "price_unit": self._convert_price_to_order_currency(
                result["unit_price"],
            ),
        }

        desc = self._get_label_description()
        if desc:
            vals["name"] = desc

        # Přímý SQL update aby se vyhnul rekurzi
        super(SaleOrderLine, self).write(vals)

    # === Vlastní computed pole pro groupované zobrazení historie nabídek zákazníka ===
    @api.depends("order_id", "order_id.name", "order_id.create_date")
    def _compute_order_display(self):
        for line in self:
            if line.order_id and line.order_id.create_date:
                date_str = line.order_id.create_date.strftime("%d.%m.%Y")
                line.label_order_display = f"{line.order_id.name} – {date_str}"
            elif line.order_id:
                line.label_order_display = line.order_id.name
            else:
                line.label_order_display = ""

    # === Přidání auto discountu z partnerovy hladiny do kalkulace ===
    @api.onchange("product_template_id", "label_material_id")
    def _onchange_apply_partner_discount(self):
        """Automaticky vyplní slevu z hladiny zákazníka.

        VIP zákazníci nemají slevu – discount = 0.
        """
        if self.pricing_type != "calculator":
            return
        partner = self.order_id.partner_id
        if not partner:
            return
        if partner.label_is_vip:
            self.discount = 0
        elif partner.label_effective_discount > 0:
            self.discount = partner.label_effective_discount

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

        # label_calculated_price always stores CZK value (original calculation)
        self.label_calculated_price = result["unit_price"]
        # price_unit stores value in order currency (converted if needed)
        self.price_unit = self._convert_price_to_order_currency(
            result["unit_price"],
        )
        self.label_material_cost_only = result.get("material_cost_only", 0)
        self.label_price_breakdown = self._format_breakdown(result)

        desc = self._get_label_description()
        if desc:
            self.name = desc

    # === Kopírování z historie ===

    def action_copy_to_current_order(self):
        """Zkopíruje parametry tohoto řádku do aktuální objednávky."""
        self.ensure_one()

        order_id = self.env.context.get("active_order_id")
        if not order_id:
            partner = self.order_id.partner_id
            if partner:
                draft_order = self.env["sale.order"].search(
                    [
                        ("partner_id", "=", partner.id),
                        ("state", "=", "draft"),
                    ],
                    order="create_date desc",
                    limit=1,
                )
                if draft_order:
                    order_id = draft_order.id

        if not order_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Chyba",
                    "message": "Nenalezena otevřená objednávka pro kopírování. "
                    "Nejdřív vytvořte novou nabídku pro tohoto zákazníka.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        order = self.env["sale.order"].browse(order_id)
        if not order.exists() or order.state != "draft":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Chyba",
                    "message": "Objednávka musí být ve stavu 'Nabídka' pro kopírování.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        addon_ids = (
            [(6, 0, self.label_addon_ids.ids)] if self.label_addon_ids else [(5, 0, 0)]
        )

        # Zjisti slevu zákazníka (VIP = 0)
        discount = 0
        if order.partner_id:
            if order.partner_id.label_is_vip:
                discount = 0
            elif order.partner_id.label_effective_discount > 0:
                discount = order.partner_id.label_effective_discount

        vals = {
            "order_id": order.id,
            "product_id": self.product_id.id,
            "product_template_id": self.product_template_id.id,
            "product_uom_qty": self.product_uom_qty,
            "label_material_id": (
                self.label_material_id.id if self.label_material_id else False
            ),
            "label_width_mm": self.label_width_mm,
            "label_height_mm": self.label_height_mm,
            "label_ttr_material_id": (
                self.label_ttr_material_id.id if self.label_ttr_material_id else False
            ),
            "label_addon_ids": addon_ids,
            "label_is_repeat_design": True,
            "discount": discount,
        }

        self.env["sale.order.line"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    # === Pomocné metody ===

    def _convert_price_to_order_currency(self, company_price):
        """Convert price from company currency to order currency.

        If the order uses the same currency as the company, returns the price
        unchanged. Otherwise uses Odoo's built-in currency conversion with
        the order date as reference.

        Args:
            company_price: Unit price in company currency.

        Returns:
            Price converted to the order's currency.
        """
        self.ensure_one()
        company_currency = self.env.company.currency_id
        order_currency = self.order_id.currency_id
        if not order_currency or order_currency == company_currency:
            return company_price
        return company_currency._convert(
            company_price,
            order_currency,
            self.env.company,
            self.order_id.date_order or fields.Date.today(),
        )

    def _run_calculation(self):
        """Spustí kalkulaci s přihlédnutím k cenovému profilu zákazníka."""
        addon_ids = []
        if self.label_ttr_material_id:
            addon_ids.append(self.label_ttr_material_id.id)
        if self.label_addon_ids:
            addon_ids.extend(self.label_addon_ids.ids)

        # Resolve pricing profile from partner
        profile_id = None
        if self.order_id.partner_id:
            partner = self.order_id.partner_id
            if partner.label_pricing_profile_id:
                profile_id = partner.label_pricing_profile_id.id

        calc = self.env["label.calculator"]
        return calc.compute_price(
            material_id=self.label_material_id.id,
            width_mm=self.label_width_mm or 0,
            height_mm=self.label_height_mm or 0,
            quantity=int(self.product_uom_qty or 1),
            is_repeat_design=self.label_is_repeat_design,
            addon_material_ids=addon_ids or None,
            pricing_profile_id=profile_id,
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
        lines.append(
            f"  Práce:              {labor_cost:.4f} Kč " f"({pcs_per_hour:.0f} ks/hod)"
        )
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
                    lines.append(
                        f"    Čas: {secs:.0f}s × amortizace = " f"{addon_mach:.4f} Kč"
                    )
                else:
                    if addon_mat > 0:
                        lines.append(f"    Materiál: {addon_mat:.4f} Kč")
                    if addon_mach > 0:
                        lines.append(f"    Amortizace: {addon_mach:.4f} Kč")
                lines.append(f"    Subtotal: {addon_sub:.4f} Kč")

        lines.append("")
        lines.append("═══ SOUHRN ═══")
        profile_name = result.get("pricing_profile_name", "")
        if profile_name and profile_name != "Standard":
            lines.append(f"  Profil:  ⭐ {profile_name}")
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

    # Přenese pole definované v Prodej do Faktury, aby se zachoval rozpad ceny a informace o materiálu.
    def _prepare_invoice_line(self, **optional_values):
        """Přenese kalkulační pole na fakturu."""
        vals = super()._prepare_invoice_line(**optional_values)
        if self.pricing_type == "calculator":
            vals.update(
                {
                    "label_material_id": self.label_material_id.id,
                    "label_width_mm": self.label_width_mm,
                    "label_height_mm": self.label_height_mm,
                    "label_material_cost_only": self.label_material_cost_only,
                    "label_price_breakdown": self.label_price_breakdown,
                }
            )
        return vals
