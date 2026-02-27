from odoo import models, fields, api


class LabelMaterialGroup(models.Model):
    _name = "label.material.group"
    _description = "Skupina materiálů"
    _order = "sequence, name"

    name = fields.Char(string="Název skupiny", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    material_type = fields.Selection(
        [
            ("area", "Plošný (mm²) – hliník, koženka..."),
            ("length", "Délkový (mm) – stuha, TTR páska..."),
            ("time", "Časový (s) – heat press, sušení..."),
            ("pieces", "Kusový (ks) – nýt, kroužek..."),
        ],
        string="Typ výpočtu",
        required=True,
        default="area",
    )

    is_addon = fields.Boolean(
        string="Příplatkový materiál",
        default=False,
        help="True = přidává se k hlavnímu materiálu. "
             "Nepočítá se práce ani admin – jen materiálové náklady "
             "(a amortizace stroje, pokud je přiřazen).",
    )

    default_margin_pct = fields.Float(
        string="Výchozí marže (%)",
        digits=(5, 2),
        help="Fallback marže, pokud tier nemá vlastní. "
             "Pokud 0, použije se globální nastavení.",
    )

    machine_id = fields.Many2one(
        "label.machine",
        string="Stroj",
        help="Stroj používaný pro výrobu z tohoto materiálu. "
             "Amortizace se zahrne do kalkulace.",
    )

    material_ids = fields.One2many(
        "label.material", "group_id", string="Materiály",
    )
    tier_ids = fields.One2many(
        "label.production.tier", "group_id", string="Množstevní hladiny",
    )

    material_count = fields.Integer(
        compute="_compute_counts",
    )
    tier_count = fields.Integer(
        compute="_compute_counts",
    )

    @api.depends("material_ids", "tier_ids")
    def _compute_counts(self):
        for g in self:
            g.material_count = len(g.material_ids)
            g.tier_count = len(g.tier_ids)

    def get_effective_margin(self, tier=None):
        """Vrátí efektivní marži: tier → skupina → globální."""
        self.ensure_one()
        if tier and tier.margin_pct:
            return tier.margin_pct
        if self.default_margin_pct:
            return self.default_margin_pct
        return float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("label_calc.material_margin_pct", 30)
        )
