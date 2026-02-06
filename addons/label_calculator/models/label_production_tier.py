from odoo import models, fields


class LabelProductionTier(models.Model):
    _name = "label.production.tier"
    _description = "Množstevní hladina výroby"
    _order = "min_quantity"

    name = fields.Char(
        string="Název hladiny",
        required=True,
        help="Např. 'Malá série', 'Velkoobjem'",
    )
    active = fields.Boolean(default=True)

    min_quantity = fields.Integer(
        string="Od (ks)",
        required=True,
    )
    max_quantity = fields.Integer(
        string="Do (ks)",
        required=True,
        help="Zadej 0 pro neomezeně (999999)",
    )
    pieces_per_hour = fields.Float(
        string="Výkon (ks/hod)",
        required=True,
        help="Kolik kusů zvládneš vyrobit za hodinu v této hladině",
    )
    waste_test_pieces = fields.Integer(
        string="Testovací odpad (ks)",
        default=0,
        help="Počet kusů na testování a nastavení (pro NOVÝ design). "
             "U opakované výroby se nastaví na 0.",
    )

    waste_test_percentage = fields.Float(
        string="Testovací odpad (%)",
        digits=(5, 2),
        help="Kolik procent z celkové zakázky odhadujete jako odpad pro testování a nastavení.",
    )

    waste_pruning_percentage = fields.Float(
        string="Ořezový odpad (%)",
        digits=(5, 2),
        help="Kolik procent z celkové zakázky odhadujete jako odpad pro ořez.",
    )

    notes = fields.Text(
        string="Poznámky",
    )
