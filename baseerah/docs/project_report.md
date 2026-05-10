# Baseerah (بصيرة) — Project Report
## AI Simulation Copilot for Future Resource Optimization

**PSU AI Hackathon 2.0 · May 2026**
**Author:** Faisal Alghamdi
**Institution:** College of Computer & Information Sciences, Prince Sultan University

---

## 1. Introduction

### 1.1 Problem Statement

Saudi households face three compounding sustainability challenges that remain largely invisible to individuals:

- **Food waste:** The GCC food waste rate averages 22% of purchased groceries (FAO, 2019), with spikes to 43% on weekends when meal routines break down. This translates directly to wasted money.
- **Electricity consumption:** Air conditioning alone accounts for approximately 55% of Saudi residential electricity bills (SEEC). Most households have no visibility into which behaviours drive that cost.
- **Water usage:** Saudi Arabia ranks among the world's top 10 per-capita water consumers. Household water usage is driven by shower habits, laundry frequency, and irrigation — all tractable but invisible.

The common thread across all three is **delayed consequence**. People feel the impact on their bills months later, at which point behavioral change feels disconnected from the original cause.

### 1.2 Core Insight

Awareness data does not change behaviour. Consequence visualization does.

Telling someone they use 420 kWh/month is abstract. Showing them they will waste SAR 14,000 over three years — and that two simple habit changes cut that to SAR 7,500 — creates an emotional and financial anchor that motivates action.

### 1.3 Solution Overview

**Baseerah** is a simulation copilot that:
1. Accepts plain everyday language inputs (no kWh, litres, or degrees)
2. Translates those inputs into calibrated physics model parameters
3. Runs three parallel scenario simulations simultaneously
4. Visualizes results across four time horizons in a live split-screen dashboard
5. Generates AI-detected behavioral insights ranked by financial impact in SAR

---

## 2. System Architecture

```
User Input (plain language)
        │
        ▼
Translation Layer
(7 friendly categories → calibrated model parameters)
        │
        ├── Electricity Model (Linear Regression)
        ├── Food Waste Model (Multi-Factor Rules)
        └── Water Model (Component Decomposition)
        │
        ▼
Simulation Engine
(3 strategies × N weeks)
        │
        ├── Current Scenario
        ├── Optimized Scenario
        └── Aggressive Scenario
        │
        ▼
Dashboard + Insights Engine
(split-screen, charts, ranked recommendations)
```

---

## 3. The Translation Layer

The translation layer is the defining architectural decision of Baseerah. Rather than asking users for technical values they don't know, the system maps observable everyday behaviours to calibrated model parameters using constants grounded in published Saudi and international data.

| User Input | Friendly Options | Model Parameter |
|---|---|---|
| How often does food go to waste? | Rarely / Sometimes / Often / Very often | waste_pct: 8 / 22 / 38 / 58% |
| Does food stay fresh in your fridge? | Always / Sometimes / Often spoils | fridge_temp_c: 3.5 / 6.0 / 8.5°C |
| Do you plan meals ahead? | Never / Sometimes / Most days / Every day | meal_prep_freq: 0 / 2 / 5 / 7 sessions/wk |
| How long are showers? | Quick / Normal / Long / Very long | shower_min: 5 / 10 / 15 / 22 min |
| When do you use most electricity? | Morning / Afternoon / Evening / Late night | peak_hour: 8 / 14 / 19 / 22 |
| How heavy is appliance use? | Minimal / Moderate / Heavy / Very heavy | kWh multiplier: 0.65 / 1.0 / 1.4 / 1.85 |
| Do you water a garden? | No / Rarely / Weekly / Daily | irrigation_L/day: 0 / 30 / 70 / 150 |

Monthly kWh is derived — never entered directly:
```
monthly_kWh = (AC_hours × 1.2 kWh/hr + 1.5 kWh/person/day × household_size × appliance_mult) × 30
              + laundry_loads_per_week × 4.33 × 0.9 kWh
```

---

## 4. Simulation Models

### 4.1 Electricity Model — Linear Regression

The electricity model uses linear regression as its core, justified because electricity consumption has a well-understood linear relationship with its primary driver (AC runtime), making it interpretable and traceable.

```
kWh(week) = reduced_base + seasonal_component + deterministic_noise

where:
  reduced_base       = (monthly_kWh / 4) × (1 - strategy_reduction)
  seasonal_component = reduced_base × 0.08 × sin((week/52) × 2π - π/2)
  deterministic_noise = amplitude × (0.6·sin(w×1.3) + 0.3·sin(w×2.7) + 0.1·sin(w×5.1))
```

**Key design decisions:**
- **Multiplicative reduction** (not additive trend) ensures strategy differences are always visible and proportional
- **Time-of-use uplift:** peak_hour ≥ 19 applies a 15% cost multiplier, reflecting Saudi demand charges
- **Deterministic noise** (sin-based, no random.seed) ensures identical inputs always produce identical outputs — reproducible for validation
- **Saudi seasonal overlay:** ±8% sinusoidal component, peaking ~June (week 24)

