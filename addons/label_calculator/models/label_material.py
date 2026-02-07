from odoo import models, fields, api


class LabelMaterial(models.Model):
    _name = "label.material"
    _description = "Materiál – varianta (barva, tloušťka...)"
    _order = "group_id, name, color_name"

    name = fields.Char(
        string="Název",
        required=True,
        help="Např. '0.5mm', '20mm', '40s ×1'",
    )
    active = fields.Boolean(default=True)

    group_id = fields.Many2one(
        "label.material.group",
        string="Skupina",
        required=True,
        ondelete="cascade",
    )
    material_type = fields.Selection(
        related="group_id.material_type",
        store=True,
        readonly=True,
    )

    # === Barva ===
    color_name = fields.Char(string="Barva / varianta")
    color_hex = fields.Char(string="Barva (hex)")

    # === Nákupní cena a DPH ===
    purchase_price = fields.Float(
        string="Nákupní cena",
        digits=(12, 4),
        help="Cena od dodavatele (s nebo bez DPH – viz příznak níže)",
    )
    purchase_vat_included = fields.Boolean(
        string="Cena je s DPH",
        default=True,
        help="Zaškrtni, pokud dodavatel uvádí cenu včetně DPH",
    )
    purchase_vat_pct = fields.Float(
        string="Sazba DPH (%)",
        default=21,
    )
    purchase_price_excl_vat = fields.Float(
        string="Cena bez DPH",
        digits=(12, 4),
        compute="_compute_vat_prices",
        store=True,
    )
    purchase_price_incl_vat = fields.Float(
        string="Cena s DPH",
        digits=(12, 4),
        compute="_compute_vat_prices",
        store=True,
    )

    # === Rozměry zdroje (tabule, role) ===
    # area: tabule/arch
    sheet_width_mm = fields.Float(
        string="Šířka tabule (mm)",
        digits=(10, 1),
        help="Pro plošný materiál – šířka nakupované tabule/archu",
    )
    sheet_height_mm = fields.Float(
        string="Výška tabule (mm)",
        digits=(10, 1),
        help="Pro plošný materiál – výška nakupované tabule/archu",
    )
    thickness_mm = fields.Float(
        string="Tloušťka (mm)",
        digits=(6, 2),
    )

    # length: role (stuha i TTR)
    roll_width_mm = fields.Float(
        string="Šířka role (mm)",
        digits=(6, 1),
        help="Fixní šířka role – zákazník nemůže objednat menší",
    )
    roll_length_m = fields.Float(
        string="Délka role (m)",
        digits=(8, 1),
    )

    # time: heat press
    time_seconds = fields.Float(
        string="Čas na kus (s)",
        digits=(8, 1),
    )
    time_multiplier = fields.Integer(
        string="Počet opakování",
        default=1,
    )

    # pieces: komponenty
    component_price = fields.Float(
        string="Cena za kus (Kč)",
        digits=(12, 4),
    )

    # === Computed jednotkové ceny ===
    price_per_mm2 = fields.Float(
        string="Cena/mm²",
        digits=(12, 10),
        compute="_compute_unit_prices",
        store=True,
    )
    price_per_mm_length = fields.Float(
        string="Cena/mm délky",
        digits=(12, 8),
        compute="_compute_unit_prices",
        store=True,
    )
    price_per_second = fields.Float(
        string="Cena/s (amortizace)",
        digits=(12, 8),
        compute="_compute_unit_prices",
        store=True,
    )

    # === Výroba ===
    production_notes = fields.Text(string="Výrobní poznámky")

    # === Tier overrides ===
    tier_override_ids = fields.One2many(
        "label.material.tier.override", "material_id",
        string="Přetížení hladin",
    )

    @api.depends("purchase_price", "purchase_vat_included", "purchase_vat_pct")
    def _compute_vat_prices(self):
        for mat in self:
            vat_rate = mat.purchase_vat_pct / 100 if mat.purchase_vat_pct else 0
            if mat.purchase_vat_included:
                mat.purchase_price_incl_vat = mat.purchase_price
                mat.purchase_price_excl_vat = (
                    mat.purchase_price / (1 + vat_rate) if vat_rate else mat.purchase_price
                )
            else:
                mat.purchase_price_excl_vat = mat.purchase_price
                mat.purchase_price_incl_vat = mat.purchase_price * (1 + vat_rate)

    @api.depends(
        "material_type",
        "purchase_price_incl_vat",
        "sheet_width_mm", "sheet_height_mm",
        "roll_width_mm", "roll_length_m",
        "group_id.machine_id",
        "group_id.machine_id.hourly_amortization",
    )
    def _compute_unit_prices(self):
        for mat in self:
            mat.price_per_mm2 = 0
            mat.price_per_mm_length = 0
            mat.price_per_second = 0

            price = mat.purchase_price_incl_vat or 0

            if mat.material_type == "area":
                # Tabule: cena / (šířka × výška) = cena za mm²
                if mat.sheet_width_mm and mat.sheet_height_mm and price:
                    area_mm2 = mat.sheet_width_mm * mat.sheet_height_mm
                    mat.price_per_mm2 = price / area_mm2

            elif mat.material_type == "length":
                # Role: cena / (délka v mm) = cena za mm délky
                if mat.roll_length_m and price:
                    length_mm = mat.roll_length_m * 1_000
                    mat.price_per_mm_length = price / length_mm

            elif mat.material_type == "time":
                # Čas: amortizace stroje / 3600 = cena za sekundu
                machine = mat.group_id.machine_id
                if machine and machine.hourly_amortization:
                    mat.price_per_second = machine.hourly_amortization / 3600

    def get_unit_cost(self, width_mm=0, height_mm=0, quantity=1):
        """Vrátí materiálovou cenu za 1 ks (bez marže, bez odpadů)."""
        self.ensure_one()
        if self.material_type == "area":
            return width_mm * height_mm * self.price_per_mm2
        elif self.material_type == "length":
            # Délkový: jen délka (výška etikety), šířka je fixní z role
            return height_mm * self.price_per_mm_length
        elif self.material_type == "time":
            seconds = self.time_seconds * (self.time_multiplier or 1)
            return seconds * self.price_per_second
        elif self.material_type == "pieces":
            return self.component_price
        return 0

    def name_get(self):
        result = []
        for mat in self:
            parts = [mat.group_id.name or "", mat.name or ""]
            if mat.color_name:
                parts.append(mat.color_name)
            if mat.material_type == "time" and mat.time_seconds:
                time_str = f"{mat.time_seconds:.0f}s"
                if mat.time_multiplier and mat.time_multiplier > 1:
                    time_str += f" ×{mat.time_multiplier}"
                parts.append(time_str)
            result.append((mat.id, " – ".join(filter(None, parts))))
        return result
