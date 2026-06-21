"""
src/engine/kpi.py

KPIEngine — orchestre le calcul des KPIs définis dans dashboard.yml.

Le calcul effectif est délégué aux modules dans src/charts/.
Ajouter un type de graphique = ajouter un fichier dans src/charts/
et une entrée dans CHART_HANDLERS.

Usage direct (test) :
    python -m src.engine.kpi
"""

import logging
import yaml
import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.charts import CHART_HANDLERS, CHART_META

logger = logging.getLogger(__name__)



def _clean_nan(obj):
    """Remplace récursivement NaN et inf par None pour sérialisation JSON."""
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    elif isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    return obj


class KPIEngine:
    """
    Calcule les KPIs définis dans dashboard.yml
    en déléguant à src/charts/.
    """

    def __init__(self,
                 kpis_path:      str,
                 dashboard_path: str,
                 building_path:  str,
                 meters_path:    str = None):

        self.kpis      = self._load_yaml(Path(kpis_path))["kpis"]
        self.dashboard = self._load_yaml(Path(dashboard_path))
        self.building  = self._load_yaml(Path(building_path))
        self.meters    = self._load_yaml(Path(meters_path))["meters"] if meters_path else {}

    # ------------------------------------------------------------------
    # Point d'entrée principal
    # ------------------------------------------------------------------

    def compute_navigation(self, df_daily: pd.DataFrame) -> dict:
        """
        Parcourt la structure navigation de dashboard.yml,
        calcule les KPIs de chaque section et retourne
        la structure complète avec données.
        """
        self._df = df_daily
        navigation = []

        for menu in self.dashboard.get("navigation", []):
            sections = []

            for section in menu.get("sections", []):
                kpis_out = []

                for kpi_instance in section.get("kpis", []):
                    result = self._compute_kpi(kpi_instance)
                    if result:
                        kpis_out.append(result)

                sections.append({
                    "id"    : section["id"],
                    "title" : section["title"],
                    "kpis"  : kpis_out,
                })

            navigation.append({
                "id"      : menu["id"],
                "title"   : menu["title"],
                "sections": sections,
            })

        return {
            "title"     : self.dashboard.get("title", ""),
            "navigation": navigation,
        }

    # ------------------------------------------------------------------
    # Calcul d'un KPI individuel
    # ------------------------------------------------------------------

    def _compute_kpi(self, instance: dict) -> dict | None:
        """
        Calcule un KPI depuis son instance dans dashboard.yml.
        """
        kpi_id  = instance.get("id")
        kpi_ref = instance.get("kpi_ref")

        if kpi_ref not in self.kpis:
            logger.error(f"KPI '{kpi_id}' : kpi_ref '{kpi_ref}' introuvable dans kpis.yml.")
            return None

        kpi_def     = self.kpis[kpi_ref]
        display_ref = kpi_def.get("display_ref")
        inputs      = instance.get("inputs", {})

        # Récupère le meta depuis le registre
        chart_type = display_ref
        handler    = CHART_HANDLERS.get(chart_type)
        meta       = CHART_META.get(chart_type, {})

        if handler is None:
            logger.error(
                f"KPI '{kpi_id}' : type '{chart_type}' non supporté. "
                f"Disponibles : {list(CHART_HANDLERS.keys())}"
            )
            return None

        try:
            import math
            chart_data = handler(self._df, inputs, meta, meters=self.meters,  building = self.building)
            # Nettoie les NaN → None (JSON compliant)
            chart_data = _clean_nan(chart_data)
            return {
                "id"     : kpi_id,
                "title"  : instance.get("title", kpi_def.get("description", kpi_id)),
                "display": {"type": meta.get("type", display_ref)},
                **chart_data,
            }
        except Exception as e:
            logger.error(f"KPI '{kpi_id}' : erreur — {e}")
            return None

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


# ----------------------------------------------------------------------
# Test intégré
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from src.engine.loader import Loader

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(levelname)s — %(message)s"
    )

    PROJECT = "maison_yverdon"
    START   = date(2020, 1, 1)
    END     = date(2025, 12, 31)

    print("\n" + "="*60)
    print("  TEST KPIEngine")
    print(f"  Projet  : {PROJECT}")
    print(f"  Période : {START} → {END}")
    print("="*60 + "\n")

    try:
        loader   = Loader(project=PROJECT)
        df_daily = loader.load(start=START, end=END)
    except Exception as e:
        print(f"ERREUR chargement : {e}")
        sys.exit(1)

    engine = KPIEngine(
        kpis_path      = "reference/kpis.yml",
        dashboard_path = f"projects/{PROJECT}/config/dashboard.yml",
        building_path  = f"projects/{PROJECT}/config/building.yml",
        meters_path    = f"projects/{PROJECT}/config/meters.yml"
    )

    result = engine.compute_navigation(df_daily)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print("\n✓ Test KPIEngine terminé sans erreur.")