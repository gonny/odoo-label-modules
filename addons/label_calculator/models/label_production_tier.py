from odoo import models, fields


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

    notes = fields.Text(string="Poznámky")
