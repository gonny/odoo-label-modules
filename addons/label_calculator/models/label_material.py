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

    # === Ceny dle typu ===

    # area (plošný)
    price_per_m2 = fields.Float(
        string="Cena za m² (Kč)", digits=(12, 2),
    )
    thickness_mm = fields.Float(
        string="Tloušťka (mm)", digits=(6, 2),
    )

    # length (stuha, TTR)
    ribbon_width_mm = fields.Float(
        string="Šířka role (mm)", digits=(6, 1),
        help="Fixní šířka – zákazník nemůže objednat menší",
    )
    price_per_meter = fields.Float(
        string="Cena za běžný metr (Kč)", digits=(12, 4),
    )
    # TTR specifické (length typ, ale cena se počítá z role)
    ttr_length_m = fields.Float(
        string="Délka role (m)", digits=(8, 1),
    )
    ttr_width_mm = fields.Float(
        string="Šířka role (mm)", digits=(6, 1),
    )
    ttr_price_per_roll = fields.Float(
        string="Cena za roli (Kč)", digits=(12, 2),
    )

    # time (heat press)
    time_seconds = fields.Float(
        string="Čas na kus (s)", digits=(8, 1),
        help="Např. 40s pro heat press, 600s pro předehřátí",
    )
    time_multiplier = fields.Integer(
        string="Počet opakování",
        default=1,
        help="Např. 3× press pro bavlněné štítky",
    )

    # pieces (komponenty)
    component_price = fields.Float(
        string="Cena za kus (Kč)", digits=(12, 4),
    )

    # === Computed jednotkové ceny ===
    price_per_mm2 = fields.Float(
        string="Cena/mm²", digits=(12, 10),
        compute="_compute_unit_prices", store=True,
    )
    price_per_mm_length = fields.Float(
        string="Cena/mm délky", digits=(12, 8),
        compute="_compute_unit_prices", store=True,
    )
    price_per_second = fields.Float(
        string="Cena/s (amortizace)", digits=(12, 8),
        compute="_compute_unit_prices", store=True,
    )

    # === Výroba ===
    production_notes = fields.Text(string="Výrobní poznámky")

    # === Tier overrides ===
    tier_override_ids = fields.One2many(
        "label.material.tier.override", "material_id",
        string="Přetížení hladin",
    )

    @api.depends(
        "material_type", "price_per_m2", "price_per_meter",
        "ttr_price_per_roll", "ttr_length_m", "ttr_width_mm",
        "group_id.machine_id", "group_id.machine_id.hourly_amortization",
    )
    def _compute_unit_prices(self):
        for mat in self:
            mat.price_per_mm2 = 0
            mat.price_per_mm_length = 0
            mat.price_per_second = 0

            if mat.material_type == "area" and mat.price_per_m2:
                mat.price_per_mm2 = mat.price_per_m2 / 1_000_000

            elif mat.material_type == "length":
                if mat.price_per_meter:
                    # Stuha: cena za metr → cena za mm
                    mat.price_per_mm_length = mat.price_per_meter / 1_000
                elif mat.ttr_price_per_roll and mat.ttr_length_m:
                    # TTR: cena za roli → cena za mm délky
                    total_mm = mat.ttr_length_m * 1_000
                    mat.price_per_mm_length = mat.ttr_price_per_roll / total_mm

            elif mat.material_type == "time":
                # Cena za sekundu = amortizace stroje / 3600
                machine = mat.group_id.machine_id
                if machine and machine.hourly_amortization:
                    mat.price_per_second = machine.hourly_amortization / 3600

    def get_unit_cost(self, width_mm=0, height_mm=0, quantity=1):
        """Vrátí materiálovou cenu za 1 ks (bez marže, DPH, odpadů)."""
        self.ensure_one()
        if self.material_type == "area":
            return width_mm * height_mm * self.price_per_mm2
        elif self.material_type == "length":
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
