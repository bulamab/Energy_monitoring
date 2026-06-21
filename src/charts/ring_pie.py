"""
src/charts/ring_pie.py

Camembert en anneau (donut) — répartition d'un total entre plusieurs
compteurs, avec sélection d'année.

Inputs requis :
    meters : list — [{meter, label}]
    unit   : str
    years  : list — années sélectionnables
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

CHART_META = {
    "type"       : "ring_pie",
    "description": "Camembert en anneau — répartition entre plusieurs compteurs",
    "js_file"    : "ring_pie.js",
    "display"    : {
        "colors": ["#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#e74c3c", "#1abc9c"]
    },
    "required"   : ["meters", "unit", "years"],
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict, **kwargs) -> dict:
    meters_cfg = inputs.get("meters", [])
    unit       = inputs.get("unit", "")
    years      = inputs.get("years")

    if not meters_cfg:
        raise ValueError("ring_pie : input 'meters' manquant ou vide.")
    if not years:
        raise ValueError("ring_pie : 'years' manquant ou vide.")

    for cfg in meters_cfg:
        mid = cfg.get("meter")
        if not mid:
            raise ValueError("ring_pie : 'meter' manquant dans un élément.")
        if mid not in df_daily.columns:
            raise ValueError(f"ring_pie : meter '{mid}' absent du DataFrame.")

    labels = {cfg["meter"]: cfg.get("label", cfg["meter"]) for cfg in meters_cfg}

    values_by_year = {}
    for year in years:
        df_year = df_daily[df_daily.index.year == int(year)]
        if df_year.empty:
            logger.warning(f"ring_pie : aucune donnée pour l'année {year}.")
            values_by_year[str(year)] = []
            continue

        slices = []
        for cfg in meters_cfg:
            mid   = cfg["meter"]
            total = float(df_year[mid].sum())
            slices.append({"name": labels[mid], "value": round(total, 1)})
        values_by_year[str(year)] = slices

    return {
        "type"           : "ring_pie",
        "unit"           : unit,
        "years_available": years,
        "data"           : {
            "labels": labels,
            "values": values_by_year,
        },
    }