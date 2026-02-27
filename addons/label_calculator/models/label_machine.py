from odoo import models, fields, api


class LabelMachine(models.Model):
    _name = "label.machine"
    _description = "Výrobní stroj"
    _order = "name"

    name = fields.Char(string="Název stroje", required=True)
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
    working_days_per_week = fields.Selection(
        [("5", "5 dní (Po–Pá)"), ("6", "6 dní (Po–So)"), ("7", "7 dní")],
        string="Pracovní dny v týdnu",
        default="5",
        required=True,
    )
    hours_per_day = fields.Float(
        string="Hodin denně na stroji",
        default=6,
        required=True,
    )
    weeks_per_year = fields.Float(
        string="Pracovních týdnů v roce",
        default=50,
    )

    working_days_per_year = fields.Float(
        string="Pracovních dní/rok",
        compute="_compute_amortization",
        store=True,
    )
    hours_per_year = fields.Float(
        string="Hodin/rok",
        compute="_compute_amortization",
        store=True,
    )
    total_lifetime_hours = fields.Float(
        string="Celkem hodin za životnost",
        compute="_compute_amortization",
        store=True,
    )
    hourly_amortization = fields.Float(
        string="Amortizace (Kč/hod)",
        digits=(12, 4),
        compute="_compute_amortization",
        store=True,
    )
    daily_amortization = fields.Float(
        string="Amortizace (Kč/den)",
        digits=(12, 2),
        compute="_compute_amortization",
        store=True,
    )

    notes = fields.Text(string="Poznámky")

    @api.depends(
        "purchase_price", "lifetime_years",
        "working_days_per_week", "hours_per_day", "weeks_per_year",
    )
    def _compute_amortization(self):
        for m in self:
            dpw = int(m.working_days_per_week or 5)
            dpy = dpw * m.weeks_per_year
            hpy = dpy * m.hours_per_day
            total_h = m.lifetime_years * hpy

            m.working_days_per_year = dpy
            m.hours_per_year = hpy
            m.total_lifetime_hours = total_h
            m.hourly_amortization = m.purchase_price / total_h if total_h else 0

            total_d = m.lifetime_years * dpy
            m.daily_amortization = m.purchase_price / total_d if total_d else 0
