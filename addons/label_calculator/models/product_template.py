from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pricing_type = fields.Selection(
        [
            ("fixed", "Fixní cena"),
            ("calculator", "Kalkulačka štítků"),
        ],
        string="Typ cenotvorby",
        default="fixed",
    )

    label_material_group_id = fields.Many2one(
        "label.material.group",
        string="Skupina materiálů",
        domain=[("is_addon", "=", False)],
    )

    label_default_material_id = fields.Many2one(
        "label.material",
        string="Výchozí varianta",
    )

    @api.onchange("pricing_type")
    def _onchange_pricing_type(self):
        """Při změně typu cenotvorby vynuluj kalkulační pole."""
        if self.pricing_type != "calculator":
            self.label_material_group_id = False
            self.label_default_material_id = False

    @api.onchange("label_material_group_id")
    def _onchange_material_group(self):
        """Při změně skupiny vynuluj výchozí variantu."""
        self.label_default_material_id = False
