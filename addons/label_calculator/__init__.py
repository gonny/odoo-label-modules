from . import models


def _post_init_disable_default_sale_tax(env):
    """Disable default sale tax – the business is a non-VAT-payer (neplátce DPH).

    Runs after module installation to ensure no tax appears on new invoice lines.
    """
    # Remove default sale tax from account settings
    env["ir.config_parameter"].sudo().set_param(
        "account.default_sale_tax_id", False,
    )

    # Deactivate all sale-type taxes so they don't appear in dropdowns
    sale_taxes = env["account.tax"].sudo().search([
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
    ])
    if sale_taxes:
        sale_taxes.write({"active": False})