# Baseerah — Live Demo Script
## PSU AI Hackathon 2.0

---

## Setup (do this BEFORE presenting)

1. Open `frontend/index.html` in Chrome — keep it ready on Screen 1
2. Open `http://localhost:8000/docs` in another tab — keep it ready on Screen 2
3. Run backend: `python -m uvicorn main:app --reload --port 8000`
4. Have this script open on your phone

---

## The 3-Minute Demo Flow

### STEP 1 — Hook (20 seconds)
Show the landing screen. Say:

> "Every Saudi household loses thousands of riyals every year to three things:
> food waste, electricity, and water. The problem isn't that people don't care —
> it's that they can't see it. Baseerah changes that."

Click **Start Simulation**.

---

### STEP 2 — Input Screen (30 seconds)
Show the chip selectors. Say:

> "No kWh. No litres. No technical values. Just plain questions.
> Ahmed is our demo user — 3-person household in Riyadh, typical AC usage."

Point to the chips: *"Does food stay fresh?"* → *"Sometimes spoils"*
Point to: *"How long are showers?"* → *"Normal ~10 min"*

Click **Simulate My Future**.

---

### STEP 3 — Dashboard Split Screen (45 seconds)
The simulation runs. Dashboard appears. Say:

> "Baseerah just ran three parallel simulations simultaneously.
> Left side: where Ahmed is heading today. Right side: where he could be."

Point to the metric cards — Current vs Optimized.

> "Food waste drops from 22% to 14%. Weekly cost from SAR 109 to SAR 74.
> Water from 3,930 to 3,065 litres."

Now switch the time horizon to **3Y**. Say:

> "Over three years — that's SAR 10,500 saved. With zero hardware.
> No solar panels. No smart meters. Just changed habits."

Show the chart — three lines clearly diverging.

---

### STEP 4 — Switch Strategy (15 seconds)
Click **Aggressive**. Say:

> "Go full aggressive — SAR 49 per week. That's half of current."

Click back to **Optimized**. Say:

> "We recommend Optimized for most people — realistic, immediate, no sacrifice."

---

### STEP 5 — Insights (30 seconds)
Click **View Insights**. Show the 4 cards. Say:

> "The AI doesn't just simulate — it tells you exactly what to change first,
> ranked by how much money it saves you."

Point to each card:
- *"Weekend waste spike — plan meals on Friday."*
- *"Peak at 22:00 — run laundry after midnight."*
- *"7-minute shower timer — SAR 180 per year per person."*

---

### STEP 6 — Campus Mode (20 seconds)
Go back to Dashboard. Click **Campus Mode**. Say:

> "One toggle. Now we're looking at 300 university residential units.
> Same model — 300 times the scale. SAR 3.1 million saved annually.
> This is how PSU could use Baseerah for facilities management."

---

### STEP 7 — Technical Depth (20 seconds)
Switch to the `/docs` tab. Say:

> "For the technical judges — this is a real FastAPI backend.
> Three physics-based models: linear regression for electricity,
> multi-factor rules for food waste, component decomposition for water.
> Every number on the dashboard is traceable to a specific model parameter."

Click **Try it out** on `/api/simulate/all`. Change `waste_frequency` to `"very_often"`. Hit Execute. Show the response.

---

## One-Liner Closing
> "Baseerah proves that the barrier to sustainability isn't motivation.
> It's visibility. When people see their future in SAR, they act."

---

## Backup — if someone asks to see it work offline
Close the terminal (kill the server). Reload `index.html`. It still works — JS fallback engine runs automatically.
