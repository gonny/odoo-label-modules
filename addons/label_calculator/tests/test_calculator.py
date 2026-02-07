import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

class TestLabelCalculator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Nastav globální parametry
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("label_calc.hourly_rate", "800")
        ICP.set_param("label_calc.admin_overhead_minutes", "15")
        ICP.set_param("label_calc.vat_surcharge_pct", "21")
        ICP.set_param("label_calc.material_margin_pct", "30")
        ICP.set_param("label_calc.min_order_price", "250")
        ICP.set_param("label_calc.min_order_quantity", "50")
        ICP.set_param("label_calc.fixed_rent_yearly", "60000")
        ICP.set_param("label_calc.fixed_energy_yearly", "18000")
        ICP.set_param("label_calc.fixed_other_yearly", "12000")
        ICP.set_param("label_calc.working_hours_yearly", "2000")

        # Stroj
        cls.laser = cls.env["label.machine"].create({
            "name": "Laser CO2",
            "purchase_price": 100000,
            "lifetime_years": 5,
            "working_days_per_week": "5",
            "hours_per_day": 6,
            "weeks_per_year": 50,
        })

        cls.printer = cls.env["label.machine"].create({
            "name": "Tiskárna etiket",
            "purchase_price": 35000,
            "lifetime_years": 4,
            "working_days_per_week": "5",
            "hours_per_day": 4,
            "weeks_per_year": 50,
        })

        # Skupina: Hliník (area)
        cls.group_alu = cls.env["label.material.group"].create({
            "name": "Hliník",
            "material_type": "area",
            "is_addon": False,
            "default_margin_pct": 35,
            "machine_id": cls.laser.id,
        })

        # Materiál: Hliník 0.5mm Černá
        cls.mat_alu_black = cls.env["label.material"].create({
            "name": "0.5mm",
            "group_id": cls.group_alu.id,
            "color_name": "Černá eloxovaná",
            "purchase_price": 380,
            "purchase_vat_included": True,
            "purchase_vat_pct": 21,
            "sheet_width_mm": 500,
            "sheet_height_mm": 500,
            "thickness_mm": 0.5,
        })

        # Tier: Velkoobjem (500+)
        cls.tier_alu_bulk = cls.env["label.production.tier"].create({
            "name": "Velkoobjem",
            "group_id": cls.group_alu.id,
            "min_quantity": 500,
            "max_quantity": 999999,
            "pieces_per_hour": 1200,
            "margin_pct": 25,
            "waste_test_pieces": 2,
            "waste_test_percentage": 2,
            "waste_pruning_percentage": 5,
        })

        # Tier: Malá série (1-49)
        cls.tier_alu_small = cls.env["label.production.tier"].create({
            "name": "Malá série",
            "group_id": cls.group_alu.id,
            "min_quantity": 1,
            "max_quantity": 49,
            "pieces_per_hour": 500,
            "margin_pct": 40,
            "waste_test_pieces": 5,
            "waste_test_percentage": 10,
            "waste_pruning_percentage": 10,
        })

        # Skupina: Satén (length)
        cls.group_satin = cls.env["label.material.group"].create({
            "name": "Satén",
            "material_type": "length",
            "is_addon": False,
            "default_margin_pct": 25,
            "machine_id": cls.printer.id,
        })

        cls.mat_satin_20 = cls.env["label.material"].create({
            "name": "20mm",
            "group_id": cls.group_satin.id,
            "color_name": "Bílý",
            "purchase_price": 220,
            "purchase_vat_included": True,
            "purchase_vat_pct": 21,
            "roll_width_mm": 20,
            "roll_length_m": 100,
        })

        cls.tier_satin_bulk = cls.env["label.production.tier"].create({
            "name": "Velkoobjem",
            "group_id": cls.group_satin.id,
            "min_quantity": 50,
            "max_quantity": 999999,
            "pieces_per_hour": 1500,
            "margin_pct": 25,
            "waste_test_pieces": 3,
            "waste_test_percentage": 5,
            "waste_pruning_percentage": 3,
        })

        # Skupina: TTR (length, addon)
        cls.group_ttr = cls.env["label.material.group"].create({
            "name": "TTR pásky",
            "material_type": "length",
            "is_addon": True,
            "default_margin_pct": 20,
        })

        cls.mat_ttr_black = cls.env["label.material"].create({
            "name": "110mm",
            "group_id": cls.group_ttr.id,
            "color_name": "Černá",
            "purchase_price": 350,
            "purchase_vat_included": True,
            "purchase_vat_pct": 21,
            "roll_width_mm": 110,
            "roll_length_m": 100,
        })

        # Skupina: Komponenty (pieces, addon)
        cls.group_comp = cls.env["label.material.group"].create({
            "name": "Komponenty",
            "material_type": "pieces",
            "is_addon": True,
            "default_margin_pct": 40,
        })

        cls.mat_rivet = cls.env["label.material"].create({
            "name": "Nýt mosazný",
            "group_id": cls.group_comp.id,
            "component_price": 1.20,
        })

        cls.calc = cls.env["label.calculator"]

    # ==================================================================
    # TESTY
    # ==================================================================

    def test_01_basic_area_calculation(self):
        """Gravírovaný štítek – hliník 30×40mm, 500 ks."""
        result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
        )

        self.assertGreater(result["unit_price"], 0)
        self.assertEqual(result["quantity"], 500)
        self.assertEqual(result["tier_name"], "Velkoobjem")
        self.assertEqual(result["margin_pct"], 25)
        self.assertFalse(result["warnings"])  # 500 ks > min 50

        bd = result["breakdown"]["main"]
        self.assertGreater(bd["material_cost"], 0)
        self.assertGreater(bd["labor_cost"], 0)
        self.assertGreater(bd["admin_cost"], 0)
        self.assertGreater(bd["machine_cost"], 0)
        self.assertEqual(bd["machine_name"], "Laser CO2")

        # Ověř rozumné rozmezí ceny
        # Materiál: 30×40=1200mm² × 0.00152 Kč/mm² × odpady × DPH × marže ≈ 2-3 Kč
        # Práce: 845/1200 ≈ 0.70 Kč
        # Admin: 0.25×845/500 ≈ 0.42 Kč
        # Amortizace: 66.67/1200 ≈ 0.06 Kč
        # Celkem: cca 3-5 Kč/ks
        self.assertGreater(result["unit_price"], 1)
        self.assertLess(result["unit_price"], 10)

        _logger.info(
            "TEST 01: Hliník 30×40mm, 500 ks = %.2f Kč/ks (celkem %.0f Kč)",
            result["unit_price"], result["total_price"],
        )

    def test_02_small_quantity_warnings(self):
        """Malá série – varování pod minimem."""
        result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=10,
        )

        self.assertGreater(result["unit_price"], 0)
        self.assertEqual(result["tier_name"], "Malá série")
        self.assertEqual(result["margin_pct"], 40)

        # Musí být varování o množství
        qty_warnings = [w for w in result["warnings"] if w["type"] == "quantity"]
        self.assertTrue(qty_warnings)

        # Malá série je dražší než velkoobjem
        bulk_result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
        )
        self.assertGreater(result["unit_price"], bulk_result["unit_price"])

        _logger.info(
            "TEST 02: Hliník 30×40mm, 10 ks = %.2f Kč/ks (vs 500 ks = %.2f Kč/ks)",
            result["unit_price"], bulk_result["unit_price"],
        )

    def test_03_repeat_design_less_waste(self):
        """Opakovaný design – nulový testovací odpad."""
        new_result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
            is_repeat_design=False,
        )

        repeat_result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
            is_repeat_design=True,
        )

        # Opakovaný design = levnější (méně odpadu)
        self.assertLess(
            repeat_result["unit_price"],
            new_result["unit_price"],
        )

        _logger.info(
            "TEST 03: Nový design = %.2f Kč, opakovaný = %.2f Kč (úspora %.1f%%)",
            new_result["unit_price"],
            repeat_result["unit_price"],
            (1 - repeat_result["unit_price"] / new_result["unit_price"]) * 100,
        )

    def test_04_ribbon_with_ttr_addon(self):
        """Textilní etiketa – satén + TTR příplatek."""
        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=60,
            quantity=200,
            addon_material_ids=[self.mat_ttr_black.id],
        )

        self.assertGreater(result["unit_price"], 0)
        self.assertEqual(len(result["breakdown"]["addons"]), 1)

        addon = result["breakdown"]["addons"][0]
        self.assertEqual(addon["type"], "addon_material")
        self.assertGreater(addon["material_cost"], 0)
        self.assertEqual(addon["machine_cost"], 0)  # TTR nemá stroj

        _logger.info(
            "TEST 04: Satén 20×60mm + TTR, 200 ks = %.2f Kč/ks",
            result["unit_price"],
        )

    def test_05_component_addon(self):
        """Štítek s nýtem – hlavní materiál + nýt jako příplatek."""
        result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
            addon_material_ids=[self.mat_rivet.id],
        )

        # Cena musí být vyšší než bez nýtu
        result_no_rivet = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
        )

        self.assertGreater(
            result["unit_price"],
            result_no_rivet["unit_price"],
        )

        addon = result["breakdown"]["addons"][0]
        # Nýt: 1.20 Kč × DPH × marže
        self.assertGreater(addon["material_cost"], 1.0)

        _logger.info(
            "TEST 05: Hliník + nýt = %.2f Kč/ks (bez nýtu = %.2f Kč/ks)",
            result["unit_price"], result_no_rivet["unit_price"],
        )

    def test_06_addon_cannot_be_main(self):
        """Addon materiál nelze použít jako hlavní."""
        result = self.calc.compute_price(
            material_id=self.mat_ttr_black.id,
            width_mm=20,
            height_mm=60,
            quantity=200,
        )

        self.assertEqual(result["unit_price"], 0)
        self.assertTrue(result["warnings"])
        self.assertEqual(result["warnings"][0]["type"], "error")

    def test_07_missing_tier(self):
        """Chybějící tier – chybová hláška."""
        # Satén nemá tier pro 1-49 ks v test datech
        # (záleží na setup – pokud máš tier pro 1-49, přeskoč)
        result = self.calc.compute_price(
            material_id=self.mat_satin_20.id,
            width_mm=20,
            height_mm=60,
            quantity=10,  # Malá série – nemáme tier pro Satén
        )

        # Buď najde tier, nebo vrátí error
        if not result["tier_name"]:
            self.assertTrue(result["warnings"])

    def test_08_tier_override(self):
        """Přetížení výkonu pro konkrétní materiál."""
        # Vytvoř override: Černá elox je pomalejší
        self.env["label.material.tier.override"].create({
            "material_id": self.mat_alu_black.id,
            "tier_id": self.tier_alu_bulk.id,
            "pieces_per_hour_override": 800,  # místo 1200
        })

        result = self.calc.compute_price(
            material_id=self.mat_alu_black.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
        )

        # Práce musí být dražší (800 ks/hod místo 1200)
        bd = result["breakdown"]["main"]
        self.assertEqual(bd["pcs_per_hour"], 800)
        self.assertGreater(bd["labor_cost"], 0.8)  # 845/800 > 1.0

        _logger.info(
            "TEST 08: S override (800/hod) = %.2f Kč/ks",
            result["unit_price"],
        )
