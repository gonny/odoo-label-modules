# 🏷️ Odoo Label ERP – Architecture & Roadmap

> Vlastní ERP systém pro výrobu gravírovaných štítků a textilních etiket
> Postaveno na Odoo 19 Community Edition

---

## 📋 Obsah

- [Tech Stack](#tech-stack)
- [Architektura](#architektura)
- [Struktura repozitáře](#struktura-repozitáře)
- [Fáze 1 – Nahraď Profit + Excel](#fáze-1--nahraď-profit--excel)
- [Fáze 2 – Chytré funkce + Veřejná kalkulačka](#fáze-2--chytré-funkce--veřejná-kalkulačka)
- [Fáze 3 – Bonus (automatizace)](#fáze-3--bonus-automatizace)
- [Konfigurace systému](#konfigurace-systému)
- [Kalkulační model](#kalkulační-model)
- [UX principy](#ux-principy)
- [Changelog](#changelog)

---

## Tech Stack

| Komponenta | Technologie |
|---|---|
| ERP | Odoo 19 Community Edition |
| Databáze | PostgreSQL 16 |
| Kontejnerizace | Docker + Docker Compose |
| OS | Windows + WSL2 |
| Vývoj | VS Code + Python 3.12 |
| Veřejná kalkulačka | SvelteKit (SSG) |
| Hosting kalkulačky | Cloudflare Pages (zdarma) |
| Vzdálený přístup | Cloudflare Tunnel (zdarma) |
| Verzování | Git + GitHub |

---

## Architektura

```
┌─────────────────────────────────────────────────┐
│                  FRONTEND                        │
│                                                  │
│  Odoo Web UI          SvelteKit SSG              │
│  (interní)            (veřejná kalkulačka)       │
│  localhost:8069       Cloudflare Pages            │
└────────┬─────────────────────┬───────────────────┘
         │                     │
         │              REST API (build time)
         │                     │
┌────────▼─────────────────────▼───────────────────┐
│                  ODOO SERVER                      │
│                                                   │
│  Standardní moduly:        Vlastní moduly:        │
│  ├── Contacts              ├── label_calculator   │
│  ├── Sales                 ├── customer_designs   │
│  ├── Invoicing             ├── loyalty_discount   │
│  ├── CRM                   ├── shipping_packeta   │
│  ├── Inventory             ├── shipping_cp        │
│  └── Manufacturing         ├── shipping_dpd       │
│                            ├── payment_comgate    │
│  OCA moduly:               ├── bank_partners      │
│  └── l10n_cz               ├── price_api          │
│                            └── label_reports      │
└────────┬─────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────┐
│              PostgreSQL 16                        │
│              (Docker volume)                      │
└──────────────────────────────────────────────────┘
```

---

## Struktura repozitáře

```
odoo-label-modules/
├── ARCHITECTURE.md              ← tento soubor
├── README.md
├── docker-compose.yml
├── .env
├── .gitignore
│
├── config/
│   └── odoo.conf
│
├── addons/
│   ├── label_calculator/        ← Fáze 1
│   ├── loyalty_discount/        ← Fáze 1
│   ├── customer_designs/        ← Fáze 2
│   ├── price_history/           ← Fáze 2
│   ├── shipping_packeta/        ← Fáze 2
│   ├── shipping_cp/             ← Fáze 2
│   ├── price_api/               ← Fáze 2
│   ├── shipping_dpd/            ← Fáze 3
│   ├── payment_comgate/         ← Fáze 3
│   ├── bank_partners/           ← Fáze 3
│   └── label_reports/           ← Fáze 3
│
├── calculator-web/              ← Fáze 2 (SvelteKit)
│   ├── src/
│   ├── package.json
│   └── svelte.config.js
│
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   └── import_from_profit.py
│
└── docs/
    ├── import-guide.md
    └── api-reference.md
```

---

## Fáze 1 – Nahraď Profit + Excel

> **Cíl:** Fakturovat v Odoo rychleji než v Profitu + Excelu
> **Časový odhad:** 2–3 týdny
> **Výsledek:** Konec Excelu, konec přepínání mezi nástroji

### Epic 1.0: Infrastruktura

- [ ] **Story 1.0.1: Docker setup**
  - [x] Vytvořit `docker-compose.yml` (Odoo 17 + PostgreSQL 15)
  - [x] Vytvořit `config/odoo.conf` s dev mode
  - [x] Vytvořit `.env` soubor (hesla, porty)
  - [x] Vytvořit `.gitignore`
  - [x] Ověřit spuštění: `docker compose up -d`
  - [x] Ověřit přístup: `http://localhost:8069`
  - [x] Vytvořit databázi `odoo_label`
  - [ ] Aktivovat Developer Mode

- [ ] **Story 1.0.2: Git repozitář**
  - [x] Inicializovat Git repo
  - [x] Vytvořit `README.md`
  - [x] Vytvořit `ARCHITECTURE.md` (tento soubor)
  - [x] Push na GitHub
  
- [ ] **Story 1.0.3: Instalace standardních modulů**
  - [x] Nainstalovat modul Contacts (Kontakty)
  - [x] Nainstalovat modul Sales (Prodej)
  - [x] Nainstalovat modul Invoicing (Fakturace)
  - [ ] Základní konfigurace firmy (název, adresa, logo, IČO)

### Epic 1.1: Import dat z Profitu

- [ ] **Story 1.1.1: Export z Profitu**
  - [ ] Exportovat zákazníky do CSV (název, IČO, adresa, kontakt, email)
  - [ ] Exportovat doručovací adresy (parcelbox, šicí dílny)
  - [ ] Exportovat produkty/číselníky
  - [ ] Exportovat historii faktur (pro výpočet věrnostních slev)
  - [ ] Zdokumentovat strukturu exportu

- [ ] **Story 1.1.2: Import do Odoo**
  - [ ] Vytvořit import skript / CSV šablonu pro zákazníky
  - [ ] Importovat ~1000 zákazníků
  - [ ] Importovat doručovací adresy (přiřadit k zákazníkům)
  - [ ] Ověřit správnost importu (náhodný vzorek 20 zákazníků)

### Epic 1.2: Modul `label_calculator`

> Hlavní kalkulační modul – srdce celého systému

- [x] **Story 1.2.1: Model `label.material` – Materiály**
  - [x] Definovat model (name, material_type, color, color_hex)
  - [x] Pole pro plošný materiál (price_per_m2, thickness_mm)
  - [x] Pole pro stuhu (width_mm, price_per_meter)
  - [x] Pole pro TTR pásku (ttr_length_m, ttr_width_mm, ttr_price_per_roll)
  - [x] Pole pro komponenty (component_price)
  - [x] Computed pole: price_per_mm2, price_per_mm_length
  - [x] Výrobní poznámky (laser_power_pct, laser_speed, production_notes)
  - [x] Formulářový view (dynamické zobrazení dle typu)
  - [x] Seznamový view
  - [x] Přístupová práva (security/ir.model.access.csv)
  - [x] Naplnit daty: 6 typů × ~50 barev

- [x] **Story 1.2.2: Model `label.machine` – Stroje**
  - [x] Definovat model (name, purchase_price, lifetime_years, hours_per_year)
  - [x] Computed pole: hourly_amortization
  - [x] Formulářový a seznamový view
  - [x] Přístupová práva
  - [x] Naplnit daty (laser, tiskárna etiket)

- [x] **Story 1.2.3: Model `label.production.tier` – Hladiny**
  - [x] Definovat model (name, min_quantity, max_quantity, pieces_per_hour, waste_test_pieces)
  - [x] Formulářový a seznamový view
  - [x] Přístupová práva
  - [x] Naplnit výchozími daty (4 hladiny)

- [x] **Story 1.2.4: Globální nastavení (res.config.settings)**
  - [x] Hodinová sazba (hourly_rate)
  - [x] Admin overhead na zakázku (admin_overhead_minutes)
  - [x] DPH přirážka % (vat_surcharge_pct)
  - [x] Marže na materiál % (material_margin_pct)
  - [x] Minimální cena zakázky (min_order_price)
  - [x] View v Nastavení

- [ ] **Story 1.2.5: Rozšíření `product.template` – Typ cenotvorby**
  - [ ] Přidat pole pricing_type: 'fixed' / 'calculator'
  - [ ] Přidat vazbu na materiál (material_id → label.material)
  - [ ] Přidat vazbu na stroj (machine_id → label.machine)
  - [ ] Přidat pole pro výchozí odpad % (default_waste_pct)
  - [ ] View: zobrazit nová pole ve formuláři produktu
  - [ ] Naplnit produkty: materiály × barvy + fixní cena produkty (koženka apod.)

- [ ] **Story 1.2.6: Kalkulace v prodejní objednávce (sale.order.line)**
  - [ ] Přidat pole: width_mm, height_mm (rozměr štítku)
  - [ ] Přidat pole: calculated_price (navržená cena z kalkulátoru)
  - [ ] Přidat pole: last_price (minulá cena – hint)
  - [ ] Logika: při změně produktu + rozměru + množství → auto-výpočet ceny
  - [ ] Logika: pokud pricing_type == 'fixed' → standardní chování
  - [ ] Logika: pokud pricing_type == 'calculator' → spustit kalkulaci
  - [ ] Logika: detekce hladiny dle množství
  - [ ] Logika: nalezení minulé ceny pro stejný produkt + zákazníka
  - [ ] View: čistý řádek (produkt, rozměr, ks, cena, celkem)
  - [ ] View: detail na klik (rozpad kalkulace, historie, poznámky)

- [ ] **Story 1.2.7: Menu a navigace**
  - [ ] Hlavní menu "🏷️ Štítky"
  - [ ] Podmenu "⚙️ Konfigurace" → Materiály, Stroje, Hladiny
  - [ ] Podmenu "🧮 Kalkulace" (pokud bude samostatný view)

### Epic 1.3: Modul `loyalty_discount`

- [ ] **Story 1.3.1: Věrnostní slevy**
  - [ ] Definovat model `loyalty.tier` (name, min_spent, discount_pct)
  - [ ] Rozšířit `res.partner`: computed pole total_spent, discount_tier, discount_pct
  - [ ] Logika: výpočet celkové útraty z potvrzených faktur
  - [ ] Logika: automatická detekce hladiny
  - [ ] Logika: sleva se aplikuje na produkty, NE na přepravu
  - [ ] View: zobrazit věrnostní úroveň v kartě zákazníka
  - [ ] View: zobrazit slevu v prodejní objednávce
  - [ ] Naplnit daty (Bronze 5%, Silver 10%, Gold 15% + prahy)
  - [ ] Import historické útraty z Profitu (pro správné zařazení)

### Epic 1.4: Česká lokalizace

- [ ] **Story 1.4.1: Czech Accounting (OCA)**
  - [ ] Najít a nainstalovat l10n_cz modul (nebo ekvivalent pro v17)
  - [ ] Konfigurace české měny (CZK)
  - [ ] Konfigurace formátu faktur (IČO, DIČ – neplátce)
  - [ ] Ověřit formát faktur dle české legislativy

### Epic 1.5: Testování a go-live Fáze 1

- [ ] **Story 1.5.1: Testování**
  - [ ] Vytvořit testovacího zákazníka
  - [ ] Vytvořit zakázku s kalkulovaným produktem (gravír)
  - [ ] Vytvořit zakázku s kalkulovaným produktem (textil)
  - [ ] Vytvořit zakázku s fixní cenou (koženka)
  - [ ] Ověřit kalkulaci vs. Excel (stejné výsledky?)
  - [ ] Ověřit věrnostní slevu
  - [ ] Ověřit minulou cenu (hint)
  - [ ] Ověřit více doručovacích adres
  - [ ] Vytvořit a odeslat fakturu
  - [ ] Celkový čas na fakturu < 1 minuta?

- [ ] **Story 1.5.2: Go-live**
  - [ ] Přesunout na produkční stroj (i3) nebo nechat na pracovním PC
  - [ ] Nastavit Cloudflare Tunnel (přístup zvenku)
  - [ ] Nastavit automatické zálohy (cron → pg_dump)
  - [ ] Začít fakturovat v Odoo (paralelně s Profitem 1 týden)
  - [ ] Konec Profitu pro nové faktury ✅

---

## Fáze 2 – Chytré funkce + Veřejná kalkulačka

> **Cíl:** Sledování poptávek, historie designů, tisk štítků přepravců, veřejná kalkulačka
> **Časový odhad:** 2–3 týdny
> **Výsledek:** Kompletní workflow od poptávky po expedici + zákazníci si počítají cenu sami

### Epic 2.1: CRM Pipeline

- [ ] **Story 2.1.1: Konfigurace CRM**
  - [ ] Nainstalovat modul CRM
  - [ ] Vytvořit pipeline stages: Nová poptávka → Komunikace → Grafika → Vzorek → Schváleno
  - [ ] Přidat pole: kanál poptávky (IG, FB, email, web, WA, messenger)
  - [ ] Přidat pole: komunikační log (jednoduchý text + datum)
  - [ ] Přidat pole: přílohy (PDF okótované, fotky vzorků)
  - [ ] View: Kanban board s kartami
  - [ ] Logika: ze schválené poptávky → vytvořit prodejní objednávku (1 klik)

### Epic 2.2: Modul `customer_designs`

- [ ] **Story 2.2.1: Model zákaznického designu**
  - [ ] Definovat model `label.customer.design`
  - [ ] Pole: name, partner_id, product_type (gravír/textil)
  - [ ] Pole: preview_image (náhled – Image field)
  - [ ] Pole: file_path (cesta k CDR na disku)
  - [ ] Pole: attachment_ids (přílohy – PDF, obrázky)
  - [ ] Pole: notes (výrobní poznámky)
  - [ ] Pole: is_tested (boolean – otestováno ✅)
  - [ ] Relace: order_line_ids → historie objednávek
  - [ ] Formulářový view
  - [ ] Seznamový view (s náhledy)

- [ ] **Story 2.2.2: Integrace do zákaznické karty**
  - [ ] Rozšířit res.partner: design_ids (One2many)
  - [ ] View: záložka "Designy" v kartě zákazníka
  - [ ] View: počet designů na kartě

- [ ] **Story 2.2.3: Integrace do prodejní objednávky**
  - [ ] Přidat pole design_id na sale.order.line
  - [ ] Logika: při výběru zákazníka → nabídnout jeho designy
  - [ ] Logika: při výběru designu → předvyplnit materiál, rozměr z posledního objednávky
  - [ ] Logika: nový design → test_waste z hladiny, opakovaný → test_waste = 0
  - [ ] View: výběr designu v řádku objednávky

### Epic 2.3: Modul `price_history`

- [ ] **Story 2.3.1: Historie cen**
  - [ ] Logika: při potvrzení objednávky → uložit cenu per produkt + zákazník + design
  - [ ] Logika: při nové objednávce → najít poslední cenu a zobrazit jako hint
  - [ ] Logika: vypočítat rozdíl (%) mezi kalkulovanou a minulou cenou
  - [ ] View: hint pod položkou: "Minule: 2,15 Kč (FV-2025-089)"
  - [ ] View: možnost "Použít minulou cenu" jedním klikem

### Epic 2.4: Modul `shipping_packeta`

- [ ] **Story 2.4.1: Konfigurace**
  - [ ] Model pro API credentials (api_key, sender info)
  - [ ] View v Nastavení

- [ ] **Story 2.4.2: Vytvoření zásilky**
  - [ ] Integrace s delivery.carrier (Odoo shipping framework)
  - [ ] API volání: vytvoření zásilky (packetAttributes)
  - [ ] Uložení tracking čísla
  - [ ] Podpora: na adresu, na výdejní místo (Z-Box, pobočka)

- [ ] **Story 2.4.3: Tisk štítků**
  - [ ] API volání: stažení PDF štítku
  - [ ] Tlačítko "Tisk štítku" na dodacím listu
  - [ ] Podpora více zásilek na jednu objednávku (více doručovacích adres)

### Epic 2.5: Modul `shipping_cp`

- [ ] **Story 2.5.1: Konfigurace**
  - [ ] Model pro API credentials (Česká pošta / Balíkovna)
  - [ ] View v Nastavení

- [ ] **Story 2.5.2: Vytvoření zásilky + tisk**
  - [ ] API integrace (SOAP nebo REST dle aktuálního API)
  - [ ] Vytvoření zásilky
  - [ ] Tisk podacího archu / štítku
  - [ ] Tracking

### Epic 2.6: Veřejná kalkulačka (SvelteKit)

- [ ] **Story 2.6.1: Modul `price_api` – REST endpoint v Odoo**
  - [ ] Endpoint: GET /api/label/materials → seznam materiálů + barev + cen
  - [ ] Endpoint: GET /api/label/tiers → hladiny
  - [ ] Endpoint: GET /api/label/config → marže, DPH přirážka, min. zakázka
  - [ ] Autentizace: API klíč (jen pro build time)
  - [ ] Dokumentace API (docs/api-reference.md)

- [ ] **Story 2.6.2: SvelteKit aplikace**
  - [ ] Inicializovat SvelteKit projekt (calculator-web/)
  - [ ] Konfigurace SSG (static adapter)
  - [ ] Data loader: fetch z Odoo API při buildu
  - [ ] Komponenta: výběr typu (gravír / textil)
  - [ ] Komponenta: výběr materiálu + barvy (s barevnými čtverečky)
  - [ ] Komponenta: rozměr (input + slider)
  - [ ] Komponenta: cenová tabulka (všechny hladiny najednou)
  - [ ] Komponenta: vlastní množství (input → live výpočet)
  - [ ] Responzivní design (mobil – zákazníci píšou z telefonu!)
  - [ ] Disclaimer: "Ceny jsou orientační"

- [ ] **Story 2.6.3: Poptávkový formulář**
  - [ ] Formulář na kalkulačce: jméno, email, popis, rozměr, množství
  - [ ] Odeslání do Odoo CRM (POST /api/label/lead) → vytvoří poptávku
  - [ ] Potvrzovací zpráva

- [ ] **Story 2.6.4: Deployment**
  - [ ] Deploy na Cloudflare Pages
  - [ ] Vlastní doména (kalkulacka.tvojestranka.cz)
  - [ ] Build script pro rebuild při změně cen
  - [ ] Dokumentace: jak spustit rebuild

### Epic 2.7: Testování a go-live Fáze 2

- [ ] **Story 2.7.1: Testování**
  - [ ] CRM: vytvořit poptávku, provést celým pipeline
  - [ ] Designy: vytvořit design, přiřadit k objednávce
  - [ ] Price history: ověřit hint minulé ceny
  - [ ] Packeta: odeslat testovací zásilku (sandbox API)
  - [ ] Česká pošta: odeslat testovací zásilku
  - [ ] Kalkulačka: otestovat na mobilu + desktopu
  - [ ] Kalkulačka: ověřit ceny vs. interní kalkulátor

- [ ] **Story 2.7.2: Go-live**
  - [ ] Nasadit kalkulačku na web
  - [ ] Přepnout přepravce na produkční API klíče
  - [ ] Sdílet link na kalkulačku zákazníkům

---

## Fáze 3 – Bonus (automatizace)

> **Cíl:** Online platby, automatické párování, sklad, výroba, statistiky
> **Časový odhad:** průběžně
> **Výsledek:** Plně automatizovaný systém

### Epic 3.1: Modul `shipping_dpd`

- [ ] **Story 3.1.1: DPD API integrace**
  - [ ] Konfigurace API credentials
  - [ ] Vytvoření zásilky
  - [ ] Tisk štítků
  - [ ] Tracking

### Epic 3.2: Modul `payment_comgate`

- [ ] **Story 3.2.1: ComGate integrace**
  - [ ] Konfigurace API credentials (merchant ID, secret)
  - [ ] Logika: při odeslání faktury → vygenerovat platební odkaz
  - [ ] Logika: zákazník klikne → platební stránka ComGate
  - [ ] Logika: callback → automaticky označit fakturu jako zaplacenou
  - [ ] View: tlačítko "Odeslat s platebním odkazem"
  - [ ] View: stav platby na faktuře
  - [ ] Podpora: kartou, bankovním převodem přes ComGate

### Epic 3.3: Modul `bank_partners`

- [ ] **Story 3.3.1: Partners Bank API**
  - [ ] Konfigurace API credentials
  - [ ] Logika: periodický fetch transakcí (cron job)
  - [ ] Logika: automatické párování plateb s fakturami (dle VS)
  - [ ] Logika: notifikace při přijaté platbě
  - [ ] View: přehled transakcí
  - [ ] View: nepárované platby (ruční přiřazení)

### Epic 3.4: Sklad materiálů

- [ ] **Story 3.4.1: Inventory setup**
  - [ ] Nainstalovat modul Inventory
  - [ ] Vytvořit sklad
  - [ ] Naskladnit materiály (počáteční stavy)
  - [ ] Propojit s kalkulátorem: odpis materiálu při výrobě
  - [ ] Upozornění: nízký stav materiálu

### Epic 3.5: Výrobní zakázky

- [ ] **Story 3.5.1: Manufacturing setup**
  - [ ] Nainstalovat modul Manufacturing
  - [ ] Vytvořit BOM (Bill of Materials) pro typické produkty
  - [ ] Logika: po přijetí platby → automaticky vytvořit výrobní zakázku
  - [ ] Logika: ve výrobní zakázce zobrazit design + výrobní poznámky
  - [ ] Logika: po dokončení výroby → odpis materiálu + přesun do expedice

### Epic 3.6: Statistiky a reporty

- [ ] **Story 3.6.1: Modul `label_reports`**
  - [ ] Dashboard: obrat za měsíc/rok
  - [ ] Report: top 10 zákazníků (dle útraty)
  - [ ] Report: nejprodávanější materiály/barvy
  - [ ] Report: průměrná velikost zakázky
  - [ ] Report: konverzní poměr poptávek (CRM → faktura)
  - [ ] Report: spotřeba materiálu za období

---

## Konfigurace systému

### Výchozí hodnoty (nastavit při prvním spuštění)

```
Hodinová sazba:           800 Kč
Admin overhead/zakázka:   15 min
DPH přirážka:             21 %
Marže na materiál:        30 %
Minimální cena zakázky:   250 Kč

Stroje:
  Laser:      100 000 Kč, 5 let, 1000 hod/rok → 20 Kč/hod
  Tiskárna:    35 000 Kč, 4 roky, 800 hod/rok → 10,94 Kč/hod

Hladiny:
  Malá série:    1–49 ks,   500 ks/hod, test 10 ks
  Střední:      50–99 ks,   750 ks/hod, test 5 ks
  Velká:       100–499 ks, 1000 ks/hod, test 3 ks
  Velkoobjem:  500+ ks,    1200 ks/hod, test 2 ks

Věrnostní slevy:
  Bronze:  od  5 000 Kč útraty →  5 %
  Silver:  od 20 000 Kč útraty → 10 %
  Gold:    od 50 000 Kč útraty → 15 %
  (aplikuje se na produkty, NE na přepravu)
```

---

## Kalkulační model

### Gravírovaný štítek (plošný materiál)

```
cena_za_ks =
  MATERIÁL:
    plocha_mm2 = šířka × výška
    plocha_s_odpadem = plocha_mm2 × (1 + odpad%)
    efektivní_qty = množství + test_odpad_ks
    mat_cost = (plocha_s_odpadem × cena_za_mm2 × efektivní_qty / množství)
    mat_cost × 1.21 (DPH přirážka)
    mat_cost × (1 + marže%)
  + PRÁCE:
    hodinová_sazba / ks_za_hodinu(dle hladiny)
    + (admin_min / 60 × hodinová_sazba / množství)
  + AMORTIZACE:
    amortizace_stroje_za_hod / ks_za_hodinu
  + PŘÍPLATKY:
    nýty, díry, speciální úpravy (fixní Kč/ks)
  - SLEVA:
    věrnostní % (pokud zákazník má)
  = PRODEJNÍ CENA (min. min_cena_zakázky / množství)
```

### Textilní etiketa (stuha + TTR)

```
cena_za_ks =
  STUHA:
    délka_mm = výška_etikety + prořez
    stuha_cost = délka_mm × cena_za_mm_délky
  + TTR:
    plocha_potisku_mm2 = šířka × výška
    ttr_cost = plocha_mm2 × cena_ttr_za_mm2
  + (DPH přirážka + marže + práce + amortizace + příplatky - sleva)
  = PRODEJNÍ CENA
```

---

## UX principy

1. **Čisté zadávání** – hlavní obrazovka: produkt, rozměr, ks, cena, celkem
2. **Detail na klik** – rozpad kalkulace, historie, poznámky jsou schované
3. **Autocomplete** – "sat20č" → Satén 20mm černý potisk
4. **Auto-cena** – kalkulátor předvyplní, přepsat můžeš vždy
5. **Fixní vs. kalkulátor** – per produkt (koženka = fixní, štítek = kalkulátor)
6. **Minulá cena** – hint: "Minule: 2,15 Kč (FV-2025-089)"
7. **Adresa se pamatuje** – výchozí doručovací + více adres
8. **Komunikace mimo Odoo** – WA/IG/mail zůstávají, do Odoo jen log
9. **Faktura odkazem** – zákazník klikne → zaplatí (ComGate)

---

## Changelog

| Datum | Verze | Změna |
|---|---|---|
| 2026-02-06 | 0.1.0 | Inicializace projektu, ARCHITECTURE.md |
| | | |