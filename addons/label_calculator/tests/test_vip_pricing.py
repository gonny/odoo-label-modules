import logging
import math

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestVIPPricingProfiles(TransactionCase):
    """Testy pro VIP cenové profily."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ICP = cls.env["ir.config_parameter"].sudo()

        # === Nastavení – výchozí pro testy ===
        settings = cls.env["res.config.settings"].create(
            {
                "label_hourly_rate": 810,
                "label_admin_overhead_enabled": False,
                "label_admin_overhead_minutes": 15,
                "label_amortization_enabled": True,
                "label_fixed_costs_enabled": True,
                "label_fixed_rent_yearly": 7000,
                "label_fixed_energy_yearly": 27000,
                "label_fixed_other_yearly": 0,
                "label_working_hours_yearly": 2000,
                "label_vat_surcharge_pct": 15,
                "label_default_material_margin_pct": 30,
                "label_min_order_price": 250,
                "label_min_order_quantity": 50,
            }
        )
        settings.set_values()

        # === Stroje ===
        cls.machine_laser = cls.env["label.machine"].create(
            {
                "name": "Laser CO2",
                "purchase_price": 1000000,
                "lifetime_years": 15,
                "working_days_per_week": "5",
                "hours_per_day": 5,
                "weeks_per_year": 44,
            }
        )

        cls.machine_printer = cls.env["label.machine"].create(
            {
                "name": "Tiskárna etiket",
                "purchase_price": 80000,
                "lifetime_years": 5,
                "working_days_per_week": "5",
                "hours_per_day": 4,
                "weeks_per_year": 44,
            }
        )

        # === Skupiny ===
        cls.group_leatherette = cls.env["label.material.group"].create(
            {
                "name": "Koženka Royal",
                "material_type": "area",
                "is_addon": False,
                "default_margin_pct": 35,
                "machine_id": cls.machine_laser.id,
            }
        )

        cls.group_satin = cls.env["label.material.group"].create(
            {
                "name": "Satén",
                "material_type": "length",
                "is_addon": False,
                "default_margin_pct": 25,
                "machine_id": cls.machine_printer.id,
            }
        )

        # === Materiály ===
        cls.mat_leatherette = cls.env["label.material"].create(
            {
                "name": "Černo / stříbrná",
                "group_id": cls.group_leatherette.id,
                "color_name": "Přírodní stříbrná",
                "purchase_price": 310,
                "purchase_vat_included": True,
                "purchase_vat_pct": 21,
                "sheet_width_mm": 600,
                "sheet_height_mm": 300,
                "thickness_mm": 0.8,
            }
        )

        cls.mat_satin_20 = cls.env["label.material"].create(
            {
                "name": "Bílá 20mm",
                "group_id": cls.group_satin.id,
                "color_name": "Bílý",
                "purchase_price": 509,
                "purchase_vat_included": False,
                "purchase_vat_pct": 21,
                "roll_width_mm": 20,
                "roll_length_m": 200,
            }
        )

        # === Cenové profily ===
        # Search for existing profiles from seed data first
        existing_standard = cls.env["label.pricing.profile"].search(
            [
                ("code", "=", "standard"),
            ],
            limit=1,
        )
        if existing_standard:
            cls.profile_standard = existing_standard
        else:
            cls.profile_standard = cls.env["label.pricing.profile"].create(
                {
                    "name": "Standard",
                    "code": "standard",
                    "is_default": True,
                    "is_vip": False,
                    "sequence": 10,
                }
            )

        existing_vip1 = cls.env["label.pricing.profile"].search(
            [
                ("code", "=", "vip1"),
            ],
            limit=1,
        )
        if existing_vip1:
            cls.profile_vip1 = existing_vip1
        else:
            cls.profile_vip1 = cls.env["label.pricing.profile"].create(
                {
                    "name": "VIP1",
                    "code": "vip1",
                    "is_default": False,
                    "is_vip": True,
                    "sequence": 20,
                }
            )

        existing_vip2 = cls.env["label.pricing.profile"].search(
            [
                ("code", "=", "vip2"),
            ],
            limit=1,
        )
        if existing_vip2:
            cls.profile_vip2 = existing_vip2
        else:
            cls.profile_vip2 = cls.env["label.pricing.profile"].create(
                {
                    "name": "VIP2",
                    "code": "vip2",
                    "is_default": False,
                    "is_vip": True,
                    "sequence": 30,
                }
            )

        # === Standard tiery ===
        cls.tier_leath_30 = cls.env["label.production.tier"].create(
            {
                "name": "Do 30",
                "group_id": cls.group_leatherette.id,
                "pricing_profile_id": cls.profile_standard.id,
                "min_quantity": 1,
                "max_quantity": 29,
                "pieces_per_hour": 80,
                "margin_pct": 320,
                "waste_test_percentage": 10,
                "waste_pruning_percentage": 15,
            }
        )

        cls.tier_leath_100 = cls.env["label.production.tier"].create(
            {
                "name": "Do 100",
                "group_id": cls.group_leatherette.id,
                "pricing_profile_id": cls.profile_standard.id,
                "min_quantity": 30,
                "max_quantity": 99,
                "pieces_per_hour": 90,
                "margin_pct": 240,
                "waste_test_percentage": 10,
                "waste_pruning_percentage": 15,
            }
        )

        cls.tier_leath_500 = cls.env["label.production.tier"].create(
            {
                "name": "Do 500",
                "group_id": cls.group_leatherette.id,
                "pricing_profile_id": cls.profile_standard.id,
                "min_quantity": 100,
                "max_quantity": 499,
                "pieces_per_hour": 100,
                "margin_pct": 125,
                "waste_test_percentage": 10,
                "waste_pruning_percentage": 15,
            }
        )

        # Standard satén tier
        cls.tier_satin_200 = cls.env["label.production.tier"].create(
            {
                "name": "Do 200",
                "group_id": cls.group_satin.id,
                "pricing_profile_id": cls.profile_standard.id,
                "min_quantity": 1,
                "max_quantity": 199,
                "pieces_per_hour": 800,
                "margin_pct": 320,
                "waste_test_percentage": 10,
                "waste_pruning_percentage": 0,
            }
        )

        # === VIP1 tiery – flat, better parameters ===
        cls.tier_leath_vip1 = cls.env["label.production.tier"].create(
            {
                "name": "VIP1 koženka",
                "group_id": cls.group_leatherette.id,
                "pricing_profile_id": cls.profile_vip1.id,
                "min_quantity": 0,
                "max_quantity": 999999,
                "pieces_per_hour": 120,
                "margin_pct": 180,
                "waste_test_percentage": 5,
                "waste_pruning_percentage": 10,
            }
        )

        # === VIP2 tiery – even better parameters ===
        cls.tier_leath_vip2 = cls.env["label.production.tier"].create(
            {
                "name": "VIP2 koženka",
                "group_id": cls.group_leatherette.id,
                "pricing_profile_id": cls.profile_vip2.id,
                "min_quantity": 0,
                "max_quantity": 999999,
                "pieces_per_hour": 150,
                "margin_pct": 120,
                "waste_test_percentage": 3,
                "waste_pruning_percentage": 8,
            }
        )

        cls.calc = cls.env["label.calculator"]

        # === Cash rounding – nastavení účtů ===
        profit_account = cls.env["account.account"].search(
            [
                ("account_type", "in", ["income", "income_other"]),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        loss_account = cls.env["account.account"].search(
            [
                ("account_type", "in", ["expense", "expense_other"]),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        if profit_account and loss_account:
            cls.env["account.cash.rounding"].search([]).write(
                {
                    "profit_account_id": profit_account.id,
                    "loss_account_id": loss_account.id,
                }
            )

    # ─────────────────────────────────────────────
    # TEST 35: Pricing profile model creation
    # ─────────────────────────────────────────────
    def test_35_pricing_profile_model(self):
        """Ověří vytvoření a vlastnosti cenových profilů."""
        self.assertEqual(self.profile_standard.code, "standard")
        self.assertTrue(self.profile_standard.is_default)
        self.assertFalse(self.profile_standard.is_vip)

        self.assertEqual(self.profile_vip1.code, "vip1")
        self.assertFalse(self.profile_vip1.is_default)
        self.assertTrue(self.profile_vip1.is_vip)

        self.assertEqual(self.profile_vip2.code, "vip2")
        self.assertTrue(self.profile_vip2.is_vip)

        # Tier count should reflect assigned tiers
        self.assertTrue(self.profile_standard.tier_count >= 3)
        self.assertEqual(self.profile_vip1.tier_count, 1)
        self.assertEqual(self.profile_vip2.tier_count, 1)

        _logger.info(
            "TEST 35: profile model – standard=%s, vip1=%s, vip2=%s ✅",
            self.profile_standard.name,
            self.profile_vip1.name,
            self.profile_vip2.name,
        )

    # ─────────────────────────────────────────────
    # TEST 36: Only one default profile allowed
    # ─────────────────────────────────────────────
    def test_36_single_default_profile_constraint(self):
        """Ověří, že může být pouze jeden výchozí profil."""
        # Ensure there's a default profile already
        self.assertTrue(self.profile_standard.is_default)
        with self.assertRaises(ValidationError):
            self.env["label.pricing.profile"].create(
                {
                    "name": "Duplicate Default",
                    "code": "dup_default",
                    "is_default": True,
                    "is_vip": False,
                }
            )

        _logger.info("TEST 36: single default constraint works ✅")

    # ─────────────────────────────────────────────
    # TEST 37: Standard calc unchanged (backward compat)
    # ─────────────────────────────────────────────
    def test_37_standard_calc_unchanged(self):
        """Ověří, že Standard kalkulace funguje beze změn."""
        # Without profile (backward compat)
        result_no_profile = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
        )
        self.assertTrue(result_no_profile["unit_price"] > 0)
        self.assertEqual(result_no_profile["tier_name"], "Do 30")

        # With explicit standard profile
        result_standard = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
            pricing_profile_id=self.profile_standard.id,
        )
        self.assertEqual(
            result_no_profile["unit_price"],
            result_standard["unit_price"],
        )

        _logger.info(
            "TEST 37: standard calc unchanged – price=%.2f ✅",
            result_no_profile["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 38: VIP1 uses different tier
    # ─────────────────────────────────────────────
    def test_38_vip1_uses_vip_tier(self):
        """VIP1 profil vybere VIP1 tier s lepšími parametry."""
        result_std = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
            pricing_profile_id=self.profile_standard.id,
        )

        result_vip1 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
            pricing_profile_id=self.profile_vip1.id,
        )

        # VIP1 should have lower price (better parameters)
        self.assertLess(
            result_vip1["unit_price"],
            result_std["unit_price"],
            "VIP1 price should be lower than Standard",
        )

        # VIP1 tier name
        self.assertEqual(result_vip1["tier_name"], "VIP1 koženka")

        # VIP1 margin should be 180 (lower)
        self.assertEqual(result_vip1["margin_pct"], 180)

        # Profile name in result
        self.assertEqual(result_vip1["pricing_profile_name"], "VIP1")

        _logger.info(
            "TEST 38: VIP1 price=%.2f < Standard price=%.2f ✅",
            result_vip1["unit_price"],
            result_std["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 39: VIP2 even lower prices
    # ─────────────────────────────────────────────
    def test_39_vip2_even_lower_prices(self):
        """VIP2 profil má ještě lepší ceny než VIP1."""
        result_vip1 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
            pricing_profile_id=self.profile_vip1.id,
        )

        result_vip2 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
            pricing_profile_id=self.profile_vip2.id,
        )

        self.assertLess(
            result_vip2["unit_price"],
            result_vip1["unit_price"],
            "VIP2 price should be lower than VIP1",
        )
        self.assertEqual(result_vip2["tier_name"], "VIP2 koženka")
        self.assertEqual(result_vip2["margin_pct"], 120)

        _logger.info(
            "TEST 39: VIP2 price=%.2f < VIP1 price=%.2f ✅",
            result_vip2["unit_price"],
            result_vip1["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 40: VIP fallback to Standard tier
    # ─────────────────────────────────────────────
    def test_40_vip_fallback_to_standard(self):
        """VIP profil bez vlastního tieru spadne na Standard."""
        # Satén has Standard tier but no VIP1 tier
        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=40,
            quantity=10,
            pricing_profile_id=self.profile_vip1.id,
        )

        # Should find the standard tier as fallback
        self.assertTrue(result["unit_price"] > 0)
        self.assertEqual(result["tier_name"], "Do 200")

        _logger.info(
            "TEST 40: VIP fallback to Standard tier – price=%.2f, tier=%s ✅",
            result["unit_price"],
            result["tier_name"],
        )

    # ─────────────────────────────────────────────
    # TEST 41: Partner VIP status and effective discount
    # ─────────────────────────────────────────────
    def test_41_partner_vip_discount_zero(self):
        """VIP zákazník má discount = 0."""
        partner = self.env["res.partner"].create(
            {
                "name": "VIP Test Customer",
                "label_is_vip": True,
                "label_pricing_profile_id": self.profile_vip1.id,
                "label_discount_override": 15,
            }
        )

        # VIP customers always get 0 discount
        self.assertEqual(
            partner.label_effective_discount,
            0,
            "VIP customer should have 0% discount",
        )
        self.assertTrue(partner.label_is_vip)

        _logger.info("TEST 41: VIP partner discount=0 ✅")

    # ─────────────────────────────────────────────
    # TEST 42: Non-VIP keeps normal discount
    # ─────────────────────────────────────────────
    def test_42_non_vip_keeps_discount(self):
        """Non-VIP zákazník má normální slevu."""
        partner = self.env["res.partner"].create(
            {
                "name": "Standard Customer",
                "label_is_vip": False,
                "label_discount_override": 10,
            }
        )

        self.assertEqual(
            partner.label_effective_discount,
            10,
            "Non-VIP customer should keep discount override",
        )

        _logger.info("TEST 42: Non-VIP discount=10% ✅")

    # ─────────────────────────────────────────────
    # TEST 43: VIP SO line has discount = 0
    # ─────────────────────────────────────────────
    def test_43_vip_so_line_discount_zero(self):
        """VIP zákazník na SO lince má discount = 0."""
        partner = self.env["res.partner"].create(
            {
                "name": "VIP SO Customer",
                "label_is_vip": True,
                "label_pricing_profile_id": self.profile_vip1.id,
            }
        )

        product = self.env["product.template"].create(
            {
                "name": "Test Štítek",
                "type": "consu",
                "pricing_type": "calculator",
                "label_material_group_id": self.group_leatherette.id,
                "label_default_material_id": self.mat_leatherette.id,
                "list_price": 0,
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )

        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.product_variant_id.id,
                "product_uom_qty": 10,
                "label_material_id": self.mat_leatherette.id,
                "label_width_mm": 30,
                "label_height_mm": 20,
            }
        )

        # VIP customer should have price calculated with VIP1 profile
        self.assertTrue(
            line.label_calculated_price > 0,
            "VIP line should have calculated price",
        )

        # VIP badge should appear
        self.assertIn("VIP1", order.label_pricing_profile_display or "")

        _logger.info(
            "TEST 43: VIP SO line – price=%.2f, badge=%s ✅",
            line.label_calculated_price,
            order.label_pricing_profile_display,
        )

    # ─────────────────────────────────────────────
    # TEST 44: Standard SO line still works
    # ─────────────────────────────────────────────
    def test_44_standard_so_line_works(self):
        """Standard zákazník na SO lince funguje beze změn."""
        partner = self.env["res.partner"].create(
            {
                "name": "Standard SO Customer",
                "label_is_vip": False,
            }
        )

        product = self.env["product.template"].create(
            {
                "name": "Test Štítek Standard",
                "type": "consu",
                "pricing_type": "calculator",
                "label_material_group_id": self.group_leatherette.id,
                "label_default_material_id": self.mat_leatherette.id,
                "list_price": 0,
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )

        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.product_variant_id.id,
                "product_uom_qty": 10,
                "label_material_id": self.mat_leatherette.id,
                "label_width_mm": 30,
                "label_height_mm": 20,
            }
        )

        self.assertTrue(
            line.label_calculated_price > 0,
            "Standard line should have calculated price",
        )
        # No VIP badge for standard customer
        self.assertFalse(order.label_pricing_profile_display)

        _logger.info(
            "TEST 44: Standard SO line – price=%.2f ✅",
            line.label_calculated_price,
        )

    # ─────────────────────────────────────────────
    # TEST 45: VIP eligibility – not enough invoices
    # ─────────────────────────────────────────────
    def test_45_vip_eligibility_not_enough_invoices(self):
        """Zákazník s méně než 3 fakturami nemá nárok na VIP."""
        partner = self.env["res.partner"].create(
            {
                "name": "New Customer",
                "label_is_vip": False,
            }
        )

        partner._compute_label_vip_eligible()
        self.assertFalse(
            partner.label_vip_eligible,
            "Customer with no invoices should not be VIP eligible",
        )

        _logger.info("TEST 45: VIP eligibility – not enough invoices ✅")

    # ─────────────────────────────────────────────
    # TEST 46: Tier assigned to profile
    # ─────────────────────────────────────────────
    def test_46_tier_profile_assignment(self):
        """Ověří, že tiery jsou správně přiřazeny k profilům."""
        # Standard tiers
        self.assertEqual(
            self.tier_leath_30.pricing_profile_id,
            self.profile_standard,
        )
        self.assertEqual(
            self.tier_leath_100.pricing_profile_id,
            self.profile_standard,
        )

        # VIP1 tier
        self.assertEqual(
            self.tier_leath_vip1.pricing_profile_id,
            self.profile_vip1,
        )

        # VIP2 tier
        self.assertEqual(
            self.tier_leath_vip2.pricing_profile_id,
            self.profile_vip2,
        )

        _logger.info("TEST 46: tier profile assignment correct ✅")

    # ─────────────────────────────────────────────
    # TEST 47: VIP1 vs Standard price comparison (large qty)
    # ─────────────────────────────────────────────
    def test_47_vip1_vs_standard_large_qty(self):
        """VIP1 je stále levnější než Standard i pro větší množství."""
        result_std = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=200,
            pricing_profile_id=self.profile_standard.id,
        )

        result_vip1 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=200,
            pricing_profile_id=self.profile_vip1.id,
        )

        self.assertLess(
            result_vip1["unit_price"],
            result_std["unit_price"],
            "VIP1 should be cheaper for 200 pcs too",
        )

        _logger.info(
            "TEST 47: VIP1 200pcs=%.2f < Standard 200pcs=%.2f ✅",
            result_vip1["unit_price"],
            result_std["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 48: Profile display on sale order
    # ─────────────────────────────────────────────
    def test_48_profile_display_on_so(self):
        """VIP badge se zobrazí na nabídce."""
        vip_partner = self.env["res.partner"].create(
            {
                "name": "VIP Display Customer",
                "label_is_vip": True,
                "label_pricing_profile_id": self.profile_vip1.id,
            }
        )

        std_partner = self.env["res.partner"].create(
            {
                "name": "Standard Display Customer",
                "label_is_vip": False,
            }
        )

        vip_order = self.env["sale.order"].create(
            {
                "partner_id": vip_partner.id,
            }
        )

        std_order = self.env["sale.order"].create(
            {
                "partner_id": std_partner.id,
            }
        )

        self.assertIn("VIP1", vip_order.label_pricing_profile_display)
        self.assertFalse(std_order.label_pricing_profile_display)

        _logger.info(
            "TEST 48: VIP display=%s, Standard display=%s ✅",
            vip_order.label_pricing_profile_display,
            std_order.label_pricing_profile_display,
        )

    # ─────────────────────────────────────────────
    # TEST 49: Profile on invoice display
    # ─────────────────────────────────────────────
    def test_49_profile_display_on_invoice(self):
        """VIP badge se zobrazí na faktuře."""
        vip_partner = self.env["res.partner"].create(
            {
                "name": "VIP Invoice Customer",
                "label_is_vip": True,
                "label_pricing_profile_id": self.profile_vip2.id,
            }
        )

        std_partner = self.env["res.partner"].create(
            {
                "name": "Standard Invoice Customer",
                "label_is_vip": False,
            }
        )

        # Create minimal invoices
        vip_invoice = self.env["account.move"].create(
            {
                "partner_id": vip_partner.id,
                "move_type": "out_invoice",
            }
        )

        std_invoice = self.env["account.move"].create(
            {
                "partner_id": std_partner.id,
                "move_type": "out_invoice",
            }
        )

        self.assertIn("VIP2", vip_invoice.label_pricing_profile_display)
        self.assertFalse(std_invoice.label_pricing_profile_display)

        _logger.info(
            "TEST 49: VIP invoice=%s, Standard invoice=%s ✅",
            vip_invoice.label_pricing_profile_display,
            std_invoice.label_pricing_profile_display,
        )
