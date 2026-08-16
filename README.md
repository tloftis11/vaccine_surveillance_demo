# Vaccine Surveillance Platform

Public health intelligence for vaccine coverage, schedule adherence, and safety outcomes.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL (Render managed) |
| Frontend | React 18 + Vite |
| Pipelines | Python scripts (Render Cron Jobs) |
| Deployment | Render (render.yaml blueprint) |

## Modules

- **Coverage Explorer** — NIS-based vaccination coverage rates by state, vaccine, and demographic
- **Adverse Event Explorer** — VAERS signal detection and event frequency analysis
- **Schedule Adherence** — Multi-dose series completion rates and timing analysis

## Local Development

### Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL (local or Render dev DB)

### Backend

```bash
cd api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in DATABASE_URL
alembic upgrade head
uvicorn main:app --reload
```

API runs at http://localhost:8000. Docs at http://localhost:8000/docs.

### Frontend

```bash
cd ui
npm install
cp .env.example .env      # set VITE_API_URL=http://localhost:8000
npm run dev
```

UI runs at http://localhost:5173.

### Data Pipelines

```bash
cd pipelines
pip install -r requirements.txt
cp .env.example .env      # fill in DATABASE_URL

# Run NIS ingest first (coverage rates, adherence)
python nis_ingest.py

# Run VAERS ingest (large — takes 10–30 min first run)
python vaers_ingest.py
```

## Deployment on Render

1. Push to GitHub
2. In Render dashboard → **New → Blueprint**
3. Connect the repo — Render reads `render.yaml` automatically
4. Set the two manual env vars:
   - `ANTHROPIC_API_KEY` on vaccine-api
   - `CORS_ORIGINS` on vaccine-api (set to your vaccine-ui URL after first deploy)
5. Trigger cron jobs manually on first deploy to load data

## Data Sources

| Source | Data | Update Cadence |
|---|---|---|
| CDC NIS (data.cdc.gov Socrata API) | State/national coverage rates | Annual |
| VAERS (vaers.hhs.gov) | Adverse event reports | Quarterly |
| CDC ChildVaxView | Series completion rates | Annual |

## Environment Variables

### api/.env
```
DATABASE_URL=postgresql://user:pass@host/dbname
ANTHROPIC_API_KEY=sk-ant-...
CORS_ORIGINS=http://localhost:5173,https://vaccine-ui.onrender.com
```

### ui/.env
```
VITE_API_URL=http://localhost:8000
```

### pipelines/.env
```
DATABASE_URL=postgresql://user:pass@host/dbname
VAERS_YEARS=2020,2021,2022,2023,2024
```
