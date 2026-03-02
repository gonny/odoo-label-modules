from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipping_packeta_api_password = fields.Char(
        string="Packeta API Password",
        config_parameter="label_shipping.packeta_api_password",
    )
    shipping_packeta_indication = fields.Char(
        string="Packeta Indication (eshop)",
        config_parameter="label_shipping.packeta_indication",
        default="Etiketou",
    )
    shipping_dpd_api_key = fields.Char(
        string="DPD API Key",
        config_parameter="label_shipping.dpd_api_key",
    )
    shipping_dpd_api_dsw = fields.Char(
        string="DPD API DSW",
        config_parameter="label_shipping.dpd_api_dsw",
    )
    shipping_dpd_test_mode = fields.Boolean(
        string="DPD Test Mode",
        config_parameter="label_shipping.dpd_test_mode",
        default=True,
    )
