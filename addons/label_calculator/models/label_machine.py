from odoo import models, fields, api


class LabelMachine(models.Model):
    _name = "label.machine"
    _description = "Výrobní stroj"
    _order = "name"

    name = fields.Char(
        string="Název stroje",
        required=True,
        help="Např. 'Laser CO2 60W', 'Tiskárna etiket Godex'",
    )
    active = fields.Boolean(default=True)

    purchase_price = fields.Float(
        string="Pořizovací cena (Kč)",
        digits=(12, 2),
        required=True,
    )
    lifetime_years = fields.Float(
        string="Životnost (roky)",
        required=True,
        default=5,
    )
    hours_per_day = fields.Float(
        string="Využití (hod/den)",
        required=True,
        default=8,
        help="Odhadovaný počet produktivních hodin za den",
    )

    # Automatický výpočet
    total_lifetime_hours = fields.Float(
        string="Celkem hodin za životnost",
        compute="_compute_amortization",
        store=True,
    )
    hourly_amortization = fields.Float(
        string="Amortizace (Kč/hod)",
        digits=(12, 2),
        compute="_compute_amortization",
        store=True,
    )

    notes = fields.Text(
        string="Poznámky",
        help="Údržba, servisní intervaly, spotřební materiál...",
    )

    @api.depends("purchase_price", "lifetime_years", "hours_per_day")
    def _compute_amortization(self):
        for machine in self:
            total = machine.lifetime_years * machine.hours_per_day * 365
            machine.total_lifetime_hours = total
            if total > 0:
                machine.hourly_amortization = machine.purchase_price / total
            else:
                machine.hourly_amortization = 0
