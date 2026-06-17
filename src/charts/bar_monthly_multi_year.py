"""
src/charts/bar_monthly_multi_year.py

Histogramme mensuel comparatif — barres groupées par mois,
une série de couleur par année.

Inputs requis :
    meter : str       — meter_id à agréger
    unit  : str       — unité affichée
    years : list[int] — années à comparer
"""

import pandas as pd
from src.utils import resample_meter

CHART_META = {
    "type"       : "bar_monthly_multi_year",
    "description": "Histogramme mensuel comparatif multi-années",
    "js_file"    : "bar_monthly_multi_year.js",
    "display"    : {
        "colors": ["#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#e74c3c"]
    },
    "required"   : ["meter", "unit", "years"],
    "optional"   : [],
}

MONTH_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict,
            meters: dict = None) -> dict:
    meter_id = inputs.get("meter")
    unit     = inputs.get("unit", "")
    years    = inputs.get("years", [])

    if not meter_id:
        raise ValueError("bar_monthly_multi_year : input 'meter' manquant.")
    if not years:
        raise ValueError("bar_monthly_multi_year : input 'years' manquant ou vide.")
    if meter_id not in df_daily.columns:
        raise ValueError(f"bar_monthly_multi_year : meter '{meter_id}' absent du DataFrame.")

    meter_def = (meters or {}).get(meter_id, {})
    monthly   = resample_meter(df_daily[meter_id], meter_def)

    years_data = {}
    for year in years:
        year_data = monthly[monthly.index.year == year]
        values = []
        for month in range(1, 13):
            match = year_data[year_data.index.month == month]
            values.append(round(float(match.iloc[0]), 2) if not match.empty else None)
        years_data[str(year)] = values

    return {
        "type": "bar_monthly_multi_year",
        "unit": unit,
        "data": {
            "months": MONTH_LABELS,
            "years" : years_data,
        }
    }