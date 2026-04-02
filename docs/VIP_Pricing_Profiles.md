# VIP Pricing Profiles

## Overview

The VIP pricing profile system allows different pricing tiers for wholesale (VIP) customers vs standard customers. VIP customers receive better prices through different production tier parameters (higher efficiency, lower margins), **NOT** through discounts.

Two independent pricing systems:
- **Standard**: current tier system + customer discount (Bronze/Silver/Gold)
- **VIP**: separate tiers with better parameters, NO customer discount

## Pricing Profile Model

`label.pricing.profile` stores pricing profile definitions:

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Profile name (e.g., "Standard", "VIP1", "VIP2") |
| `code` | Char | Programmatic identifier (e.g., "standard", "vip1") |
| `is_default` | Boolean | One profile is the default (Standard) |
| `is_vip` | Boolean | VIP profiles don't get customer discounts |
| `description` | Text | Admin notes |
| `active` | Boolean | Archive toggle |
| `sequence` | Integer | Display ordering |

### Seed Profiles

Three profiles are created by default:
1. **Standard** (code: `standard`) – default profile for regular customers
2. **VIP1** (code: `vip1`) – basic wholesale profile
3. **VIP2** (code: `vip2`) – premium wholesale profile

### Tier Assignment

Each `label.production.tier` has a `pricing_profile_id` field linking it to a profile. This allows different tier parameters per material group per profile:

```
Koženka + Standard → Do 30 (80ks/hod, 320%), Do 100 (90ks/hod, 240%), ...
Koženka + VIP1    → 0-∞ (120ks/hod, 180%)
Koženka + VIP2    → 0-∞ (150ks/hod, 120%)
```

VIP tiers typically have ONE tier per material group (0 to 999999) with flat pricing regardless of quantity.

## Customer VIP Status

Extended `res.partner` fields:

| Field | Type | Description |
|-------|------|-------------|
| `label_pricing_profile_id` | Many2one | Customer's pricing profile |
| `label_is_vip` | Boolean | Manual VIP checkbox |
| `label_vip_eligible` | Boolean (computed) | Informational VIP eligibility badge |

### VIP Eligibility Rules

Computed automatically (informational only):
1. Last 3 POSTED invoices for this customer
2. Each invoice `amount_total` > 3000 CZK (EUR invoices converted to CZK)
3. Each invoice has at least one line with `quantity` > 300
4. If ALL conditions met → `label_vip_eligible = True`

**VIP status is MANUAL** – admin must check `label_is_vip` checkbox.

### VIP Effects

When `label_is_vip = True`:
- `label_effective_discount` becomes 0 (no Bronze/Silver/Gold discount)
- `label_pricing_profile_id` must be set to a VIP profile
- Calculator uses VIP profile tiers instead of Standard

When `label_is_vip = False`:
- `label_pricing_profile_id` reverts to Standard
- Normal discount system applies (Bronze/Silver/Gold)

## Calculator Integration

### Tier Selection Flow

```
partner → pricing_profile → tiers filtered by (material_group + profile) → find tier by quantity
```

### Fallback Logic

If no tier exists for the customer's profile + material group combination, the calculator falls back to the Standard profile tier. This ensures VIP customers can always get prices even for material groups without dedicated VIP tiers.

### Price Calculation

The calculation formula is **IDENTICAL** for all profiles – only the tier parameters change:
- `pieces_per_hour` (higher = more efficient → lower labor cost)
- `margin_pct` (lower = cheaper for customer)
- `waste_test_percentage` (lower = less waste)
- Same amortization, hourly rate, fixed costs (unchanged)

## UI Badges

### Customer Form
- Badge "⭐ Nárok na VIP" if eligible but not yet VIP
- Badge "⭐ VIP1" or "⭐ VIP2" when VIP is active
- Pricing profile dropdown visible when VIP is checked

### Sale Order Form
- VIP badge displayed near customer name (e.g., "⭐ VIP1")
- Standard customers show no badge

### Invoice Form
- Same VIP badge as sale order

### Invoice PDF
- Small badge with profile name near customer info section

## Menu Location

Pricing profiles are managed in:
**Kalkulačka štítků → Konfigurace → Cenové profily**

## Testing

15 new tests verify VIP pricing functionality:
- Profile model creation and constraints
- Standard calculation backward compatibility
- VIP1 and VIP2 tier selection and pricing
- Fallback to Standard when no VIP tier exists
- Partner VIP discount = 0
- SO line integration with VIP profiles
- VIP eligibility computation
- Badge display on SO and invoices