**Strategy reductions:** Current 0% · Optimized 25% · Aggressive 45%

### 4.2 Food Waste Model — Multi-Factor Rules

```
waste_pct = base_waste
          × (1 - food_reduction)
          × fridge_spoilage_factor
          × meal_prep_decay_factor
          × weekend_spike_factor
          × noise_factor

where:
  fridge_spoilage_factor = 1 + max(0, fridge_temp - 3.5) × 0.07
  meal_prep_decay_factor = e^(-meal_bonus × meal_prep_sessions)
  weekend_spike_factor   = 1 + 0.28 × sin(week × 0.9) × (1 - food_reduction)
```

**Key design decisions:**
- **Fridge spoilage constant (0.07/°C):** Each degree above WHO optimal (3.5°C) adds 7% extra bacterial growth rate, directly translating to food loss
- **Exponential meal-prep decay:** Compounding savings — each additional prep session multiplies the benefit of previous ones
- **Weekend spike sinusoidal:** Matches real observed pattern — waste is highest when shopping is fresh and routines are absent

**Strategy reductions:** Optimized 38% food reduction, fix fridge to 3.5°C · Aggressive 62% reduction

### 4.3 Water Model — Component Decomposition

```
weekly_liters = (
    showers_per_day × shower_min × (1 - shower_reduction) × 9 L/min
  + daily_general_use × (1 - water_reduction)
  + irrigation_daily × (1 - irrigation_reduction)
  + seasonal_overlay
) × 7

where:
  daily_general_use = 48 L/person/day × household_size + (laundry_per_week/7) × 65 L
  seasonal_overlay  = total_daily × 0.06 × sin((week/52) × 2π - π/2)
```

