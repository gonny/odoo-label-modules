from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LabelPricingProfile(models.Model):
    """Cenový profil pro rozlišení standardních a VIP zákazníků.

    Každý profil sdružuje sadu množstevních hladin (tiers).
    Standardní zákazníci používají profil 'standard',
    VIP zákazníci používají profily 'vip1', 'vip2' atd.
    """

    _name = "label.pricing.profile"
    _description = "Cenový profil"
    _order = "sequence, name"

    name = fields.Char(string="Název", required=True)
    code = fields.Char(
        string="Kód",
        required=True,
        help="Programatický identifikátor (např. 'standard', 'vip1').",
    )
    is_default = fields.Boolean(
        string="Výchozí profil",
        default=False,
        help="Výchozí profil se použije pro standardní zákazníky.",
    )
    is_vip = fields.Boolean(
        string="VIP profil",
        default=False,
        help="VIP profily neposkytují zákaznickou slevu.",
    )
    description = fields.Text(string="Popis")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    tier_ids = fields.One2many(
        "label.production.tier",
        "pricing_profile_id",
        string="Množstevní hladiny",
    )
    tier_count = fields.Integer(
        string="Počet hladin",
        compute="_compute_tier_count",
    )

    @api.depends("tier_ids")
    def _compute_tier_count(self):
        """Spočítá počet hladin přiřazených k profilu."""
        for profile in self:
            profile.tier_count = len(profile.tier_ids)

    def action_view_tiers(self):
        """Otevře seznam hladin přiřazených k tomuto profilu."""
        self.ensure_one()
        return {
            "name": f"Hladiny – {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "label.production.tier",
            "view_mode": "list,form",
            "domain": [("pricing_profile_id", "=", self.id)],
            "context": {"default_pricing_profile_id": self.id},
        }

    @api.constrains("is_default")
    def _check_single_default(self):
        """Zajistí, že existuje maximálně jeden výchozí profil."""
        for profile in self:
            if profile.is_default:
                other_default = self.search(
                    [
                        ("is_default", "=", True),
                        ("id", "!=", profile.id),
                    ]
                )
                if other_default:
                    raise ValidationError(
                        "Může existovat pouze jeden výchozí cenový profil. "
                        f"Profil '{other_default[0].name}' je již nastaven "
                        "jako výchozí."
                    )
