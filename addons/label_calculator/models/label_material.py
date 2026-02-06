from odoo import models, fields, api


class LabelMaterial(models.Model):
    _name = "label.material"
    _description = "Materiál pro výrobu štítků"
    _order = "material_type, name"

    # === Základní info ===
    name = fields.Char(
        string="Název",
        required=True,
        help="Např. 'Koženka černá', 'Satén 20mm bílý'",
    )
    active = fields.Boolean(default=True)

    material_type = fields.Selection(
        [
            ("sheet", "Plošný materiál (gravírování)"),
            ("ribbon", "Stuha (textilní etikety)"),
            ("ttr", "TTR páska (termotransfer)"),
            ("component", "Komponenta (nýt, kroužek...)"),
        ],
        string="Typ materiálu",
        required=True,
        default="sheet",
    )

    # === Barva ===
    color_name = fields.Char(
        string="Barva",
        help="Název barvy, např. 'Černá', 'Zlatá'",
    )
    color_hex = fields.Char(
        string="Barva (hex)",
        help="Hex kód pro zobrazení, např. '#000000'",
    )

    # === Ceny dle typu materiálu ===

    # Plošný materiál (gravírování)
    price_per_m2 = fields.Float(
        string="Cena za m² (Kč)",
        digits=(12, 2),
        help="Nákupní cena za 1 m² materiálu",
    )
    thickness_mm = fields.Float(
        string="Tloušťka (mm)",
        digits=(6, 2),
    )

    # Stuha (textilní etikety)
    ribbon_width_mm = fields.Float(
        string="Šířka stuhy (mm)",
        digits=(6, 1),
    )
    price_per_meter = fields.Float(
        string="Cena za metr (Kč)",
        digits=(12, 4),
        help="Nákupní cena za 1 běžný metr stuhy",
    )

    # TTR páska
    ttr_width_mm = fields.Float(
        string="Šířka TTR (mm)",
        digits=(6, 1),
    )
    ttr_length_m = fields.Float(
        string="Délka role TTR (m)",
        digits=(8, 1),
    )
    ttr_price_per_roll = fields.Float(
        string="Cena za roli TTR (Kč)",
        digits=(12, 2),
    )

    # Komponenta (nýt, kroužek, díra...)
    component_price = fields.Float(
        string="Cena za kus (Kč)",
        digits=(12, 5),
    )

    # === Automaticky vypočtené jednotkové ceny ===
    price_per_mm2 = fields.Float(
        string="Cena za mm²",
        digits=(12, 10),
        compute="_compute_unit_prices",
        store=True,
        help="Automaticky vypočteno z ceny za m² nebo TTR role",
    )
    price_per_mm_length = fields.Float(
        string="Cena za mm délky",
        digits=(12, 8),
        compute="_compute_unit_prices",
        store=True,
        help="Automaticky vypočteno z ceny za metr stuhy",
    )

    # === Výrobní parametry ===
    laser_power_pct = fields.Float(
        string="Laser výkon (%)",
        help="Doporučený výkon laseru pro tento materiál/barvu",
    )
    laser_speed = fields.Float(
        string="Laser rychlost (mm/s)",
        help="Doporučená rychlost laseru",
    )
    production_notes = fields.Text(
        string="Výrobní poznámky",
        help="Jak se tento materiál chová při výrobě, na co si dát pozor",
    )

    @api.depends(
        "material_type",
        "price_per_m2",
        "price_per_meter",
        "ttr_price_per_roll",
        "ttr_length_m",
        "ttr_width_mm",
    )
    def _compute_unit_prices(self):
        for mat in self:
            mat.price_per_mm2 = 0
            mat.price_per_mm_length = 0

            if mat.material_type == "sheet" and mat.price_per_m2:
                # 1 m² = 1 000 000 mm²
                mat.price_per_mm2 = mat.price_per_m2 / 1_000_000

            elif mat.material_type == "ribbon" and mat.price_per_meter:
                # 1 m = 1 000 mm
                mat.price_per_mm_length = mat.price_per_meter / 1_000

            elif mat.material_type == "ttr":
                if mat.ttr_length_m and mat.ttr_width_mm and mat.ttr_price_per_roll:
                    # Celková plocha role v mm²
                    total_mm2 = mat.ttr_length_m * 1_000 * mat.ttr_width_mm
                    mat.price_per_mm2 = mat.ttr_price_per_roll / total_mm2

    def name_get(self):
        """Zobrazení v dropdownech: 'Satén 20mm – Černá'"""
        result = []
        for mat in self:
            name = mat.name
            if mat.color_name:
                name = f"{mat.name} – {mat.color_name}"
            result.append((mat.id, name))
        return result