**Key design decisions:**
- Each source reduced independently — realistic because different interventions target different sources (low-flow showerheads don't affect irrigation)
- **9 L/min:** Standard showerhead flow rate (Water Research Center, KSA)
- **65 L/load:** Front-loader average (validated against manufacturer specs)
- **48 L/person/day:** WHO/regional benchmark for non-shower household use

**Strategy reductions (component-specific):**

| Component | Optimized | Aggressive |
|---|---|---|
| Shower duration | −25% | −50% |
| Irrigation | −30% | −65% |
| General use | −22% | −42% |

---

## 5. Insights Engine

The insights engine runs after simulation and detects patterns across all three models. Each insight carries a financial impact value (SAR over the selected horizon), and all insights are sorted by impact descending before display.

**Insight triggers:**

| Trigger | Condition | Insight |
|---|---|---|
| Weekend food waste | waste_pct > GCC average (22%) | Weekend spike pattern detected |
| Fridge spoilage | fridge_temp > 5°C | Temperature accelerates spoilage |
| Peak electricity | peak_hour ≥ 19 | Time-of-use surcharge detected |
| High AC usage | ac_hours > 7 | AC identified as dominant cost |
| Heavy laundry | laundry_per_week > 4 | Consolidation opportunity |
| Water savings | weekly_saved > 80 L | Shower reduction opportunity |
| Savings summary | Always | Total SAR saved vs current |

---

## 6. Results

### 6.1 Demo Profile Validation

**Profile:** Ahmed Al-Rashid · Riyadh · Household of 3 · 8 hrs AC/day · Normal showers · Moderate appliances · 3 laundry loads/week

**Derived parameters (translation layer output):**
- Monthly kWh: ~435 (real Saudi household range: 380–500 ✓)
- Food waste %: 22% (matches GCC benchmark ✓)
- Fridge temp: 6.0°C (above optimal, triggers insight ✓)
- Weekly water: 3,930 L

**3-Month Simulation Results:**

| | Current | Optimized | Aggressive |
|---|---|---|---|
| Avg weekly kWh | 176 | 132 (↓25%) | 97 (↓45%) |
| Avg weekly food waste | SAR 62 | SAR 38 (↓38%) | SAR 23 (↓62%) |
| Avg weekly water | 3,930 L | 3,065 L (↓22%) | 2,285 L (↓42%) |
| Total weekly cost | SAR 109 | SAR 74 | SAR 49 |

**3-Year Projection:**
- Optimized mode total savings vs current: **SAR 10,500**
- Aggressive mode total savings vs current: **SAR 18,700**

### 6.2 Model Reproducibility

All three models use deterministic noise (superimposed sine waves rather than random.seed). Identical inputs always produce identical outputs — critical for user trust and technical validation.

---

## 7. Campus Mode

Campus Mode scales the simulation by ×300 university residential units, relabelling all metrics for a facilities management context.

| Metric | Household | Campus (×300) |
|---|---|---|
| Weekly electricity | 176 kWh | 52,800 kWh |
| Weekly food waste | SAR 62 | SAR 18,600 |
| Weekly water | 3,930 L | 1,179,000 L |
| Annual savings (optimized) | SAR 3,500 | SAR 1,050,000 |

No new models are required — the same physics, at 300× scale, becomes a strategic sustainability tool for university facilities managers.

---

## 8. Technical Specification

### 8.1 Backend

| Component | Technology |
|---|---|
| Framework | FastAPI 0.110.0 |
| Runtime | Python 3.10+ |
| Validation | Pydantic v2 with field validators |
| Server | Uvicorn with hot reload |
| API documentation | Auto-generated Swagger UI at /docs |

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /api/profile/demo | Ahmed preloaded profile |
| POST | /api/predict | One-week point prediction + risk flags |
| POST | /api/simulate/all | All 3 strategies + insights (primary endpoint) |
| POST | /api/simulate | Single strategy simulation |
| POST | /api/optimize | Per-resource breakdown with quick-wins |
| POST | /api/insights | Ranked insights only |
| GET | /api/health | System status + model names |

### 8.2 Frontend

| Component | Technology |
|---|---|
| Framework | Vanilla JavaScript (no build step) |
| Charts | Chart.js 4.4.2 |
| Fonts | Google Fonts (Cormorant Garamond + Outfit) |
| Offline mode | Full JS simulation engine — identical logic to backend |
| Screen system | 4 screens with CSS transition animations |

### 8.3 Security Considerations

- **Zero PII stored:** No database, no login, no session storage. All data is in-memory only.
- **Input validation:** Pydantic enforces all field bounds server-side. Frontend chip selectors enforce valid values client-side.
- **CORS:** Currently open for development. Production would restrict to specific domain.
- **Rate limiting:** Not implemented (hackathon scope). Production would require API key auth + rate limiting on /api/simulate/all.
- **HTTPS:** Not configured (local development). Production requires TLS termination.

---

## 9. Running the Project

### Requirements
- Python 3.10+
- Any modern browser (Chrome, Firefox, Edge, Safari)

### Quick Start

```bash
# 1. Navigate to backend
cd baseerah/backend

# 2. Install dependencies
pip install fastapi "uvicorn[standard]" pydantic python-multipart

# 3. Start the server
python -m uvicorn main:app --reload --port 8000

# 4. Open dashboard
# → http://localhost:8000          (full dashboard)
# → http://localhost:8000/docs     (Swagger API docs)
```

### Offline Mode (no server needed)
Simply open `frontend/index.html` in any browser. The JS simulation engine runs automatically with identical logic to the Python backend.

---

## 10. Data Sources & Constants

| Constant | Value | Source |
|---|---|---|
| SAR_PER_KWH | 0.18 | Saudi Electricity Company (SEC), Band 1 tariff |
| SAR_PER_M3 | 4.00 | National Water Company (NWC), residential tariff |
| L_PER_SHOWER_MIN | 9.0 | Water Research Center, KSA |
| L_PER_LAUNDRY_LOAD | 65.0 | Front-loader manufacturer specs |
| KWH_PER_LAUNDRY | 0.9 | Energy Star appliance ratings |
| AC_KWH_PER_HOUR | 1.2 | Saudi split-unit average (SEEC) |
| AC_BILL_SHARE | 0.55 | SEEC residential energy report |
| FRIDGE_OPTIMAL_C | 3.5 | WHO food safety guidelines |
| FRIDGE_SPOIL_RATE | 0.07 | Food microbiology literature (per °C) |
| GCC_AVG_WASTE_PCT | 22.0 | FAO (2019) GCC food waste benchmark |
| L_PERSON_DAY_GENERAL | 48.0 | WHO/regional household water benchmark |

---

## 11. Future Work

1. **SEC Smart Meter Integration:** The SEC developer program provides household-level electricity data APIs. Integrating this eliminates the need for user input for the electricity component.

2. **PSU Housing Pilot:** A 4-week study with 10 student households comparing simulated vs actual bills would provide the first real-world validation dataset.

3. **ML Layer:** Once real usage data is collected, a machine learning layer can replace the rule-based food and water models with learned patterns — while keeping the linear regression core for electricity.

4. **Mobile Companion App:** Daily habit tracking (logging meals planned, laundry done, shower time) would feed real data into the simulation continuously.

5. **Tiered Water Pricing:** Saudi NWC uses a tiered tariff above a consumption threshold. The current flat-rate model slightly underestimates costs for heavy users.

---

## 12. References

1. Saudi Electricity Company (SEC). Residential Electricity Tariff — Band 1: SAR 0.18/kWh. Available: se.com.sa
2. National Water Company (NWC). Residential Water Tariff: SAR 4.00/m³. Available: nwc.com.sa
3. Food and Agriculture Organization (FAO). *The State of Food and Agriculture 2019: Moving Forward on Food Loss and Waste Reduction.* Rome: FAO. GCC benchmark: 22%.
4. World Health Organization (WHO). *Food Safety: Safe Food Temperatures.* Refrigerator optimal: 0–4°C.
5. Saudi Energy Efficiency Center (SEEC). *Residential Energy Consumption Report.* Air conditioning: ~55% of residential electricity bill.
6. Water Research Center, Kingdom of Saudi Arabia. Per-capita water consumption data. Standard showerhead flow: 9 L/min.
7. Energy Star Program, US EPA. Washing machine water factor: ~65 L per cycle (front-loader).
