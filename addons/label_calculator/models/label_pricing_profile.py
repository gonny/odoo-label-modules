from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LabelPricingProfile(models.Model):
    _name = "label.pricing.profile"
    _description = "Cenový profil zákazníka"
    _order = "sequence, id"

    name = fields.Char(string="Název", required=True)
    code = fields.Char(
        string="Kód",
        required=True,
        help="Programový identifikátor (standard, vip1, vip2)",
    )
    is_default = fields.Boolean(string="Výchozí profil", default=False)
    is_vip = fields.Boolean(
        string="VIP profil",
        default=False,
        help="VIP zákazníci nezískávají zákaznické slevy (Bronz/Stříbro/Zlato)",
    )
    description = fields.Text(string="Popis")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string="Pořadí", default=10)
    tier_ids = fields.One2many(
        "label.production.tier",
        "pricing_profile_id",
        string="Výrobní hladiny",
    )
    tier_count = fields.Integer(
        string="Počet hladin",
        compute="_compute_tier_count",
    )

    @api.depends("tier_ids")
    def _compute_tier_count(self):
        """Compute the number of production tiers linked to this profile."""
        for profile in self:
            profile.tier_count = len(profile.tier_ids)

    @api.constrains("is_default")
    def _check_single_default(self):
        """Ensure at most one pricing profile is marked as the default."""
        if any(profile.is_default for profile in self):
            duplicates = self.search([
                ("is_default", "=", True),
                ("id", "not in", self.ids),
            ])
            if duplicates:
                raise ValidationError(
                    "Pouze jeden cenový profil může být nastaven jako výchozí. "
                    f"Profil '{duplicates[0].name}' je již výchozí."
                )
