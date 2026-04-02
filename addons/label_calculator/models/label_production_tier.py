from odoo import models, fields, api


class LabelProductionTier(models.Model):
    _name = "label.production.tier"
    _description = "Množstevní hladina výroby"
    _order = "group_id, min_quantity"

    name = fields.Char(string="Název hladiny", required=True)
    active = fields.Boolean(default=True)

    group_id = fields.Many2one(
        "label.material.group",
        string="Skupina materiálů",
        required=True,
        ondelete="cascade",
    )

    min_quantity = fields.Integer(string="Od (ks)", required=True)
    max_quantity = fields.Integer(
        string="Do (ks)", required=True,
        help="Zadej 999999 pro neomezeně",
    )

    pieces_per_hour = fields.Float(
        string="Výkon (ks/hod)",
        required=True,
        help="Celkový výkon zahrnující VŠECHNY kroky výroby "
             "(tisk, press, postprocess, zatloukání nýtů...)",
    )

    margin_pct = fields.Float(
        string="Marže (%)",
        digits=(5, 2),
        help="Marže pro tuto hladinu. "
             "Pokud 0, použije se výchozí marže ze skupiny.",
    )

    waste_test_pieces = fields.Integer(
        string="Testovací odpad (ks)",
        default=0,
        help="Fixní počet kusů na test. U opakovaného designu = 0.",
    )
    waste_test_percentage = fields.Float(
        string="Testovací odpad (%)",
        digits=(5, 2),
        default=10,
    )
    waste_pruning_percentage = fields.Float(
        string="Ořezový odpad (%)",
        digits=(5, 2),
        default=10,
    )

    pricing_profile_id = fields.Many2one(
        "label.pricing.profile",
        string="Cenový profil",
        ondelete="restrict",
        default=lambda self: self.env["label.pricing.profile"].search(
            [("is_default", "=", True)], limit=1
        ),
        help="Cenový profil, ke kterému patří tato hladina.",
    )

    notes = fields.Text(string="Poznámky")

    # === Nové: přehled overrides ===
    override_ids = fields.One2many(
        "label.material.tier.override",
        "tier_id",
        string="Přetížení",
    )
    override_count = fields.Integer(
        string="Počet přetížení",
        compute="_compute_override_count",
    )
    override_summary = fields.Char(
        string="Přetížené materiály",
        compute="_compute_override_count",
    )

    @api.depends("override_ids")
    def _compute_override_count(self):
        for tier in self:
            overrides = tier.override_ids
            tier.override_count = len(overrides)
            if overrides:
                names = overrides.mapped(
                    lambda o: f"{o.material_id.color_name or o.material_id.name} → {o.pieces_per_hour_override:.0f}/hod"
                )
                tier.override_summary = ", ".join(names)
            else:
                tier.override_summary = ""
