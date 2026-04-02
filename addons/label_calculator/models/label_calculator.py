from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class LabelCalculator(models.AbstractModel):
    """Kalkulační engine pro výpočet cen štítků.

    Použití:
        result = self.env['label.calculator'].compute_price(
            material_id=material.id,
            width_mm=30,
            height_mm=40,
            quantity=500,
        )
        # result = {
        #     'unit_price': 4.28,
        #     'total_price': 2140.0,
        #     'breakdown': {...},
        #     'warnings': [...],
        # }
    """

    _name = "label.calculator"
    _description = "Kalkulační engine"

    # ------------------------------------------------------------------
    # Hlavní veřejná metoda
    # ------------------------------------------------------------------
    @api.model
    def compute_price(
        self,
        material_id,
        width_mm=0,
        height_mm=0,
        quantity=1,
        is_repeat_design=False,
        addon_material_ids=None,
        pricing_profile_id=None,
    ):
        """Vypočítá kompletní cenu za 1 ks a celkem.

        Args:
            material_id: int – ID hlavního label.material
            width_mm: float – šířka štítku v mm
            height_mm: float – výška/délka štítku v mm
            quantity: int – počet kusů
            is_repeat_design: bool – opakovaný design (test odpad = 0)
            addon_material_ids: list[int] – ID příplatkových materiálů
            pricing_profile_id: int – ID cenového profilu zákazníka (None = výchozí)

        Returns:
            dict s klíči: unit_price, total_price, breakdown, warnings
        """
        material = self.env["label.material"].browse(material_id)
        if not material.exists():
            return self._error_result("Materiál nenalezen")

        try:
            quantity_value = float(quantity)
            width_value = float(width_mm or 0)
            height_value = float(height_mm or 0)
        except (TypeError, ValueError):
            return self._error_result("Neplatné číselné hodnoty")

        if quantity_value <= 0:
            return self._error_result("Množství musí být větší než 0")

        if material.material_type == "area" and (
            width_value <= 0 or height_value <= 0
        ):
            return self._error_result("Rozměry štítku musí být větší než 0")

        if material.material_type == "length" and height_value <= 0:
            return self._error_result("Výška/délka etikety musí být větší než 0")

        group = material.group_id
        if not group:
            return self._error_result("Materiál nemá přiřazenou skupinu")

        if group.is_addon:
            return self._error_result(
                f"Materiál '{material.display_name}' je příplatkový – "
                f"nelze použít jako hlavní materiál"
            )

        # Načti globální nastavení
        config = self._get_config()

        # Najdi tier
        tier = self._find_tier(group, quantity, pricing_profile_id=pricing_profile_id)
        if not tier:
            return self._error_result(
                f"Nenalezena množstevní hladina pro {quantity} ks "
                f"ve skupině '{group.name}'"
            )

        # Zjisti efektivní pieces_per_hour (s override)
        pcs_per_hour = self._get_effective_pcs_per_hour(material, tier)

        # Efektivní hodinová sazba (práce + fixní náklady)
        effective_hourly = self._get_effective_hourly_rate(config)

        # Efektivní marže
        margin_pct = group.get_effective_margin(tier=tier)

        # === KALKULACE HLAVNÍHO MATERIÁLU ===
        main_result = self._calc_main_material(
            material=material,
            group=group,
            tier=tier,
            config=config,
            width_mm=width_mm,
            height_mm=height_mm,
            quantity=quantity,
            is_repeat_design=is_repeat_design,
            pcs_per_hour=pcs_per_hour,
            effective_hourly=effective_hourly,
            margin_pct=margin_pct,
        )

        # === KALKULACE PŘÍPLATKŮ (addons) ===
        addon_results = []
        if addon_material_ids:
            for addon_id in addon_material_ids:
                addon_mat = self.env["label.material"].browse(addon_id)
                if addon_mat.exists() and addon_mat.group_id.is_addon:
                    addon_result = self._calc_addon_material(
                        material=addon_mat,
                        group=addon_mat.group_id,
                        tier=tier,
                        config=config,
                        width_mm=width_mm,
                        height_mm=height_mm,
                        quantity=quantity,
                        is_repeat_design=is_repeat_design,
                        pcs_per_hour=pcs_per_hour,
                        margin_pct=margin_pct,
                    )
                    addon_results.append(addon_result)

        # === SOUČET ===
        unit_price = main_result["subtotal"]
        for addon in addon_results:
            unit_price += addon["subtotal"]

        total_price = unit_price * quantity

        # === VAROVÁNÍ ===
        warnings = self._check_warnings(config, quantity, total_price)

        # Materiálový náklad (bez marže, bez práce)
        material_cost_only = main_result.get("material_cost_raw", 0)
        for addon in addon_results:
            material_cost_only += addon.get("material_cost_raw", 0)

        # Před zaokrouhlením
        unit_price_raw = unit_price

        # Zaokrouhlení na 10 haléřů nahoru
        unit_price = self._round_price(unit_price)
        total_price = round(unit_price * quantity, 2)

        return {
            "unit_price": round(unit_price, 2),
            "unit_price_raw": round(unit_price_raw, 4),
            "total_price": round(total_price, 2),
            "material_cost_only": round(material_cost_only, 4),
            "quantity": quantity,
            "tier_name": tier.name,
            "profile_name": tier.pricing_profile_id.name if tier.pricing_profile_id else None,
            "margin_pct": margin_pct,
            "breakdown": {
                "main": main_result,
                "addons": addon_results,
            },
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Kalkulace hlavního materiálu (is_addon=False)
    # ------------------------------------------------------------------
    def _calc_main_material(
        self, material, group, tier, config,
        width_mm, height_mm, quantity,
        is_repeat_design, pcs_per_hour,
        effective_hourly, margin_pct,
    ):
        # 1. Materiálové náklady
        mat_cost = self._calc_material_cost(
            material=material,
            tier=tier,
            config=config,
            width_mm=width_mm,
            height_mm=height_mm,
            is_repeat_design=is_repeat_design,
            margin_pct=margin_pct,
        )

        # 1b. Materiálové náklady BEZ marže (pro "náklad na materiál")
        mat_cost_raw = self._calc_material_cost_raw(
            material=material,
            tier=tier,
            config=config,
            width_mm=width_mm,
            height_mm=height_mm,
            is_repeat_design=is_repeat_design,
        )

        # 2. Práce
        labor_cost = effective_hourly / pcs_per_hour if pcs_per_hour else 0

        # 3. Admin overhead (jen pokud je zapnutý)
        admin_enabled = config.get("admin_overhead_enabled", "False")
        admin_cost = 0
        if admin_enabled == "True" and quantity:
            admin_minutes = float(config.get("admin_overhead_minutes", 15))
            admin_cost = (admin_minutes / 60) * effective_hourly / quantity

        # 4. Amortizace stroje (jen pokud je zapnutá)
        amortization_enabled = config.get("amortization_enabled", "True")
        machine_cost = 0
        if (
            amortization_enabled == "True"
            and group.machine_id
            and group.machine_id.hourly_amortization
        ):
            machine_cost = group.machine_id.hourly_amortization / pcs_per_hour

        subtotal = mat_cost + labor_cost + admin_cost + machine_cost

        return {
            "material_name": material.display_name,
            "type": "main",
            "material_cost": round(mat_cost, 6),
            "material_cost_raw": round(mat_cost_raw, 6),
            "labor_cost": round(labor_cost, 4),
            "admin_cost": round(admin_cost, 4),
            "machine_cost": round(machine_cost, 4),
            "machine_name": group.machine_id.name if group.machine_id else None,
            "pcs_per_hour": pcs_per_hour,
            "subtotal": round(subtotal, 4),
        }

    def _calc_material_cost_raw(
        self, material, tier, config,
        width_mm, height_mm, is_repeat_design,
    ):
        """Materiálové náklady BEZ marže.

        1. Cena materiálu (vždy S DPH – get_unit_cost to zajistí)
        2. Odpady (zmenšují využitelnou plochu)
        3. Daň z příjmu (/ (1 - sazba))
        """
        unit_cost = material.get_unit_cost(
            width_mm=width_mm,
            height_mm=height_mm,
        )
        if not unit_cost:
            return 0

        # Odpady
        waste_multiplier = self._get_waste_multiplier(
            tier=tier,
            is_repeat_design=is_repeat_design,
        )
        cost_with_waste = unit_cost * waste_multiplier

        # Daň z příjmu
        income_tax_pct = float(config.get("vat_surcharge_pct", 0))
        if income_tax_pct > 0:
            cost_with_waste = cost_with_waste / (1 - income_tax_pct / 100)

        return cost_with_waste


    # ------------------------------------------------------------------
    # Kalkulace příplatkového materiálu (is_addon=True)
    # ------------------------------------------------------------------
    def _calc_addon_material(
        self, material, group, tier, config,
        width_mm, height_mm, quantity,
        is_repeat_design, pcs_per_hour, margin_pct,
    ):
        """Addon kalkulace dle typu:
        - area/length/pieces bez stroje → jen materiál
        - area/length/pieces se strojem → materiál + amortizace
        - time → čas × amortizace stroje
        """
        mat_type = group.material_type

        if mat_type == "time":
            # TIME: cena = čas × amortizace stroje
            seconds = material.time_seconds * (material.time_multiplier or 1)
            machine = group.machine_id
            amortization_enabled = config.get("amortization_enabled", "True")
            if (
                amortization_enabled == "True"
                and machine
                and machine.hourly_amortization
            ):
                time_cost = seconds * (machine.hourly_amortization / 3600)
            else:
                time_cost = 0

            return {
                "material_name": material.display_name,
                "type": "addon_time",
                "time_seconds": seconds,
                "machine_name": machine.name if machine else None,
                "material_cost_raw": 0,
                "material_cost": 0,
                "machine_cost": round(time_cost, 6),
                "subtotal": round(time_cost, 4),
            }

        else:
            # AREA / LENGTH / PIECES: materiálové náklady
            raw_cost = self._calc_material_cost_raw(
                material=material,
                tier=tier,
                config=config,
                width_mm=width_mm,
                height_mm=height_mm,
                is_repeat_design=is_repeat_design,
            )

            mat_cost = self._calc_material_cost(
                material=material,
                tier=tier,
                config=config,
                width_mm=width_mm,
                height_mm=height_mm,
                is_repeat_design=is_repeat_design,
                margin_pct=margin_pct,
            )

            # + amortizace stroje (pokud addon má stroj a amortizace je zapnutá)
            machine_cost = 0
            amortization_enabled = config.get("amortization_enabled", "True")
            if (
                amortization_enabled == "True"
                and group.machine_id
                and group.machine_id.hourly_amortization
            ):
                machine_cost = (
                    group.machine_id.hourly_amortization / pcs_per_hour
                    if pcs_per_hour else 0
                )

            subtotal = mat_cost + machine_cost

            return {
                "material_name": material.display_name,
                "type": "addon_material",
                "material_cost_raw": round(raw_cost, 6),
                "material_cost": round(mat_cost, 6),
                "machine_cost": round(machine_cost, 6),
                "machine_name": group.machine_id.name if group.machine_id else None,
                "subtotal": round(subtotal, 4),
            }

    # ------------------------------------------------------------------
    # Materiálové náklady (společné pro main i addon)
    # ------------------------------------------------------------------
    def _calc_material_cost(
        self, material, tier, config,
        width_mm, height_mm,
        is_repeat_design, margin_pct,
    ):
        """Materiálové náklady S marží.
        
        Marže jako přirážka: 320% = cena je (1 + 3.20) = 4.2× nákladu.
        Marže 0% = prodám za náklad.
        """
        raw_cost = self._calc_material_cost_raw(
            material=material,
            tier=tier,
            config=config,
            width_mm=width_mm,
            height_mm=height_mm,
            is_repeat_design=is_repeat_design,
        )

        cost_with_margin = raw_cost * (1 + margin_pct / 100)

        return cost_with_margin

    # ------------------------------------------------------------------
    # Pomocné metody
    # ------------------------------------------------------------------

    def _round_price(self, price):
        """Zaokrouhlí cenu na 10 haléřů nahoru.
        
        15.21 → 15.30
        15.30 → 15.30 (beze změny)
        15.01 → 15.10
        """
        import math
        return math.ceil(price * 10) / 10

    def _find_tier(self, group, quantity, pricing_profile_id=None):
        """Najde správnou hladinu pro dané množství, skupinu a cenový profil.

        Args:
            group: label.material.group recordset
            quantity: int – počet kusů
            pricing_profile_id: int|None – ID cenového profilu zákazníka;
                None = použij výchozí Standard profil

        Returns:
            label.production.tier recordset (může být prázdný)

        Pokud profil není nalezen nebo nemá hladinu, použije se výchozí Standard profil.
        """
        domain = [
            ("group_id", "=", group.id),
            ("min_quantity", "<=", quantity),
            ("max_quantity", ">=", quantity),
            ("active", "=", True),
        ]
        if pricing_profile_id:
            tier = self.env["label.production.tier"].search(
                domain + [("pricing_profile_id", "=", pricing_profile_id)],
                limit=1,
            )
            if tier:
                return tier
            # Fallback to Standard profile
        # Use default profile or no profile filter
        standard = self.env["label.pricing.profile"].search(
            [("is_default", "=", True), ("active", "=", True)],
            limit=1,
        )
        if standard:
            return self.env["label.production.tier"].search(
                domain + [("pricing_profile_id", "=", standard.id)],
                limit=1,
            )
        return self.env["label.production.tier"].search(domain, limit=1)

    def _get_effective_pcs_per_hour(self, material, tier):
        """Vrátí pieces_per_hour – s override pokud existuje."""
        override = self.env["label.material.tier.override"].search(
            [
                ("material_id", "=", material.id),
                ("tier_id", "=", tier.id),
            ],
            limit=1,
        )
        if override:
            return override.pieces_per_hour_override
        return tier.pieces_per_hour

    def _get_waste_multiplier(self, tier, is_repeat_design=False):
        """Vypočítá násobitel odpadů.

        Logika: odpady ZMENŠUJÍ využitelnou plochu.
        10% test + 15% prořez → využiju jen 90% × 85% = 76.5% tabule
        → cena za mm² je vyšší: dělím menší plochou
        → ekvivalent: násobím 1/0.90 × 1/0.85 = 1.3072

        U opakovaného designu: test = 0% → 1/1.00 × 1/0.85 = 1.1765
        """
        test_pct = 0 if is_repeat_design else tier.waste_test_percentage
        prune_pct = tier.waste_pruning_percentage

        test_factor = 1 / (1 - test_pct / 100) if test_pct < 100 else 1
        prune_factor = 1 / (1 - prune_pct / 100) if prune_pct < 100 else 1

        return test_factor * prune_factor


    def _get_effective_hourly_rate(self, config):
        """Hodinová sazba + fixní náklady rozpočítané na hodinu."""
        hourly_rate = float(config.get("hourly_rate", 800))

        fixed_costs_enabled = config.get("fixed_costs_enabled", "True")
        fixed_per_hour = 0

        if fixed_costs_enabled == "True":
            fixed_rent = float(config.get("fixed_rent_yearly", 0))
            fixed_energy = float(config.get("fixed_energy_yearly", 0))
            fixed_other = float(config.get("fixed_other_yearly", 0))
            working_hours = float(config.get("working_hours_yearly", 2000))

            fixed_total = fixed_rent + fixed_energy + fixed_other
            fixed_per_hour = fixed_total / working_hours if working_hours else 0

        return hourly_rate + fixed_per_hour

    def _get_config(self):
        """Načte všechna nastavení z ir.config_parameter."""
        ICP = self.env["ir.config_parameter"].sudo()
        return {
            "hourly_rate": ICP.get_param("label_calc.hourly_rate", "800"),
            "admin_overhead_enabled": ICP.get_param(
                "label_calc.admin_overhead_enabled", "False"
            ),
            "admin_overhead_minutes": ICP.get_param(
                "label_calc.admin_overhead_minutes", "15"
            ),
            "amortization_enabled": ICP.get_param(
                "label_calc.amortization_enabled", "True"
            ),
            "fixed_costs_enabled": ICP.get_param(
                "label_calc.fixed_costs_enabled", "True"
            ),
            "vat_surcharge_pct": ICP.get_param(
                "label_calc.vat_surcharge_pct", "15"
            ),
            "material_margin_pct": ICP.get_param(
                "label_calc.material_margin_pct", "30"
            ),
            "min_order_price": ICP.get_param(
                "label_calc.min_order_price", "250"
            ),
            "min_order_quantity": ICP.get_param(
                "label_calc.min_order_quantity", "50"
            ),
            "fixed_rent_yearly": ICP.get_param(
                "label_calc.fixed_rent_yearly", "0"
            ),
            "fixed_energy_yearly": ICP.get_param(
                "label_calc.fixed_energy_yearly", "0"
            ),
            "fixed_other_yearly": ICP.get_param(
                "label_calc.fixed_other_yearly", "0"
            ),
            "working_hours_yearly": ICP.get_param(
                "label_calc.working_hours_yearly", "2000"
            ),
        }

    def _check_warnings(self, config, quantity, total_price):
        """Zkontroluje minima a vrátí varování."""
        warnings = []

        min_qty = int(config.get("min_order_quantity", 50))
        if quantity < min_qty:
            warnings.append({
                "type": "quantity",
                "message": f"Množství ({quantity} ks) je pod doporučeným "
                           f"minimem ({min_qty} ks)",
            })

        min_price = float(config.get("min_order_price", 250))
        if total_price < min_price:
            warnings.append({
                "type": "price",
                "message": f"Cena zakázky ({total_price:.0f} Kč) je pod "
                           f"minimem ({min_price:.0f} Kč)",
            })

        return warnings

    def _error_result(self, message):
        """Vrátí chybový výsledek."""
        return {
            "unit_price": 0,
            "total_price": 0,
            "quantity": 0,
            "tier_name": None,
            "margin_pct": 0,
            "breakdown": {},
            "warnings": [{"type": "error", "message": message}],
        }
