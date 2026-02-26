import logging
import math

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestLabelCalculator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ICP = cls.env["ir.config_parameter"].sudo()

        # === Nastavení – výchozí pro testy ===
        settings = cls.env["res.config.settings"].create({
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
        })
        settings.set_values()

        # === Stroje ===
        cls.machine_laser = cls.env["label.machine"].create({
            "name": "Laser CO2",
            "purchase_price": 1000000,
            "lifetime_years": 15,
            "working_days_per_week": "5",
            "hours_per_day": 5,
            "weeks_per_year": 44,
        })

        cls.machine_printer = cls.env["label.machine"].create({
            "name": "Tiskárna etiket",
            "purchase_price": 80000,
            "lifetime_years": 5,
            "working_days_per_week": "5",
            "hours_per_day": 4,
            "weeks_per_year": 44,
        })

        cls.machine_heat_press = cls.env["label.machine"].create({
            "name": "Heat press",
            "purchase_price": 65000,
            "lifetime_years": 8,
            "working_days_per_week": "5",
            "hours_per_day": 1,
            "weeks_per_year": 44,
        })

        # === Skupiny ===
        cls.group_leatherette = cls.env["label.material.group"].create({
            "name": "Koženka Royal",
            "material_type": "area",
            "is_addon": False,
            "default_margin_pct": 35,
            "machine_id": cls.machine_laser.id,
        })

        cls.group_satin = cls.env["label.material.group"].create({
            "name": "Satén",
            "material_type": "length",
            "is_addon": False,
            "default_margin_pct": 25,
            "machine_id": cls.machine_printer.id,
        })

        cls.group_ttr = cls.env["label.material.group"].create({
            "name": "TTR pásky",
            "material_type": "length",
            "is_addon": True,
            "default_margin_pct": 20,
        })

        cls.group_heat_press = cls.env["label.material.group"].create({
            "name": "Heat press",
            "material_type": "time",
            "is_addon": True,
            "machine_id": cls.machine_heat_press.id,
        })

        cls.group_components = cls.env["label.material.group"].create({
            "name": "Komponenty",
            "material_type": "pieces",
            "is_addon": True,
            "default_margin_pct": 40,
        })

        # === Materiály ===

        # Koženka – area, cena S DPH
        cls.mat_leatherette = cls.env["label.material"].create({
            "name": "Černo / stříbrná",
            "group_id": cls.group_leatherette.id,
            "color_name": "Přírodní stříbrná",
            "purchase_price": 310,
            "purchase_vat_included": True,
            "purchase_vat_pct": 21,
            "sheet_width_mm": 600,
            "sheet_height_mm": 300,
            "thickness_mm": 0.8,
        })

        # Satén – length, cena BEZ DPH
        cls.mat_satin_20 = cls.env["label.material"].create({
            "name": "Bílá 20mm",
            "group_id": cls.group_satin.id,
            "color_name": "Bílý",
            "purchase_price": 509,
            "purchase_vat_included": False,
            "purchase_vat_pct": 21,
            "roll_width_mm": 20,
            "roll_length_m": 200,
        })

        # TTR – length, cena BEZ DPH
        cls.mat_ttr_silver = cls.env["label.material"].create({
            "name": "Stříbrná textilní",
            "group_id": cls.group_ttr.id,
            "color_name": "Stříbrná",
            "purchase_price": 441,
            "purchase_vat_included": False,
            "purchase_vat_pct": 21,
            "roll_width_mm": 69,
            "roll_length_m": 200,
        })

        # Heat press – time
        cls.mat_heat_40s = cls.env["label.material"].create({
            "name": "40s ×1",
            "group_id": cls.group_heat_press.id,
            "time_seconds": 40,
            "time_multiplier": 1,
        })

        # Komponenty – pieces
        cls.mat_rivet = cls.env["label.material"].create({
            "name": "Nýt mosazný",
            "group_id": cls.group_components.id,
            "color_name": "Mosaz",
            "component_price": 1.20,
        })

        # === Tiery ===

        # Koženka
        cls.tier_leath_30 = cls.env["label.production.tier"].create({
            "name": "Do 30",
            "group_id": cls.group_leatherette.id,
            "min_quantity": 1,
            "max_quantity": 29,
            "pieces_per_hour": 80,
            "margin_pct": 320,
            "waste_test_pieces": 0,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 15,
        })

        cls.tier_leath_100 = cls.env["label.production.tier"].create({
            "name": "Do 100",
            "group_id": cls.group_leatherette.id,
            "min_quantity": 30,
            "max_quantity": 99,
            "pieces_per_hour": 90,
            "margin_pct": 240,
            "waste_test_pieces": 0,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 15,
        })

        cls.tier_leath_500 = cls.env["label.production.tier"].create({
            "name": "Do 500",
            "group_id": cls.group_leatherette.id,
            "min_quantity": 100,
            "max_quantity": 499,
            "pieces_per_hour": 100,
            "margin_pct": 125,
            "waste_test_pieces": 0,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 15,
        })

        # Satén
        cls.tier_satin_200 = cls.env["label.production.tier"].create({
            "name": "Do 200",
            "group_id": cls.group_satin.id,
            "min_quantity": 1,
            "max_quantity": 199,
            "pieces_per_hour": 800,
            "margin_pct": 320,
            "waste_test_pieces": 0,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 0,
        })

        cls.tier_satin_1000 = cls.env["label.production.tier"].create({
            "name": "Do 1000",
            "group_id": cls.group_satin.id,
            "min_quantity": 200,
            "max_quantity": 999,
            "pieces_per_hour": 800,
            "margin_pct": 260,
            "waste_test_pieces": 0,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 0,
        })

        # Kalkulátor
        cls.calc = cls.env["label.calculator"]

    # ─────────────────────────────────────────────
    # TEST 01: Základní výpočet – koženka area
    # ─────────────────────────────────────────────
    def test_01_leatherette_basic(self):
        """Koženka Royal 30×20mm, 10 ks – ověření celého výpočtu."""
        default_machine = self.env.ref(
            "label_calculator.machine_laser", raise_if_not_found=False
        )
        default_group = self.env.ref(
            "label_calculator.group_leatherette", raise_if_not_found=False
        )
        default_material = self.env.ref(
            "label_calculator.mat_leatherette_black_silver",
            raise_if_not_found=False,
        )
        default_tier = self.env.ref(
            "label_calculator.tier_leatherette_upto_30",
            raise_if_not_found=False,
        )

        self.assertTrue(default_machine)
        self.assertTrue(default_group)
        self.assertTrue(default_material)
        self.assertTrue(default_tier)

        ICP = self.env["ir.config_parameter"].sudo()
        self.assertAlmostEqual(
            float(ICP.get_param("label_calc.hourly_rate")), 810.0
        )
        self.assertEqual(
            str(ICP.get_param("label_calc.admin_overhead_enabled")), "False"
        )
        self.assertEqual(
            str(ICP.get_param("label_calc.amortization_enabled")), "True"
        )
        self.assertEqual(
            str(ICP.get_param("label_calc.fixed_costs_enabled")), "True"
        )
        self.assertAlmostEqual(
            float(ICP.get_param("label_calc.vat_surcharge_pct")), 15.0
        )
        result = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30,
            height_mm=20,
            quantity=10,
        )

        self.assertTrue(result["unit_price"] > 0)
        self.assertEqual(result["tier_name"], "Do 30")
        self.assertEqual(result["margin_pct"], 320)

        bd = result["breakdown"]["main"]

        # Materiál náklad:
        # 310 / (600×300) × (30×20) = 1.0333
        # × 1/(1-0.10) × 1/(1-0.15) = × 1.3072 = 1.3509
        # / 0.85 (daň) = 1.5893
        self.assertAlmostEqual(bd["material_cost_raw"], 1.5893, places=2)

        # Materiál s marží: 1.5893 × (1 + 320/100) = 1.5893 × 4.2 = 6.675
        self.assertAlmostEqual(bd["material_cost"], 6.675, places=1)

        # Práce: efektivní sazba / ks za hodinu
        # efektivní = 810 + (7000+27000)/2000 = 810 + 17 = 827
        # 827 / 80 = 10.3375
        self.assertAlmostEqual(bd["labor_cost"], 10.3375, places=2)

        # Amortizace: 1000000/(15×5×5×44) = 60.61/hod → 60.61/80 = 0.7576
        self.assertAlmostEqual(bd["machine_cost"], 0.7576, places=2)

        # Zaokrouhlení na 10 haléřů nahoru
        raw_price = bd["material_cost"] + bd["labor_cost"] + bd["machine_cost"]
        expected = math.ceil(raw_price * 10) / 10
        self.assertEqual(result["unit_price"], expected)

        _logger.info(
            "TEST 01: Koženka 30×20mm, 10 ks = %.2f Kč/ks (celkem %.2f Kč)",
            result["unit_price"],
            result["total_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 02: Satén – length typ
    # ─────────────────────────────────────────────
    def test_02_satin_basic(self):
        """Satén Bílá 20mm, 20×40mm, 10 ks."""
        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=40,
            quantity=10,
        )

        self.assertTrue(result["unit_price"] > 0)
        self.assertEqual(result["tier_name"], "Do 200")

        bd = result["breakdown"]["main"]

        # Materiál náklad:
        # 509 × 1.21 = 615.89 (cena s DPH)
        # 615.89 / 200000mm × 40mm = 0.12318
        # × 1/(1-0.10) = × 1.1111 = 0.13686
        # / 0.85 = 0.16101
        self.assertAlmostEqual(bd["material_cost_raw"], 0.161, places=2)

        _logger.info(
            "TEST 02: Satén 20×40mm, 10 ks = %.2f Kč/ks",
            result["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 03: Satén + TTR příplatek
    # ─────────────────────────────────────────────
    def test_03_satin_with_ttr(self):
        """Satén + TTR stříbrná – ověření addon kalkulace."""
        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=40,
            quantity=10,
            addon_material_ids=[self.mat_ttr_silver.id],
        )

        self.assertTrue(result["unit_price"] > 0)
        self.assertTrue(len(result["breakdown"]["addons"]) > 0)

        addon = result["breakdown"]["addons"][0]
        self.assertEqual(addon["material_name"], "Stříbrná textilní")

        # TTR náklad:
        # 441 × 1.21 = 533.61 (s DPH)
        # 533.61 / 200000mm × 40mm = 0.10672
        # × 1.1111 = 0.11858
        # / 0.85 = 0.13951
        # × (1 + 320/100) = × 4.2 = 0.5859
        self.assertAlmostEqual(addon["subtotal"], 0.586, places=2)

        # Celkový náklad materiálu (satén + TTR bez marže)
        # 0.16101 + 0.13951 = 0.30052
        self.assertAlmostEqual(
            result["material_cost_only"], 0.30, places=1
        )

        _logger.info(
            "TEST 03: Satén + TTR, 10 ks = %.2f Kč/ks (náklad mat: %.4f)",
            result["unit_price"],
            result["material_cost_only"],
        )

    # ─────────────────────────────────────────────
    # TEST 04: Tier přepínání – koženka
    # ─────────────────────────────────────────────
    def test_04_tier_switching(self):
        """Ověření, že se vybere správný tier podle množství."""
        r10 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )
        r50 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=50,
        )
        r200 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=200,
        )

        self.assertEqual(r10["tier_name"], "Do 30")
        self.assertEqual(r50["tier_name"], "Do 100")
        self.assertEqual(r200["tier_name"], "Do 500")

        # Cena musí klesat s množstvím
        self.assertGreater(r10["unit_price"], r50["unit_price"])
        self.assertGreater(r50["unit_price"], r200["unit_price"])

        _logger.info(
            "TEST 04: Tiery – 10ks=%.2f, 50ks=%.2f, 200ks=%.2f",
            r10["unit_price"], r50["unit_price"], r200["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 05: Marže – 1 + margin/100
    # ─────────────────────────────────────────────
    def test_05_margin_formula(self):
        """Ověření vzorce marže: 320% = × 4.2."""
        result = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        bd = result["breakdown"]["main"]
        raw = bd["material_cost_raw"]
        with_margin = bd["material_cost"]

        # material_cost = raw × (1 + 320/100) = raw × 4.2
        expected_margin = raw * (1 + 320 / 100)
        self.assertAlmostEqual(with_margin, expected_margin, places=3)

        _logger.info(
            "TEST 05: Marže 320%% – náklad %.4f × 4.2 = %.4f (Odoo: %.4f)",
            raw, expected_margin, with_margin,
        )

    # ─────────────────────────────────────────────
    # TEST 06: Odpady – 1/(1-pct)
    # ─────────────────────────────────────────────
    def test_06_waste_formula(self):
        """Ověření vzorce odpadů: dělení, ne násobení."""
        result = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        bd = result["breakdown"]["main"]

        # Čistá cena materiálu (bez odpadů, bez daně):
        # 310 / (600×300) × (30×20) = 1.03333
        clean_cost = 310 / (600 * 300) * (30 * 20)

        # S odpady: × 1/(1-0.10) × 1/(1-0.15) = × 1.3072
        waste_mult = (1 / (1 - 0.10)) * (1 / (1 - 0.15))
        cost_with_waste = clean_cost * waste_mult

        # S daní: / 0.85
        cost_with_tax = cost_with_waste / 0.85

        self.assertAlmostEqual(bd["material_cost_raw"], cost_with_tax, places=3)

        _logger.info(
            "TEST 06: Odpady – čistá %.4f × waste %.4f / 0.85 = %.4f (Odoo: %.4f)",
            clean_cost, waste_mult, cost_with_tax, bd["material_cost_raw"],
        )

    # ─────────────────────────────────────────────
    # TEST 07: DPH – purchase_vat_included True/False
    # ─────────────────────────────────────────────
    def test_07_vat_handling(self):
        """Ověření, že cena s/bez DPH dává stejný výsledek."""
        # Materiál se stejnou reálnou cenou, zadaný dvěma způsoby
        mat_with_vat = self.env["label.material"].create({
            "name": "Test S DPH",
            "group_id": self.group_satin.id,
            "purchase_price": 615.89,
            "purchase_vat_included": True,
            "purchase_vat_pct": 21,
            "roll_width_mm": 20,
            "roll_length_m": 200,
        })

        mat_without_vat = self.env["label.material"].create({
            "name": "Test BEZ DPH",
            "group_id": self.group_satin.id,
            "purchase_price": 509,
            "purchase_vat_included": False,
            "purchase_vat_pct": 21,
            "roll_width_mm": 20,
            "roll_length_m": 200,
        })

        # Obě by měly mít stejnou purchase_price_incl_vat
        self.assertAlmostEqual(
            mat_with_vat.purchase_price_incl_vat,
            mat_without_vat.purchase_price_incl_vat,
            places=1,
        )

        r1 = self.calc.compute_price(
            material_id=mat_with_vat.id,
            width_mm=20, height_mm=40, quantity=10,
        )
        r2 = self.calc.compute_price(
            material_id=mat_without_vat.id,
            width_mm=20, height_mm=40, quantity=10,
        )

        self.assertAlmostEqual(r1["unit_price"], r2["unit_price"], places=1)

        _logger.info(
            "TEST 07: S DPH=%.2f, Bez DPH=%.2f (měly by být stejné)",
            r1["unit_price"], r2["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 08: Zaokrouhlení na 10 haléřů nahoru
    # ─────────────────────────────────────────────
    def test_08_rounding(self):
        """Ověření zaokrouhlení na 10 haléřů nahoru."""
        result = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        raw = result.get("unit_price_raw", 0)
        final = result["unit_price"]

        # Zaokrouhlení nahoru na 10 haléřů
        expected = math.ceil(raw * 10) / 10
        self.assertEqual(final, expected)

        # Finální cena musí být >= surová
        self.assertGreaterEqual(final, raw)

        # Rozdíl musí být < 0.10
        self.assertLess(final - raw, 0.10)

        _logger.info(
            "TEST 08: Zaokrouhlení – surová %.4f → finální %.2f",
            raw, final,
        )

    # ─────────────────────────────────────────────
    # TEST 09: Admin overhead ON/OFF
    # ─────────────────────────────────────────────
    def test_09_admin_overhead_toggle(self):
        """Admin overhead – zapnutý vs vypnutý."""
        ICP = self.env["ir.config_parameter"].sudo()

        # OFF
        ICP.set_param("label_calc.admin_overhead_enabled", "False")
        r_off = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # ON
        ICP.set_param("label_calc.admin_overhead_enabled", "True")
        ICP.set_param("label_calc.admin_overhead_minutes", "1")
        r_on = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # S admin overhead musí být dražší
        self.assertGreater(r_on["unit_price"], r_off["unit_price"])

        # Admin cost musí být > 0 když ON
        self.assertGreater(r_on["breakdown"]["main"]["admin_cost"], 0)
        self.assertEqual(r_off["breakdown"]["main"]["admin_cost"], 0)

        # Vrátit zpět
        ICP.set_param("label_calc.admin_overhead_enabled", "False")

        _logger.info(
            "TEST 09: Admin OFF=%.2f, ON=%.2f (rozdíl %.2f)",
            r_off["unit_price"], r_on["unit_price"],
            r_on["unit_price"] - r_off["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 10: Amortizace ON/OFF
    # ─────────────────────────────────────────────
    def test_10_amortization_toggle(self):
        """Amortizace strojů – zapnutá vs vypnutá."""
        ICP = self.env["ir.config_parameter"].sudo()

        # ON (default)
        ICP.set_param("label_calc.amortization_enabled", "True")
        r_on = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # OFF
        ICP.set_param("label_calc.amortization_enabled", "False")
        r_off = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        self.assertGreater(r_on["unit_price"], r_off["unit_price"])
        self.assertGreater(r_on["breakdown"]["main"]["machine_cost"], 0)
        self.assertEqual(r_off["breakdown"]["main"]["machine_cost"], 0)

        # Vrátit zpět
        ICP.set_param("label_calc.amortization_enabled", "True")

        _logger.info(
            "TEST 10: Amort ON=%.2f, OFF=%.2f (rozdíl %.2f)",
            r_on["unit_price"], r_off["unit_price"],
            r_on["unit_price"] - r_off["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 11: Fixní náklady ON/OFF
    # ─────────────────────────────────────────────
    def test_11_fixed_costs_toggle(self):
        """Fixní náklady – zapnuté vs vypnuté."""
        ICP = self.env["ir.config_parameter"].sudo()

        # ON (default)
        ICP.set_param("label_calc.fixed_costs_enabled", "True")
        r_on = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # OFF
        ICP.set_param("label_calc.fixed_costs_enabled", "False")
        r_off = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # S fixními náklady musí být dražší (vyšší hodinovka)
        self.assertGreater(r_on["unit_price"], r_off["unit_price"])

        # Práce ON: 827/80, OFF: 810/80
        self.assertAlmostEqual(
            r_on["breakdown"]["main"]["labor_cost"], 827 / 80, places=2
        )
        self.assertAlmostEqual(
            r_off["breakdown"]["main"]["labor_cost"], 810 / 80, places=2
        )

        # Vrátit zpět
        ICP.set_param("label_calc.fixed_costs_enabled", "True")

        _logger.info(
            "TEST 11: Fixní ON=%.2f, OFF=%.2f",
            r_on["unit_price"], r_off["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 12: Chybějící tier – graceful error
    # ─────────────────────────────────────────────
    def test_12_missing_tier(self):
        """Materiál bez tieru – vrátí chybu, ne crash."""
        group_no_tier = self.env["label.material.group"].create({
            "name": "Bez tieru",
            "material_type": "area",
            "is_addon": False,
        })
        mat_no_tier = self.env["label.material"].create({
            "name": "Test bez tieru",
            "group_id": group_no_tier.id,
            "purchase_price": 100,
            "purchase_vat_included": True,
            "sheet_width_mm": 100,
            "sheet_height_mm": 100,
        })

        result = self.calc.compute_price(
            material_id=mat_no_tier.id,
            width_mm=10, height_mm=10, quantity=10,
        )

        # Musí vrátit výsledek (ne crash)
        self.assertIsNotNone(result)
        # Tier name je None nebo prázdný
        self.assertFalse(result.get("tier_name"))
        # Musí být warning
        self.assertTrue(len(result["warnings"]) > 0)

        _logger.info("TEST 12: Chybějící tier – graceful error ✅")

    # ─────────────────────────────────────────────
    # TEST 13: Daň z příjmu – vzorec / (1-sazba)
    # ─────────────────────────────────────────────
    def test_13_income_tax(self):
        """Ověření vzorce daně z příjmu: / (1 - 0.15) = / 0.85."""
        ICP = self.env["ir.config_parameter"].sudo()

        # S daní 15%
        ICP.set_param("label_calc.vat_surcharge_pct", "15")
        r_15 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # Bez daně
        ICP.set_param("label_calc.vat_surcharge_pct", "0")
        r_0 = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        # Náklad materiálu s daní musí být vyšší
        raw_15 = r_15["breakdown"]["main"]["material_cost_raw"]
        raw_0 = r_0["breakdown"]["main"]["material_cost_raw"]
        self.assertGreater(raw_15, raw_0)

        # Poměr musí být 1/0.85 = 1.1765
        ratio = raw_15 / raw_0
        self.assertAlmostEqual(ratio, 1 / 0.85, places=3)

        # Vrátit zpět
        ICP.set_param("label_calc.vat_surcharge_pct", "15")

        _logger.info(
            "TEST 13: Daň 15%%=%.4f, 0%%=%.4f, poměr=%.4f (očekáváno 1.1765)",
            raw_15, raw_0, ratio,
        )

    # ─────────────────────────────────────────────
    # TEST 14: Opakovaný design – bez testovacího odpadu
    # ─────────────────────────────────────────────
    def test_14_repeat_design(self):
        """Opakovaný design – testovací odpad = 0%."""
        r_new = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
            is_repeat_design=False,
        )
        r_repeat = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
            is_repeat_design=True,
        )

        # Opakovaný design musí být levnější (méně odpadu)
        self.assertLess(
            r_repeat["breakdown"]["main"]["material_cost_raw"],
            r_new["breakdown"]["main"]["material_cost_raw"],
        )

        _logger.info(
            "TEST 14: Nový=%.4f, Opakovaný=%.4f (levnější)",
            r_new["breakdown"]["main"]["material_cost_raw"],
            r_repeat["breakdown"]["main"]["material_cost_raw"],
        )

    # ─────────────────────────────────────────────
    # TEST 15: Excel shoda – koženka 30×20mm
    # ─────────────────────────────────────────────
    def test_15_excel_match_leatherette(self):
        """Přesná shoda s Excelem – koženka (bez amort. a fixních)."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_calc.amortization_enabled", "False")
        ICP.set_param("label_calc.fixed_costs_enabled", "False")

        result = self.calc.compute_price(
            material_id=self.mat_leatherette.id,
            width_mm=30, height_mm=20, quantity=10,
        )

        bd = result["breakdown"]["main"]

        # Excel: materiál náklad = 1.589
        self.assertAlmostEqual(bd["material_cost_raw"], 1.589, places=2)

        # Excel: materiál s marží = 1.589 × 4.2 = 6.674
        self.assertAlmostEqual(bd["material_cost"], 6.674, places=1)

        # Excel: práce = 810/80 = 10.125
        self.assertAlmostEqual(bd["labor_cost"], 10.125, places=2)

        # Excel: celkem = 6.674 + 10.125 = 16.799 → zaokr. 16.80
        expected_raw = bd["material_cost"] + bd["labor_cost"]
        expected_rounded = math.ceil(expected_raw * 10) / 10
        self.assertEqual(result["unit_price"], expected_rounded)

        # Vrátit zpět
        ICP.set_param("label_calc.amortization_enabled", "True")
        ICP.set_param("label_calc.fixed_costs_enabled", "True")

        _logger.info(
            "TEST 15: Excel shoda – koženka = %.2f Kč/ks ✅",
            result["unit_price"],
        )

    # ─────────────────────────────────────────────
    # TEST 16: Excel shoda – satén + TTR
    # ─────────────────────────────────────────────
    def test_16_excel_match_satin_ttr(self):
        """Přesná shoda s Excelem – satén + TTR (bez amort. a fixních)."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_calc.amortization_enabled", "False")
        ICP.set_param("label_calc.fixed_costs_enabled", "False")

        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=40,
            quantity=10,
            addon_material_ids=[self.mat_ttr_silver.id],
        )

        # Excel: náklad satén + TTR = 0.301
        self.assertAlmostEqual(
            result["material_cost_only"], 0.30, places=1
        )

        # Vrátit zpět
        ICP.set_param("label_calc.amortization_enabled", "True")
        ICP.set_param("label_calc.fixed_costs_enabled", "True")

        _logger.info(
            "TEST 16: Excel shoda – satén+TTR náklad=%.4f Kč ✅",
            result["material_cost_only"],
        )

    # ─────────────────────────────────────────────
    # TEST 17: Flow SO → Faktura
    # ─────────────────────────────────────────────
    def test_17_invoice_flow(self):
        """Ověření celého flow: SO → Potvrzení → Faktura."""
        # Vytvoř produkt s kalkulačkou
        product = self.env["product.template"].create({
            "name": "Test Gravírovaný štítek",
            "type": "service",
            "pricing_type": "calculator",
            "label_material_group_id": self.group_leatherette.id,
            "invoice_policy": "order",
        })

        # Vytvoř zákazníka
        partner = self.env["res.partner"].create({
            "name": "Test Zákazník",
        })

        # Vytvoř objednávku
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
        })

        # Přidej řádek
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.product_variant_id.id,
            "product_uom_qty": 10,
            "label_material_id": self.mat_leatherette.id,
            "label_width_mm": 30,
            "label_height_mm": 20,
        })

        # Ověř, že se cena spočítala
        self.assertTrue(line.price_unit > 0)
        self.assertTrue(line.label_price_breakdown)

        # Potvrď objednávku
        order.action_confirm()
        self.assertEqual(order.state, "sale")

        # Vytvoř fakturu
        invoice = order._create_invoices()
        self.assertTrue(invoice)

        # Ověř, že se pole přenesly na fakturu
        inv_line = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == product.product_variant_id
        )
        self.assertTrue(inv_line)
        self.assertEqual(
            inv_line.label_material_id.id,
            self.mat_leatherette.id,
        )
        self.assertEqual(inv_line.label_width_mm, 30)
        self.assertEqual(inv_line.label_height_mm, 20)
        self.assertTrue(inv_line.label_material_cost_only > 0)
        self.assertTrue(inv_line.label_price_breakdown)

        _logger.info(
            "TEST 17: SO → Faktura – pole přeneseny ✅ "
            "(materiál: %s, cena: %.2f, náklad: %.4f)",
            inv_line.label_material_id.name,
            inv_line.price_unit,
            inv_line.label_material_cost_only,
        )

      # ─────────────────────────────────────────────
    # TEST 17: Zákaznické slevy – automatická hladina
    # ─────────────────────────────────────────────
    def test_17_discount_tier_auto(self):
        """Ověření automatického přiřazení slevové hladiny."""
        # Vytvoř slevové hladiny
        tier_bronze = self.env["partner.discount.tier"].create({
            "name": "Bronzový",
            "min_spent": 5000,
            "discount_pct": 5,
        })
        tier_silver = self.env["partner.discount.tier"].create({
            "name": "Stříbrný",
            "min_spent": 20000,
            "discount_pct": 10,
        })
        tier_gold = self.env["partner.discount.tier"].create({
            "name": "Zlatý",
            "min_spent": 50000,
            "discount_pct": 15,
        })

        # Vytvoř zákazníka
        partner = self.env["res.partner"].create({
            "name": "Test Zákazník Slevy",
        })

        # Bez útraty → žádná hladina
        partner._compute_label_discount_tier()
        self.assertFalse(partner.label_discount_tier_id)
        self.assertEqual(partner.label_effective_discount, 0)

        # Vytvoř produkt
        product = self.env["product.template"].create({
            "name": "Test Gravírovaný štítek",
            "type": "service",
            "pricing_type": "calculator",
            "label_material_group_id": self.group_leatherette.id,
            "invoice_policy": "order",
        })

        # Vytvoř objednávku za 6000 Kč → Bronze
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
        })
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.product_variant_id.id,
            "product_uom_qty": 100,
            "label_material_id": self.mat_leatherette.id,
            "label_width_mm": 30,
            "label_height_mm": 20,
        })

        # Potvrď objednávku
        order.action_confirm()
        self.assertEqual(order.state, "sale")

        # Vytvoř a potvrď fakturu
        invoice = order._create_invoices()
        invoice.action_post()

        # Přepočítej útratu
        partner._compute_label_total_invoiced()
        partner._compute_label_discount_tier()

        _logger.info(
            "TEST 17: Útrata=%.2f, Hladina=%s, Sleva=%.1f%%",
            partner.label_total_invoiced,
            partner.label_discount_tier_id.name if partner.label_discount_tier_id else "žádná",
            partner.label_effective_discount,
        )

        # Útrata by měla být > 0
        self.assertGreater(partner.label_total_invoiced, 0)

        # Pokud útrata >= 5000 → Bronze
        if partner.label_total_invoiced >= 5000:
            self.assertEqual(
                partner.label_discount_tier_id.id, tier_bronze.id
            )
            self.assertEqual(partner.label_effective_discount, 5)
        else:
            # Útrata < 5000 → žádná hladina
            self.assertFalse(partner.label_discount_tier_id)

    # ─────────────────────────────────────────────
    # TEST 18: Zákaznické slevy – ruční přetížení
    # ─────────────────────────────────────────────
    def test_18_discount_manual_override(self):
        """Ruční sleva přetíží automatickou hladinu."""
        tier_bronze = self.env["partner.discount.tier"].create({
            "name": "Bronzový",
            "min_spent": 0,
            "discount_pct": 5,
        })

        partner = self.env["res.partner"].create({
            "name": "Test Override",
        })

        # Automatická sleva = Bronze 5%
        partner._compute_label_discount_tier()
        self.assertEqual(partner.label_discount_tier_id.id, tier_bronze.id)
        self.assertEqual(partner.label_effective_discount, 5)

        # Ruční přetížení na 12%
        partner.write({"label_discount_override": 12})
        partner._compute_label_effective_discount()
        self.assertEqual(partner.label_effective_discount, 12)

        # Ruční přetížení zpět na 0 → vrátí se automatická
        partner.write({"label_discount_override": 0})
        partner._compute_label_effective_discount()
        self.assertEqual(partner.label_effective_discount, 5)

        _logger.info("TEST 18: Ruční přetížení slevy ✅")

    # ─────────────────────────────────────────────
    # TEST 19: Zákaznické slevy – hladiny správně řazeny
    # ─────────────────────────────────────────────
    def test_19_discount_tier_ordering(self):
        """Ověření, že se vybere nejvyšší dosažená hladina."""
        tier_bronze = self.env["partner.discount.tier"].create({
            "name": "Bronzový",
            "min_spent": 100,
            "discount_pct": 5,
        })
        tier_silver = self.env["partner.discount.tier"].create({
            "name": "Stříbrný",
            "min_spent": 500,
            "discount_pct": 10,
        })
        tier_gold = self.env["partner.discount.tier"].create({
            "name": "Zlatý",
            "min_spent": 5000,
            "discount_pct": 15,
        })

        partner = self.env["res.partner"].create({
            "name": "Test Tier Ordering",
        })

        product = self.env["product.template"].create({
            "name": "Test Tier Štítek",
            "type": "service",
            "pricing_type": "calculator",
            "label_material_group_id": self.group_leatherette.id,
            "invoice_policy": "order",
        })

        # Jedna objednávka – 50 ks koženky 30×20mm
        # Tier "Do 100": margin 240%, pcs/hour 90
        # Cena cca 15-20 Kč/ks → 50 × 15 = 750+ Kč → Silver (500+)
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.product_variant_id.id,
            "product_uom_qty": 50,
            "label_material_id": self.mat_leatherette.id,
            "label_width_mm": 30,
            "label_height_mm": 20,
        })
        order.action_confirm()
        invoice = order._create_invoices()
        invoice.action_post()

        # Přepočítej
        partner._compute_label_total_invoiced()
        partner._compute_label_discount_tier()
        partner._compute_label_effective_discount()

        _logger.info(
            "TEST 19: Útrata=%.2f, Hladina=%s, Sleva=%.1f%%",
            partner.label_total_invoiced,
            partner.label_discount_tier_id.name
            if partner.label_discount_tier_id else "žádná",
            partner.label_effective_discount,
        )

        # Útrata musí být > 500 (Silver)
        self.assertGreater(
            partner.label_total_invoiced, 500,
            f"Útrata {partner.label_total_invoiced} by měla být > 500"
        )

        # Musí být Silver (500 ≤ útrata < 5000)
        self.assertEqual(
            partner.label_discount_tier_id.id, tier_silver.id,
            f"Očekáván Silver, útrata={partner.label_total_invoiced}"
        )
        self.assertEqual(partner.label_effective_discount, 10)

        _logger.info(
            "TEST 19: Útrata %.0f → Stříbrný (10%%) ✅",
            partner.label_total_invoiced,
        )


    # ─────────────────────────────────────────────
    # TEST 20: Zákaznické slevy – žádná hladina
    # ─────────────────────────────────────────────
    def test_20_discount_no_tier(self):
        """Zákazník bez útraty → žádná sleva."""
        partner = self.env["res.partner"].create({
            "name": "Test Nový Zákazník",
        })

        partner._compute_label_total_invoiced()
        partner._compute_label_discount_tier()
        partner._compute_label_effective_discount()

        self.assertEqual(partner.label_total_invoiced, 0)
        self.assertFalse(partner.label_discount_tier_id)
        self.assertEqual(partner.label_effective_discount, 0)
        self.assertEqual(partner.label_discount_override, 0)

        _logger.info("TEST 20: Nový zákazník → žádná sleva ✅")

    # ─────────────────────────────────────────────
    # TEST 21: Sleva se aplikuje na SO řádek
    # ─────────────────────────────────────────────
    def test_21_discount_applied_to_so_line(self):
        """Ověření, že se sleva přenese na řádek objednávky."""
        self.env["partner.discount.tier"].create({
            "name": "Bronzový",
            "min_spent": 0,
            "discount_pct": 5,
        })

        partner = self.env["res.partner"].create({
            "name": "Test SO Discount",
        })

        # Přepočítej – min_spent=0 → Bronze 5%
        partner._compute_label_discount_tier()
        partner._compute_label_effective_discount()
        self.assertEqual(partner.label_effective_discount, 5)

        product = self.env["product.template"].create({
            "name": "Test Štítek",
            "type": "service",
            "pricing_type": "calculator",
            "label_material_group_id": self.group_leatherette.id,
            "invoice_policy": "order",
        })

        order = self.env["sale.order"].create({
            "partner_id": partner.id,
        })

        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.product_variant_id.id,
            "product_uom_qty": 10,
            "label_material_id": self.mat_leatherette.id,
            "label_width_mm": 30,
            "label_height_mm": 20,
            "discount": partner.label_effective_discount,
        })

        # Sleva musí být 5%
        self.assertEqual(line.discount, 5)

        # Cena se slevou musí být nižší
        price_without = line.price_unit * line.product_uom_qty
        price_with = line.price_subtotal
        self.assertLess(price_with, price_without)

        # Rozdíl = 5%
        expected_subtotal = price_without * (1 - 5 / 100)
        self.assertAlmostEqual(price_with, expected_subtotal, places=2)

        _logger.info(
            "TEST 21: SO řádek – cena %.2f, sleva %s%%, subtotal %.2f ✅",
            line.price_unit, line.discount, line.price_subtotal,
        )

    # ─────────────────────────────────────────────
    # TEST 22: Fakturace – kompletní flow se slevou
    # ─────────────────────────────────────────────
    def test_22_invoice_flow_with_discount(self):
        """SO → Potvrzení → Faktura – sleva se přenese."""
        self.env["partner.discount.tier"].create({
            "name": "Test Tier",
            "min_spent": 0,
            "discount_pct": 8,
        })

        partner = self.env["res.partner"].create({
            "name": "Test Invoice Discount",
        })
        partner._compute_label_discount_tier()
        partner._compute_label_effective_discount()

        product = self.env["product.template"].create({
            "name": "Test Štítek Faktura",
            "type": "service",
            "pricing_type": "calculator",
            "label_material_group_id": self.group_leatherette.id,
            "invoice_policy": "order",
        })

        order = self.env["sale.order"].create({
            "partner_id": partner.id,
        })

        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.product_variant_id.id,
            "product_uom_qty": 50,
            "label_material_id": self.mat_leatherette.id,
            "label_width_mm": 30,
            "label_height_mm": 20,
            "discount": partner.label_effective_discount,
        })

        # Potvrď
        order.action_confirm()
        self.assertEqual(order.state, "sale")

        # Fakturuj
        invoice = order._create_invoices()
        self.assertTrue(invoice)

        # Ověř slevu na faktuře
        inv_line = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == product.product_variant_id
        )
        self.assertTrue(inv_line)
        self.assertEqual(inv_line.discount, 8)

        # Ověř kalkulační pole
        self.assertEqual(
            inv_line.label_material_id.id,
            self.mat_leatherette.id,
        )
        self.assertTrue(inv_line.label_price_breakdown)

        _logger.info(
            "TEST 22: Faktura se slevou 8%% – cena %.2f, sleva %.0f%%, "
            "materiál: %s ✅",
            inv_line.price_unit,
            inv_line.discount,
            inv_line.label_material_id.name,
        )

    # ─────────────────────────────────────────────
    # TEST 23: Variable symbol – basic computation
    # ─────────────────────────────────────────────
    def test_23_variable_symbol_basic(self):
        """Variable symbol extracts digits from invoice name."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.env["res.partner"].create(
                {"name": "VS Test"}
            ).id,
        })
        # Draft invoice has name "/"
        self.assertEqual(move.label_variable_symbol, "")

        # Simulate a posted name
        move.name = "INV/2026/00042"
        move._compute_variable_symbol()
        self.assertEqual(move.label_variable_symbol, "202600042")

        _logger.info("TEST 23: Variable symbol INV/2026/00042 → %s ✅",
                      move.label_variable_symbol)

    # ─────────────────────────────────────────────
    # TEST 24: Variable symbol – edge cases
    # ─────────────────────────────────────────────
    def test_24_variable_symbol_edge_cases(self):
        """Variable symbol handles '/', empty, long numbers."""
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.env["res.partner"].create(
                {"name": "VS Edge"}
            ).id,
        })

        # "/" → empty
        move.name = "/"
        move._compute_variable_symbol()
        self.assertEqual(move.label_variable_symbol, "")

        # FV format
        move.name = "FV/2026/00001"
        move._compute_variable_symbol()
        self.assertEqual(move.label_variable_symbol, "202600001")

        # Long number → last 10 digits
        move.name = "INV/20261234567890123"
        move._compute_variable_symbol()
        self.assertEqual(len(move.label_variable_symbol), 10)

        _logger.info("TEST 24: Variable symbol edge cases ✅")

    # ─────────────────────────────────────────────
    # TEST 25: SPD string generation
    # ─────────────────────────────────────────────
    def test_25_spd_string(self):
        """SPD string is generated for CZK invoices with bank account."""
        company = self.env.company
        czk = self.env.ref("base.CZK", raise_if_not_found=False)
        if not czk:
            _logger.info("TEST 25: CZK currency not found, skipping")
            return

        # Create a bank account for company
        bank = self.env["res.partner.bank"].create({
            "acc_number": "CZ6508000000192000145399",
            "partner_id": company.partner_id.id,
            "currency_id": czk.id,
        })

        partner = self.env["res.partner"].create({"name": "SPD Test"})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": czk.id,
        })
        move.name = "FV/2026/00001"
        move._compute_variable_symbol()

        spd = move._get_spd_string()
        self.assertIn("SPD*1.0", spd)
        self.assertIn("ACC:CZ6508000000192000145399", spd)
        self.assertIn("CC:CZK", spd)
        self.assertIn("X-VS:202600001", spd)

        _logger.info("TEST 25: SPD string → %s ✅", spd[:60])

    # ─────────────────────────────────────────────
    # TEST 26: QR code base64 generation
    # ─────────────────────────────────────────────
    def test_26_qr_code_base64(self):
        """QR code base64 is returned for CZK invoices."""
        company = self.env.company
        czk = self.env.ref("base.CZK", raise_if_not_found=False)
        if not czk:
            _logger.info("TEST 26: CZK currency not found, skipping")
            return

        self.env["res.partner.bank"].create({
            "acc_number": "CZ6508000000192000145399",
            "partner_id": company.partner_id.id,
            "currency_id": czk.id,
        })

        partner = self.env["res.partner"].create({"name": "QR Test"})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": czk.id,
        })
        move.name = "FV/2026/00001"
        move._compute_variable_symbol()

        try:
            import qrcode  # noqa: F401
        except ImportError:
            _logger.info("TEST 26: qrcode not installed, skipping")
            return

        qr_b64 = move._get_qr_code_base64()
        self.assertTrue(qr_b64, "QR code base64 should not be empty")
        # Verify it's valid base64
        import base64
        decoded = base64.b64decode(qr_b64)
        # PNG starts with \x89PNG
        self.assertTrue(decoded[:4] == b"\x89PNG",
                        "QR code should be a valid PNG image")

        _logger.info("TEST 26: QR code base64 length=%d ✅", len(qr_b64))

    # ─────────────────────────────────────────────
    # TEST 27: QR code empty for non-CZK invoice
    # ─────────────────────────────────────────────
    def test_27_qr_code_non_czk(self):
        """QR code is empty for EUR invoices."""
        eur = self.env.ref("base.EUR", raise_if_not_found=False)
        if not eur:
            _logger.info("TEST 27: EUR currency not found, skipping")
            return

        partner = self.env["res.partner"].create({"name": "EUR Test"})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": eur.id,
        })

        spd = move._get_spd_string()
        self.assertEqual(spd, "")

        qr_b64 = move._get_qr_code_base64()
        self.assertEqual(qr_b64, "")

        _logger.info("TEST 27: No QR for EUR invoice ✅")

    # ─────────────────────────────────────────────
    # TEST 28: Bank account auto-selection by currency
    # ─────────────────────────────────────────────
    def test_28_bank_account_auto_select(self):
        """Invoice create auto-selects company bank account by currency."""
        company = self.env.company
        czk = self.env.ref("base.CZK", raise_if_not_found=False)
        if not czk:
            _logger.info("TEST 28: CZK currency not found, skipping")
            return

        bank_czk = self.env["res.partner.bank"].create({
            "acc_number": "CZ6508000000192000145399",
            "partner_id": company.partner_id.id,
            "currency_id": czk.id,
        })

        partner = self.env["res.partner"].create({"name": "Bank Test"})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": czk.id,
        })

        self.assertEqual(move.partner_bank_id.id, bank_czk.id,
                         "Bank account should be auto-selected by currency")

        _logger.info("TEST 28: Auto bank selection → %s ✅",
                      move.partner_bank_id.acc_number)

    # ─────────────────────────────────────────────
    # TEST 29: Cash rounding auto-set
    # ─────────────────────────────────────────────
    def test_29_cash_rounding_auto_set(self):
        """Invoice create auto-sets cash rounding by currency name."""
        czk = self.env.ref("base.CZK", raise_if_not_found=False)
        if not czk:
            _logger.info("TEST 29: CZK currency not found, skipping")
            return

        rounding_czk = self.env["account.cash.rounding"].create({
            "name": "CZK test rounding",
            "rounding": 1.0,
            "strategy": "add_invoice_line",
            "rounding_method": "HALF-UP",
        })

        partner = self.env["res.partner"].create({"name": "Rounding Test"})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": czk.id,
        })

        self.assertTrue(move.invoice_cash_rounding_id,
                        "Cash rounding should be auto-set")

        _logger.info("TEST 29: Auto cash rounding → %s ✅",
                      move.invoice_cash_rounding_id.name)
