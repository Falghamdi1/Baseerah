"""
╔══════════════════════════════════════════════════════════════════╗
║  BASEERAH AI COPILOT  ·  بصيرة  ·  Backend v3                  ║
║  User-friendly inputs → translation layer → physics simulation  ║
╚══════════════════════════════════════════════════════════════════╝

Architecture
────────────
Users answer plain questions (chips + sliders).
A translation layer converts those to calibrated model parameters.
Three physics-based simulation models run on the translated params.
All outputs are week-level, for any horizon (1–200 weeks).

Input Schema  →  Translation  →  Internal Model Params  →  Simulation
"Often waste"  →  38% waste    →  food_waste_model()    →  weekly SAR lost
"Late night"   →  peak_hour=22 →  electricity_model()   →  ToU cost uplift
"Normal shower"→  10 min       →  water_model()         →  weekly litres
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import math, os

app = FastAPI(title="Baseerah AI Copilot", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(_frontend):
    _static = os.path.join(_frontend, "static")
    if os.path.exists(_static):
        app.mount("/static", StaticFiles(directory=_static), name="static")

# ══════════════════════════════════════════════════════════════════
#  CONSTANTS  (grounded in Saudi / GCC published data)
# ══════════════════════════════════════════════════════════════════
SAR_PER_KWH        = 0.18    # SEC residential tariff, band 1
SAR_PER_M3         = 4.00    # NWC water tariff, residential
LITERS_PER_M3      = 1000.0
L_PER_SHOWER_MIN   = 9.0     # standard showerhead (L/min)
L_PER_LAUNDRY_LOAD = 65.0    # front-loader average
KWH_PER_LAUNDRY    = 0.9     # washing machine per cycle
AC_KWH_PER_HOUR    = 1.2     # typical Saudi split-unit
AC_BILL_SHARE      = 0.55    # AC = ~55 % of Saudi electric bill (SEC data)
FRIDGE_OPTIMAL_C   = 3.5     # WHO/WHO recommended max for fresh food
FRIDGE_SPOIL_RATE  = 0.07    # extra waste % per °C above optimal
GCC_AVG_WASTE_PCT  = 22.0    # GCC benchmark (FAO)
GCC_AVG_KWH_MONTH  = 380.0   # GCC household average

# ──────────────────────────────────────────────────────────────────
#  TRANSLATION TABLES  (user-friendly label → technical value)
# ──────────────────────────────────────────────────────────────────
WASTE_FREQ_TO_PCT: Dict[str, float] = {
    "rarely":     8.0,   # almost nothing thrown away
    "sometimes": 22.0,   # occasional waste, typical GCC
    "often":     38.0,   # regular spoilage
    "very_often":58.0,   # most groceries go bad
}
MEAL_PLAN_TO_FREQ: Dict[str, int] = {
    "never":     0,
    "sometimes": 2,
    "most_days": 5,
    "every_day": 7,
}
FRIDGE_FRESH_TO_C: Dict[str, float] = {
    "always":    3.5,   # well-maintained, food stays cold
    "sometimes": 6.0,   # slightly warm, occasional spoilage
    "often":     8.5,   # too warm, frequent spoilage
}
APPLIANCE_TO_MULT: Dict[str, float] = {
    "minimal":    0.65,  # very light appliance use
    "moderate":   1.00,  # average household
    "heavy":      1.40,  # multiple heavy appliances
    "very_heavy": 1.85,  # very high usage
}
PEAK_TIME_TO_HOUR: Dict[str, int] = {
    "morning":    8,
    "afternoon":  14,
    "evening":    19,
    "late_night": 22,
}
SHOWER_LENGTH_TO_MIN: Dict[str, float] = {
    "quick":     5.0,
    "normal":   10.0,
    "long":     15.0,
    "very_long":22.0,
}
GARDEN_TO_IRR_L: Dict[str, float] = {
    "none":   0.0,
    "rarely": 30.0,    # occasional watering
    "weekly": 70.0,    # regular garden watering
    "daily":  150.0,   # large garden, daily
}

# ══════════════════════════════════════════════════════════════════
#  PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════

class UserInput(BaseModel):
    """
    User-friendly input model.
    All fields are plain English — no kWh, no °C, no litres.
    Translation to model params happens in translate_input().
    """
    name: str = "Ahmed"
    household_size: int = Field(3, ge=1, le=20, description="Number of people in the home")

    # ── Food ──────────────────────────────────────────────────────
    weekly_grocery_spend: float = Field(280.0, ge=50, le=5000,
        description="SAR spent on groceries per week")
    waste_frequency: str = Field("sometimes",
        description="How often food goes to waste: rarely/sometimes/often/very_often")
    meal_planning: str = Field("sometimes",
        description="How often meals are planned ahead: never/sometimes/most_days/every_day")
    fridge_freshness: str = Field("sometimes",
        description="How well the fridge keeps food fresh: always/sometimes/often")

    # ── Electricity ───────────────────────────────────────────────
    ac_hours_per_day: float = Field(8.0, ge=0, le=24,
        description="Hours the AC runs per day")
    appliance_usage: str = Field("moderate",
        description="How heavily other appliances are used: minimal/moderate/heavy/very_heavy")
    peak_time: str = Field("late_night",
        description="When most electricity is used: morning/afternoon/evening/late_night")

    # ── Water ─────────────────────────────────────────────────────
    shower_length: str = Field("normal",
        description="Typical shower duration: quick/normal/long/very_long")
    showers_per_day: int = Field(4, ge=0, le=20,
        description="Total showers per day across the whole household")
    laundry_per_week: int = Field(3, ge=0, le=21,
        description="Number of laundry loads per week")
    garden_watering: str = Field("rarely",
        description="How often outdoor/garden areas are watered: none/rarely/weekly/daily")

    @validator("waste_frequency")
    def check_waste(cls, v):
        assert v in WASTE_FREQ_TO_PCT, f"waste_frequency must be one of {list(WASTE_FREQ_TO_PCT)}"
        return v
    @validator("meal_planning")
    def check_meal(cls, v):
        assert v in MEAL_PLAN_TO_FREQ, f"meal_planning must be one of {list(MEAL_PLAN_TO_FREQ)}"
        return v
    @validator("fridge_freshness")
    def check_fridge(cls, v):
        assert v in FRIDGE_FRESH_TO_C, f"fridge_freshness must be one of {list(FRIDGE_FRESH_TO_C)}"
        return v
    @validator("appliance_usage")
    def check_app(cls, v):
        assert v in APPLIANCE_TO_MULT, f"appliance_usage must be one of {list(APPLIANCE_TO_MULT)}"
        return v
    @validator("peak_time")
    def check_peak(cls, v):
        assert v in PEAK_TIME_TO_HOUR, f"peak_time must be one of {list(PEAK_TIME_TO_HOUR)}"
        return v
    @validator("shower_length")
    def check_shower(cls, v):
        assert v in SHOWER_LENGTH_TO_MIN, f"shower_length must be one of {list(SHOWER_LENGTH_TO_MIN)}"
        return v
    @validator("garden_watering")
    def check_garden(cls, v):
        assert v in GARDEN_TO_IRR_L, f"garden_watering must be one of {list(GARDEN_TO_IRR_L)}"
        return v


class ModelParams:
    """
    Internal model parameters — derived by translation layer.
    Never exposed directly to users.
    """
    def __init__(self, inp: UserInput):
        self.name              = inp.name
        self.household_size    = inp.household_size
        self.weekly_grocery    = inp.weekly_grocery_spend

        # Food
        self.food_waste_pct    = WASTE_FREQ_TO_PCT[inp.waste_frequency]
        self.meal_prep_freq    = MEAL_PLAN_TO_FREQ[inp.meal_planning]
        self.fridge_temp_c     = FRIDGE_FRESH_TO_C[inp.fridge_freshness]

        # Electricity — derive monthly kWh from observable behaviours
        ac_kwh_daily           = inp.ac_hours_per_day * AC_KWH_PER_HOUR
        non_ac_base_daily      = 1.5 * inp.household_size          # other appliances per person
        appliance_mult         = APPLIANCE_TO_MULT[inp.appliance_usage]
        laundry_kwh_monthly    = inp.laundry_per_week * 4.33 * KWH_PER_LAUNDRY
        self.monthly_kwh       = (ac_kwh_daily + non_ac_base_daily * appliance_mult) * 30 + laundry_kwh_monthly
        self.peak_hour         = PEAK_TIME_TO_HOUR[inp.peak_time]
        self.ac_hours          = inp.ac_hours_per_day

        # Water — derive daily liters from observable behaviors
        self.shower_min        = SHOWER_LENGTH_TO_MIN[inp.shower_length]
        self.showers_per_day   = inp.showers_per_day
        laundry_daily_l        = (inp.laundry_per_week / 7.0) * L_PER_LAUNDRY_LOAD
        general_daily_l        = 48.0 * inp.household_size     # drinking, cooking, cleaning
        self.daily_water_l     = general_daily_l + laundry_daily_l
        self.irr_l_per_day     = GARDEN_TO_IRR_L[inp.garden_watering]

        # Pass-through friendly labels for insight generation
        self._waste_freq       = inp.waste_frequency
        self._fridge_fresh     = inp.fridge_freshness
        self._peak_time        = inp.peak_time
        self._shower_length    = inp.shower_length
        self._laundry_per_week = inp.laundry_per_week
        self._appliance_use    = inp.appliance_usage

    def base_weekly_water(self) -> float:
        shower_daily = self.showers_per_day * self.shower_min * L_PER_SHOWER_MIN
        return (self.daily_water_l + shower_daily + self.irr_l_per_day) * 7.0

# ══════════════════════════════════════════════════════════════════
#  STRATEGY PARAMETERS
# ══════════════════════════════════════════════════════════════════
STRATEGIES: Dict[str, Dict] = {
    "current": {
        "label":    "Current Behavior",
        "color":    "#D97706",
        "elec_red": 0.00, "food_red": 0.00, "meal_bonus": 0.00,
        "water_red":0.00, "irr_red":  0.00, "shower_red": 0.00,
        "fix_fridge": False,
    },
    "optimized": {
        "label":    "Optimized Mode",
        "color":    "#0D9488",
        "elec_red": 0.25,   # smart AC schedule, LED lights, off-peak appliances
        "food_red": 0.38,   # meal planning, FIFO fridge organisation
        "meal_bonus":0.15,
        "water_red":0.22,   # low-flow taps, shorter showers
        "irr_red":  0.30,   # drip irrigation
        "shower_red":0.25,  # cut 2–3 min per shower
        "fix_fridge": True, # lower to 3.5°C
    },
    "aggressive": {
        "label":    "Aggressive Savings",
        "color":    "#7C3AED",
        "elec_red": 0.45,   # solar water heater, LED everywhere, smart strips
        "food_red": 0.62,   # zero-waste meal planning, daily list
        "meal_bonus":0.30,
        "water_red":0.42,   # grey-water reuse, aerators on every tap
        "irr_red":  0.65,   # native plants, minimal irrigation
        "shower_red":0.50,  # 5-min showers
        "fix_fridge": True,
    },
}

# ══════════════════════════════════════════════════════════════════
#  DETERMINISTIC NOISE  (reproducible — no random.seed needed)
# ══════════════════════════════════════════════════════════════════
def _noise(week: int, salt: int, amp: float) -> float:
    return amp * (
        0.60 * math.sin(week * 1.31 + salt) +
        0.28 * math.sin(week * 2.73 + salt * 3) +
        0.12 * math.sin(week * 5.17 + salt * 7)
    )

# ══════════════════════════════════════════════════════════════════
#  SIMULATION MODELS
# ══════════════════════════════════════════════════════════════════

def _electricity_model(p: ModelParams, strategy: str, week: int) -> Dict:
    """
    Linear regression model with:
      - Multiplicative reduction on the derived base kWh
      - Saudi seasonal oscillation (summer peak ~June)
      - Time-of-Use cost uplift for evening/late-night users
      - Deterministic noise (reproducible)
    """
    s = STRATEGIES[strategy]
    base_weekly  = p.monthly_kwh / 4.0
    reduced_base = base_weekly * (1.0 - s["elec_red"])

    # Seasonal: Saudi peak ~week 24 (June heat)
    seasonal = reduced_base * 0.08 * math.sin((week / 52.0) * 2 * math.pi - math.pi / 2)
    noise    = _noise(week, 7, reduced_base * 0.048)
    kwh      = max(28.0, reduced_base + seasonal + noise)

    # ToU: evening & late-night users pay ~15% more (demand charges)
    tou_uplift = 1.15 if p.peak_hour >= 19 else 1.0
    cost_sar   = round(kwh * SAR_PER_KWH * tou_uplift, 2)

    return {"kwh": round(kwh, 1), "cost_sar": cost_sar, "tou_pct": round((tou_uplift-1)*100,1)}


def _food_model(p: ModelParams, strategy: str, week: int) -> Dict:
    """
    Multi-factor rule model:
      1. Base waste from user-reported frequency (translated to %)
      2. Fridge temperature spoilage factor (FRIDGE_SPOIL_RATE per °C above optimal)
      3. Meal-prep exponential decay (each session compounds the savings)
      4. Weekend spike (sin cycle — waste is higher when routine breaks)
      5. Small deterministic noise
    """
    s = STRATEGIES[strategy]

    # Fridge: fix_fridge strategies lower temp to optimal
    eff_temp  = FRIDGE_OPTIMAL_C if s["fix_fridge"] else p.fridge_temp_c
    fridge_f  = 1.0 + max(0, eff_temp - FRIDGE_OPTIMAL_C) * FRIDGE_SPOIL_RATE

    # Meal prep: exponential decay — more sessions = compounding savings
    meal_f    = math.exp(-s["meal_bonus"] * p.meal_prep_freq)

    # Weekend spike oscillates on a weekly cycle; dampened by food reduction
    weekend_f = 1.0 + 0.28 * math.sin(week * 0.90) * (1.0 - s["food_red"])

    # Noise ±4%
    noise_f   = 1.0 + _noise(week, 13, 0.04)

    adj_pct   = max(2.0, min(90.0,
        p.food_waste_pct * (1.0 - s["food_red"]) * fridge_f * meal_f * weekend_f * noise_f
    ))
    wasted_sar = round(p.weekly_grocery * (adj_pct / 100.0), 2)
    saved_meals = max(0.0, round(
        (p.food_waste_pct - adj_pct) / 100.0 * p.weekly_grocery / 25.0, 1
    ))

    return {"waste_pct": round(adj_pct, 2), "wasted_sar": wasted_sar, "saved_meals": saved_meals}


def _water_model(p: ModelParams, strategy: str, week: int) -> Dict:
    """
    Component-based model — each water source reduced separately:
      - Shower: duration × flow × count, reduced by shower_red
      - Irrigation: reduced by irr_red (drip irrigation / native plants)
      - General (cooking, drinking, cleaning): reduced by water_red
      - Laundry: already accounted in p.daily_water_l
    Plus Saudi seasonal oscillation (more water in summer).
    """
    s = STRATEGIES[strategy]

    shower_daily  = p.showers_per_day * p.shower_min * (1.0 - s["shower_red"]) * L_PER_SHOWER_MIN
    general_daily = p.daily_water_l   * (1.0 - s["water_red"])
    irr_daily     = p.irr_l_per_day   * (1.0 - s["irr_red"])

    total_daily   = shower_daily + general_daily + irr_daily
    seasonal      = total_daily * 0.06 * math.sin((week / 52.0) * 2 * math.pi - math.pi / 2)
    noise         = _noise(week, 31, total_daily * 0.03)

    weekly_l      = max(50.0, (total_daily + seasonal + noise) * 7.0)
    cost_sar      = round((weekly_l / LITERS_PER_M3) * SAR_PER_M3, 2)

    return {
        "liters":    round(weekly_l, 0),
        "cost_sar":  cost_sar,
        "shower_L":  round(shower_daily * 7, 0),
        "general_L": round(general_daily * 7, 0),
        "irr_L":     round(irr_daily * 7, 0),
    }

# ══════════════════════════════════════════════════════════════════
#  SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════

def run_simulation(p: ModelParams, strategy: str, weeks: int) -> Dict:
    s = STRATEGIES[strategy]
    weekly_data: List[Dict] = []
    acc_kwh = acc_waste_sar = acc_water = acc_cost = 0.0

    for week in range(1, weeks + 1):
        elec  = _electricity_model(p, strategy, week)
        food  = _food_model(p, strategy, week)
        water = _water_model(p, strategy, week)
        week_cost = elec["cost_sar"] + food["wasted_sar"] + water["cost_sar"]

        acc_kwh      += elec["kwh"]
        acc_waste_sar+= food["wasted_sar"]
        acc_water    += water["liters"]
        acc_cost     += week_cost

        weekly_data.append({
            "week":           week,
            "kwh":            elec["kwh"],
            "elec_cost_sar":  elec["cost_sar"],
            "tou_uplift_pct": elec["tou_pct"],
            "food_waste_pct": food["waste_pct"],
            "food_waste_sar": food["wasted_sar"],
            "saved_meals":    food["saved_meals"],
            "water_liters":   water["liters"],
            "water_cost_sar": water["cost_sar"],
            "total_cost":     round(week_cost, 2),
        })

    # Baseline cost (current-mode, same weeks) for savings % calculation
    base_elec   = (p.monthly_kwh / 4.0) * SAR_PER_KWH
    base_food   = p.weekly_grocery * (p.food_waste_pct / 100.0)
    base_water  = (p.base_weekly_water() / LITERS_PER_M3) * SAR_PER_M3
    base_total  = (base_elec + base_food + base_water) * weeks
    savings_pct = round(max(0.0, (1.0 - acc_cost / base_total) * 100.0), 1) if base_total > 0 else 0.0

    return {
        "strategy":    strategy,
        "label":       s["label"],
        "color":       s["color"],
        "weeks":       weeks,
        "weekly_data": weekly_data,
        "summary": {
            "total_cost_sar":          round(acc_cost, 2),
            "total_kwh":               round(acc_kwh, 1),
            "total_waste_sar":         round(acc_waste_sar, 2),
            "total_water_liters":      round(acc_water, 0),
            "avg_weekly_kwh":          round(acc_kwh / weeks, 1),
            "avg_weekly_waste_sar":    round(acc_waste_sar / weeks, 2),
            "avg_weekly_water_liters": round(acc_water / weeks, 0),
            "avg_weekly_cost":         round(acc_cost / weeks, 2),
            "avg_waste_pct":           round(sum(w["food_waste_pct"] for w in weekly_data) / weeks, 2),
            "savings_pct":             savings_pct,
        }
    }

# ══════════════════════════════════════════════════════════════════
#  INSIGHTS ENGINE
# ══════════════════════════════════════════════════════════════════

def _period_label(weeks: int) -> str:
    if weeks <= 13: return "3 months"
    if weeks <= 26: return "6 months"
    if weeks <= 52: return "1 year"
    return "3 years"

def generate_insights(p: ModelParams, sims: Dict, weeks: int) -> List[Dict]:
    ins = []
    cur = sims["current"]["summary"]
    opt = sims["optimized"]["summary"]
    agg = sims["aggressive"]["summary"]
    period = _period_label(weeks)

    # ── Food waste ────────────────────────────────────────────────
    if p.food_waste_pct > GCC_AVG_WASTE_PCT:
        freq_label = {
            "often":     "often waste food",
            "very_often":"waste a lot of food",
        }.get(p._waste_freq, "sometimes waste food")
        ins.append({
            "sv":"high", "icon":"🍽️", "cat":"Food Waste",
            "title":"More food goes to waste on weekends",
            "detail":(
                f"You {freq_label} — this spikes on weekends when daily routines break down. "
                f"GCC households average {GCC_AVG_WASTE_PCT:.0f}%. Planning weekend meals on Friday "
                f"can cut this significantly."
            ),
            "action":"Plan Friday evening what you will eat over the weekend",
            "impact_sar": round(cur["total_waste_sar"] - opt["total_waste_sar"], 0),
        })

    # ── Fridge freshness ──────────────────────────────────────────
    if p.fridge_temp_c > FRIDGE_OPTIMAL_C + 1:
        extra = (p.fridge_temp_c - FRIDGE_OPTIMAL_C) * FRIDGE_SPOIL_RATE * 100
        ins.append({
            "sv":"medium", "icon":"🌡️", "cat":"Food Storage",
            "title":"Food spoiling faster than it should",
            "detail":(
                f"Your fridge appears warmer than optimal — the clearest sign is food spoiling early. "
                f"Every extra degree above 3.5°C speeds bacterial growth by ~{FRIDGE_SPOIL_RATE*100:.0f}% "
                f"and adds SAR {p.weekly_grocery * (extra/100):.0f}/week in avoidable waste."
            ),
            "action":"Lower the fridge dial — aim to keep food cold, not just cool",
            "impact_sar": round(p.weekly_grocery * (extra/100) * weeks, 0),
        })

    # ── Peak electricity ──────────────────────────────────────────
    if p.peak_hour >= 19:
        time_label = {"evening":"in the evening","late_night":"late at night"}.get(p._peak_time, "at night")
        ins.append({
            "sv":"high", "icon":"⚡", "cat":"Peak Electricity",
            "title":f"You use most electricity {time_label}",
            "detail":(
                f"Running laundry and other heavy appliances {time_label} attracts higher demand charges. "
                f"Shifting them to after midnight can cut your electricity cost by up to 22% "
                f"— with zero lifestyle change."
            ),
            "action":"Schedule laundry and the dishwasher to run after midnight",
            "impact_sar": round(cur["avg_weekly_kwh"] * SAR_PER_KWH * 0.15 * weeks, 0),
        })

    # ── AC usage ──────────────────────────────────────────────────
    if p.ac_hours > 7:
        ins.append({
            "sv":"medium", "icon":"❄️", "cat":"Air Conditioning",
            "title":f"AC running {p.ac_hours:.0f} hrs/day — your largest cost",
            "detail":(
                f"Air conditioning accounts for ~{AC_BILL_SHARE*100:.0f}% of a Saudi household's "
                f"electricity bill. Running it {p.ac_hours:.0f} hrs/day is in the high-usage range. "
                f"Setting it to 24°C instead of 20°C and using a timer saves thousands per year."
            ),
            "action":"Set AC to 24°C and use a timer to auto-off at midnight",
            "impact_sar": round(
                cur["avg_weekly_kwh"] * AC_BILL_SHARE * 0.28 * SAR_PER_KWH * weeks, 0
            ),
        })

    # ── Laundry ───────────────────────────────────────────────────
    if p._laundry_per_week and p._laundry_per_week > 4:
        ins.append({
            "sv":"medium", "icon":"🫧", "cat":"Laundry Usage",
            "title":f"{p._laundry_per_week} laundry loads a week adds up fast",
            "detail":(
                f"Each wash uses ~{L_PER_LAUNDRY_LOAD:.0f} L of water and {KWH_PER_LAUNDRY} kWh. "
                f"At {p._laundry_per_week} loads/week, waiting for full loads and washing at 30°C "
                f"can save 15–20% on laundry water and energy."
            ),
            "action":"Only run the machine when it is completely full",
            "impact_sar": round(
                p._laundry_per_week * 0.2 * (L_PER_LAUNDRY_LOAD/LITERS_PER_M3 * SAR_PER_M3 + KWH_PER_LAUNDRY * SAR_PER_KWH) * 52, 0
            ),
        })

    # ── Water ─────────────────────────────────────────────────────
    water_saved_wk = cur["avg_weekly_water_liters"] - opt["avg_weekly_water_liters"]
    if water_saved_wk > 80:
        shower_label = {
            "long":"15-min", "very_long":"20+ minute"
        }.get(p._shower_length, "")
        ins.append({
            "sv":"medium", "icon":"💧", "cat":"Water Conservation",
            "title":f"Save {water_saved_wk:.0f} litres every week",
            "detail":(
                f"Your household uses ~{cur['avg_weekly_water_liters']:.0f} L/week. "
                f"{'Long showers are the biggest single driver. ' if shower_label else ''}"
                f"Cutting shower time by just 5 minutes per person per day is the highest-impact "
                f"water change you can make — especially in Saudi Arabia's water-scarce climate."
            ),
            "action":"Set a 7-minute shower timer for everyone in the household",
            "impact_sar": round(water_saved_wk / LITERS_PER_M3 * SAR_PER_M3 * weeks, 0),
        })

    # ── Savings opportunity — always last ─────────────────────────
    sar_saved_opt = round(cur["total_cost_sar"] - opt["total_cost_sar"], 0)
    sar_saved_agg = round(cur["total_cost_sar"] - agg["total_cost_sar"], 0)
    ins.append({
        "sv":"opportunity", "icon":"💰", "cat":"Savings Opportunity",
        "title":f"Save SAR {sar_saved_opt:,.0f} over {period}",
        "detail":(
            f"Optimized mode saves {opt['savings_pct']}% (SAR {sar_saved_opt:,.0f}) with no hardware "
            f"purchases or major lifestyle shifts. Aggressive mode can reach SAR {sar_saved_agg:,.0f}."
        ),
        "action":"Switch to Optimized strategy and see your new future",
        "impact_sar": sar_saved_opt,
    })

    # Sort by financial impact, cap at 5
    ins.sort(key=lambda x: abs(x.get("impact_sar", 0)), reverse=True)
    return ins[:5]

# ══════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.get("/", include_in_schema=False)
async def root():
    idx = os.path.join(_frontend, "index.html")
    if os.path.exists(idx):
        return FileResponse(idx)
    return {"service": "Baseerah AI Copilot v3", "docs": "/docs"}


@app.get("/api/profile/demo", tags=["Profile"])
async def demo_profile():
    """Ahmed Al-Rashid — preloaded demo profile (friendly fields)."""
    return {
        "name":                "Ahmed",
        "household_size":      3,
        "weekly_grocery_spend":280.0,
        "waste_frequency":     "sometimes",
        "meal_planning":       "sometimes",
        "fridge_freshness":    "sometimes",
        "ac_hours_per_day":    8.0,
        "appliance_usage":     "moderate",
        "peak_time":           "late_night",
        "shower_length":       "normal",
        "showers_per_day":     4,
        "laundry_per_week":    3,
        "garden_watering":     "rarely",
        # derived values shown for transparency
        "_derived": {
            "monthly_kwh_estimate": "~420 kWh",
            "food_waste_pct":       f"{WASTE_FREQ_TO_PCT['sometimes']}%",
            "fridge_temp":          f"{FRIDGE_FRESH_TO_C['sometimes']}°C",
            "shower_min":           f"{SHOWER_LENGTH_TO_MIN['normal']} min",
        }
    }


@app.post("/api/predict", tags=["Simulation"])
async def predict(inp: UserInput):
    """One-week point prediction for current behaviour. Useful for a quick snapshot."""
    p = ModelParams(inp)
    elec  = _electricity_model(p, "current", 1)
    food  = _food_model(p, "current", 1)
    water = _water_model(p, "current", 1)
    return {
        "next_week": {
            "kwh":           elec["kwh"],
            "elec_cost_sar": elec["cost_sar"],
            "food_waste_pct":food["waste_pct"],
            "food_waste_sar":food["wasted_sar"],
            "water_liters":  water["liters"],
            "water_cost_sar":water["cost_sar"],
            "total_cost_sar":round(elec["cost_sar"]+food["wasted_sar"]+water["cost_sar"],2),
        },
        "derived_params": {
            "monthly_kwh":    round(p.monthly_kwh, 1),
            "food_waste_pct": p.food_waste_pct,
            "fridge_temp_c":  p.fridge_temp_c,
            "peak_hour":      p.peak_hour,
            "shower_min":     p.shower_min,
        },
        "flags": {
            "peak_risk":         p.peak_hour >= 19,
            "fridge_too_warm":   p.fridge_temp_c > FRIDGE_OPTIMAL_C + 1,
            "high_food_waste":   p.food_waste_pct > GCC_AVG_WASTE_PCT,
            "high_kwh":          p.monthly_kwh > GCC_AVG_KWH_MONTH * 1.2,
            "long_shower":       p.shower_min > 10,
            "heavy_irrigation":  p.irr_l_per_day > 80,
            "heavy_laundry":     inp.laundry_per_week > 4,
        }
    }


@app.post("/api/simulate/all", tags=["Simulation"])
async def simulate_all(
    inp: UserInput,
    weeks: int = Query(13, ge=1, le=200, description="13=3M  26=6M  52=1Y  156=3Y"),
):
    """
    Primary endpoint — runs all 3 strategies and returns full comparison.
    Accepts user-friendly fields; translates internally before simulation.
    """
    p    = ModelParams(inp)
    sims = {s: run_simulation(p, s, weeks) for s in STRATEGIES}
    ins  = generate_insights(p, sims, weeks)

    weekly_delta = [
        {
            "week":      w + 1,
            "kwh_saved": round(
                sims["current"]["weekly_data"][w]["kwh"]
                - sims["optimized"]["weekly_data"][w]["kwh"], 1),
            "water_saved":round(
                sims["current"]["weekly_data"][w]["water_liters"]
                - sims["optimized"]["weekly_data"][w]["water_liters"], 0),
            "cost_saved": round(
                sims["current"]["weekly_data"][w]["total_cost"]
                - sims["optimized"]["weekly_data"][w]["total_cost"], 2),
        }
        for w in range(weeks)
    ]

    return {
        "user":   inp.name,
        "weeks":  weeks,
        "period": _period_label(weeks),
        "derived_params": {
            "monthly_kwh":   round(p.monthly_kwh, 1),
            "food_waste_pct":p.food_waste_pct,
            "fridge_temp_c": p.fridge_temp_c,
            "peak_hour":     p.peak_hour,
            "shower_min":    p.shower_min,
        },
        "simulations":     sims,
        "insights":        ins,
        "weekly_delta":    weekly_delta,
        "comparison_summary": {
            s: {
                "label":       sims[s]["label"],
                "color":       sims[s]["color"],
                "savings_pct": sims[s]["summary"]["savings_pct"],
                "total_cost":  sims[s]["summary"]["total_cost_sar"],
                "total_water": sims[s]["summary"]["total_water_liters"],
                "avg_waste":   sims[s]["summary"]["avg_waste_pct"],
            }
            for s in STRATEGIES
        },
    }


@app.post("/api/simulate", tags=["Simulation"])
async def simulate_single(inp: UserInput, strategy: str = "current", weeks: int = 13):
    p = ModelParams(inp)
    return run_simulation(p, strategy, weeks)


@app.post("/api/optimize", tags=["Analysis"])
async def optimize(inp: UserInput, weeks: int = Query(13, ge=1, le=200)):
    """Detailed optimisation breakdown with per-resource recommendations."""
    p    = ModelParams(inp)
    sims = {s: run_simulation(p, s, weeks) for s in STRATEGIES}
    cur  = sims["current"]["summary"]
    opt  = sims["optimized"]["summary"]
    agg  = sims["aggressive"]["summary"]
    return {
        "period":  _period_label(weeks),
        "recommendations": [
            {
                "resource":              "Electricity",
                "user_inputs":           f"{inp.ac_hours_per_day} hrs AC/day, {inp.appliance_usage} appliance use, {inp.peak_time} peak",
                "derived_monthly_kwh":   round(p.monthly_kwh, 1),
                "optimized_avg_wk_kwh":  opt["avg_weekly_kwh"],
                "reduction_pct":         round((1 - opt["avg_weekly_kwh"]/cur["avg_weekly_kwh"])*100, 1),
                "sar_saved_period":      round(cur["total_cost_sar"] * STRATEGIES["optimized"]["elec_red"], 0),
                "quick_wins": [
                    "Set AC thermostat to 24°C (not 20°C)",
                    "Use a timer to auto-off AC at midnight",
                    "Run laundry after midnight to avoid peak charges",
                    "Replace remaining bulbs with LED",
                ],
            },
            {
                "resource":              "Food Waste",
                "user_inputs":           f"Waste: {inp.waste_frequency}, Meal plan: {inp.meal_planning}, Fridge: {inp.fridge_freshness}",
                "derived_waste_pct":     p.food_waste_pct,
                "optimized_avg_waste":   opt["avg_waste_pct"],
                "reduction_pct":         round((1 - opt["avg_waste_pct"]/cur["avg_waste_pct"])*100, 1),
                "sar_saved_period":      round(cur["total_waste_sar"] - opt["total_waste_sar"], 0),
                "quick_wins": [
                    "Plan meals every Friday for the coming week",
                    "Lower fridge temperature (food should feel cold, not just cool)",
                    "First In First Out — older items at the front of the fridge",
                    "Write a shopping list and stick to it",
                ],
            },
            {
                "resource":              "Water",
                "user_inputs":           f"{inp.shower_length} showers, {inp.showers_per_day}/day, {inp.laundry_per_week} laundry/wk, garden: {inp.garden_watering}",
                "derived_weekly_liters": round(p.base_weekly_water(), 0),
                "optimized_avg_liters":  opt["avg_weekly_water_liters"],
                "reduction_pct":         round((1 - opt["avg_weekly_water_liters"]/cur["avg_weekly_water_liters"])*100, 1),
                "sar_saved_period":      round((cur["total_water_liters"]-opt["total_water_liters"])/LITERS_PER_M3*SAR_PER_M3, 0),
                "quick_wins": [
                    "Set a 7-minute shower timer",
                    "Only run laundry when the machine is completely full",
                    "Switch to drip irrigation for the garden",
                    "Fix any dripping taps",
                ],
            },
        ],
        "total_sar_saved_optimized":  round(cur["total_cost_sar"] - opt["total_cost_sar"], 0),
        "total_sar_saved_aggressive": round(cur["total_cost_sar"] - agg["total_cost_sar"], 0),
    }


@app.post("/api/insights", tags=["Analysis"])
async def insights_only(inp: UserInput, weeks: int = Query(13, ge=1, le=200)):
    p    = ModelParams(inp)
    sims = {s: run_simulation(p, s, weeks) for s in STRATEGIES}
    return {"insights": generate_insights(p, sims, weeks)}


@app.get("/api/health", tags=["System"])
async def health():
    return {"status":"ok","version":"3.0.0","input_mode":"friendly","models":["electricity_linear_regression","food_multifactor_rules","water_component_based"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
