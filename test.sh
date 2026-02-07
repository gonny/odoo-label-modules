docker compose run --rm odoo \
  odoo     \
  -d odoo_label \
  -u label_calculator \
  --test-tags /label_calculator \
  --stop-after-init \
  --log-level=info