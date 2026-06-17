"""
src/api/main.py

API REST FastAPI — expose les KPIs et la structure du dashboard.

Lancer :
    uvicorn src.api.main:app --reload
"""

import logging
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.engine.loader import Loader
from src.engine.kpi import KPIEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Energy Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

STATIC_DIR = Path("src/dashboard")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ------------------------------------------------------------------
# Chargement au démarrage
# ------------------------------------------------------------------

PROJECT = "maison_yverdon"
START   = date(2020, 1, 1)
END     = date.today()

logger.info(f"Chargement des données : {START} → {END}")
loader   = Loader(project=PROJECT)
df_daily = loader.load(start=START, end=END)
logger.info("Données chargées.")

engine = KPIEngine(
    kpis_path      = "reference/kpis.yml",
    dashboard_path = f"projects/{PROJECT}/config/dashboard.yml",
    building_path  = f"projects/{PROJECT}/config/building.yml",
    meters_path    = f"projects/{PROJECT}/config/meters.yml"
)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/")
def serve_dashboard():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Dashboard introuvable dans src/dashboard/"}

@app.get("/api/charts")
def get_charts():
    """Retourne la liste des types de graphiques disponibles."""
    from src.charts import CHART_META
    return list(CHART_META.values())

@app.get("/api/health")
def health():
    return {
        "status" : "ok",
        "project": PROJECT,
        "days"   : len(df_daily),
        "meters" : list(df_daily.columns),
    }

@app.get("/api/dashboard")
def get_dashboard():
    """
    Retourne la structure complète du dashboard avec les données KPI.
    Format :
    {
      title: str,
      navigation: [
        {
          id, title,
          sections: [
            {
              id, title,
              kpis: [ {id, title, unit, data, display} ]
            }
          ]
        }
      ]
    }
    """
    try:
        # Calcule tous les KPIs de la navigation
        kpi_results = engine.compute_navigation(df_daily)
        return kpi_results
    except Exception as e:
        logger.error(f"Erreur dashboard : {e}")
        raise HTTPException(status_code=500, detail=str(e))