from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shipping_packeta_api_key = fields.Char(
        string="Packeta API Key",
        config_parameter="label_shipping.packeta_api_key",
    )
    shipping_packeta_api_password = fields.Char(
        string="Packeta API Password",
        config_parameter="label_shipping.packeta_api_password",
    )
    shipping_dpd_api_key = fields.Char(
        string="DPD API Key",
        config_parameter="label_shipping.dpd_api_key",
    )
    shipping_dpd_api_dsw = fields.Char(
        string="DPD API DSW",
        config_parameter="label_shipping.dpd_api_dsw",
    )
    shipping_czech_post_api_key = fields.Char(
        string="Česká pošta API Key",
        config_parameter="label_shipping.czech_post_api_key",
    )
    shipping_czech_post_secret_key = fields.Char(
        string="Česká pošta Secret Key",
        config_parameter="label_shipping.czech_post_secret_key",
    )
