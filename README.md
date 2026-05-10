🔭 Baseerah — بصيرة
AI Simulation Copilot for Future Resource Optimization
"We don't predict the future — we help you choose it."

PSU AI Hackathon 2.0 · May 2026 Author: Faisal Alghamdi | College of Computer & Information Sciences | Prince Sultan University

What Is Baseerah?
Baseerah (بصيرة — meaning "insight" in Arabic) is an AI-powered simulation copilot that makes the future cost of daily habits visible before it happens.

Users answer plain everyday questions — "How long are your showers?", "How often does food go to waste?" — and Baseerah instantly simulates three parallel futures for their food waste, electricity, and water consumption across four time horizons.

No kWh. No litres. No degrees. Just plain questions.

Live Demo
Open frontend/index.html in any browser. Works fully offline — no server, no install, no setup.

For the full experience with API:

cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
# → http://localhost:8000        (dashboard)
# → http://localhost:8000/docs   (Swagger API)
The Three Strategies
📍 Current	✨ Optimized	🔥 Aggressive
Description	Baseline — no changes	Smart habits, no hardware	Maximum savings
Electricity ↓	0%	25%	45%
Food Waste ↓	0%	38%	62%
Water ↓	0%	22%	42%
Over 3 years, Optimized mode saves SAR 10,500 — zero hardware required.

The Four Time Horizons
Switch between 3 Months · 6 Months · 1 Year · 3 Years — all three strategies update instantly.

How It Works
Plain Language Input
        │
        ▼
Translation Layer         ← converts everyday answers to model parameters
        │
        ├── ⚡ Electricity Model    (Linear Regression)
        ├── 🍽️ Food Waste Model     (Multi-Factor Rules)
        └── 💧 Water Model          (Component Decomposition)
        │
        ▼
Simulation Engine         ← 3 strategies × N weeks simultaneously
        │
        ▼
Dashboard + Insights      ← split screen, charts, ranked recommendations
The Translation Layer
Users never see a technical value:

What the user sees	What the model uses
"How often does food go to waste?" → Often	food_waste_pct = 38%
"How long are showers?" → Normal	shower_min = 10 min
"Does food stay fresh?" → Sometimes spoils	fridge_temp_c = 6.0°C
"When do you use most electricity?" → Late night	peak_hour = 22
"How heavy is appliance use?" → Moderate	kWh_multiplier = 1.0
The Three Models
⚡ Electricity — Linear Regression
Monthly kWh is derived — never entered directly — from observable behaviours:

monthly_kWh = (AC_hours × 1.2 kWh/hr  +  1.5 kWh/person/day × household × appliance_mult) × 30
              + laundry_per_week × 4.33 × 0.9 kWh
Then per week:

kWh(week) = (monthly_kWh/4) × (1 − strategy_reduction) + seasonal_overlay + noise
ToU uplift: peak_hour ≥ 19 → +15% cost (demand charges)
Seasonal overlay: ±8% sinusoidal (Saudi summer peaks ~June)
Noise: deterministic sin-based — same inputs always produce identical outputs
🍽️ Food Waste — Multi-Factor Rules
waste% = base_waste
       × (1 − food_reduction)
       × fridge_spoilage_factor      ← +7% per °C above 3.5°C optimal
       × meal_prep_decay             ← exponential: e^(−k × sessions)
       × weekend_spike               ← sinusoidal weekly cycle
       × noise
💧 Water — Component Decomposition
Each source reduced independently per strategy:

weekly_liters = (
    showers/day × shower_min × (1 − shower_red) × 9 L/min
  + daily_general × (1 − water_red)
  + irrigation/day × (1 − irr_red)
) × 7
Results — Ahmed Demo Profile
(Riyadh · 3 people · 3-month projection)

Current	Optimized	Aggressive
Weekly cost	SAR 109	SAR 74	SAR 49
Electricity	176 kWh	132 kWh	97 kWh
Food waste	22%	14%	8%
Water	3,930 L	3,065 L	2,285 L
Campus Mode
One toggle scales ×300 university residential units. Same physics. University scale.

