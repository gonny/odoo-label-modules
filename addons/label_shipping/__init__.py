import os

from . import models
from . import services


def _post_init_shipping(env):
    """Populate ir.config_parameter from environment variables.

    Reads carrier API keys from environment and stores them
    in Odoo system parameters if not already set.
    """
    ICP = env["ir.config_parameter"].sudo()
    mapping = {
        "label_shipping.packeta_api_key": "PACKETA_API_KEY",
        "label_shipping.packeta_api_password": "PACKETA_API_PASSWORD",
        "label_shipping.dpd_api_key": "DPD_API_KEY",
        "label_shipping.dpd_api_dsw": "DPD_API_DSW",
        "label_shipping.czech_post_api_key": "CZECH_POST_API_KEY",
        "label_shipping.czech_post_secret_key": "CZECH_POST_SECRET_KEY",
    }
    for param_key, env_var in mapping.items():
        current = ICP.get_param(param_key, "")
        env_value = os.environ.get(env_var, "")
        if env_value and not current:
            ICP.set_param(param_key, env_value)