Campus weekly electricity: ~52,800 kWh
Annual savings (optimized): SAR 3.1 million
AI Insights Engine
Detects behavioral patterns across all three models. Ranked by SAR impact:

🍽️ Weekend waste spike — waste jumps to 43% on weekends
⚡ Peak usage at 22:00 — 15% time-of-use surcharge
💧 Long showers — 7-min timer saves SAR 180/year per person
💰 SAR 10,500 opportunity — optimized mode, 3 years, no hardware
Project Structure
baseerah/
├── backend/
│   ├── main.py              ← FastAPI server · 3 physics models · insights engine
│   └── requirements.txt     ← 4 dependencies only
├── frontend/
│   └── index.html           ← Complete dashboard · works fully offline
├── data/
│   └── sample_dataset.json  ← Demo profile · benchmarks · valid field values
├── docs/
│   ├── abstract.txt         ← 500-word submission abstract
│   ├── project_report.md    ← Full technical report
│   ├── demo_script.md       ← 3-minute live demo guide
│   └── judge_factsheet.txt  ← One-page summary for judges
└── README.md
API Reference
Method	Endpoint	Description
GET	/api/profile/demo	Ahmed's preloaded profile
POST	/api/simulate/all?weeks=13	Primary — all 3 strategies + insights
POST	/api/predict	One-week snapshot + risk flags
POST	/api/optimize	Per-resource breakdown + quick-wins
POST	/api/insights	Ranked insights only
GET	/api/health	System status
weeks: 13=3M · 26=6M · 52=1Y · 156=3Y

Example Request
curl -X POST "http://localhost:8000/api/simulate/all?weeks=52" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ahmed",
    "household_size": 3,
    "weekly_grocery_spend": 280,
    "waste_frequency": "sometimes",
    "meal_planning": "sometimes",
    "fridge_freshness": "sometimes",
    "ac_hours_per_day": 8,
    "appliance_usage": "moderate",
    "peak_time": "late_night",
    "shower_length": "normal",
    "showers_per_day": 4,
    "laundry_per_week": 3,
    "garden_watering": "rarely"
  }'
Tech Stack
Layer	Technology
Backend	FastAPI 0.110 + Python 3.10 + Pydantic v2
Frontend	Vanilla JavaScript + Chart.js 4.4
Models	Linear regression · Rule engine · Component model
API Docs	Auto-generated Swagger UI at /docs
Offline	Full JS simulation engine — identical logic to backend
Data Sources
All model constants grounded in published Saudi and international data:

Constant	Value	Source
Electricity tariff	SAR 0.18/kWh	Saudi Electricity Company (SEC)
Water tariff	SAR 4.00/m³	National Water Company (NWC)
AC share of bill	55%	Saudi Energy Efficiency Center (SEEC)
GCC food waste avg	22%	FAO (2019)
Fridge optimal temp	3.5°C	World Health Organization (WHO)
Shower flow rate	9 L/min	Water Research Center, KSA
Laundry water use	65 L/load	Front-loader manufacturer average
Security
Zero PII stored — no database, no login, no cookies, no tracking
Input validation — Pydantic enforces all field bounds server-side
Offline-safe — JS fallback engine runs with no server or network
CORS — currently open for local development
Running Locally
Requires: Python 3.10+ · Any modern browser

# Option A — with backend (full experience)
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Option B — offline only (demo mode)
# Just open frontend/index.html in your browser
# The JS simulation engine runs automatically
Judging Criteria Mapping
Criteria	How Baseerah addresses it
Technical Execution	3 physics models, linear regression, FastAPI, Pydantic, Swagger docs
Innovation	Translation layer, parallel scenario simulation, friendly UX over technical inputs
Feasibility	Works offline, zero hardware, runs on any device, campus scale proven
Business Viability	Freemium app + B2B university contracts + Saudi Vision 2030 alignment
Presentation	5-screen demo flow, split-screen dashboard, live API docs
Ethics	Zero PII, all constants cited, transparent model logic, no black-box AI
License
MIT License — free to use, modify, and distribute.

Baseerah (بصيرة) means "insight" in Arabic. Built in one day at PSU AI Hackathon 2.0, May 2026.
