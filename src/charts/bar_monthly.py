"""
src/charts/bar_monthly.py
Histogramme mensuel simple — une barre par mois sur toute la période.
"""

import pandas as pd
from src.utils import resample_meter

CHART_META = {
    "type"       : "bar_monthly",
    "description": "Histogramme mensuel simple",
    "js_file"    : "bar_monthly.js",
    "display"    : { "color": "#3498db" },
    "required"   : ["meter", "unit"],
    "optional"   : [],
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict,
            meters: dict = None) -> dict:
    meter_id = inputs.get("meter")
    unit     = inputs.get("unit", "")

    if not meter_id:
        raise ValueError("bar_monthly : input 'meter' manquant.")
    if meter_id not in df_daily.columns:
        raise ValueError(f"bar_monthly : meter '{meter_id}' absent du DataFrame.")

    meter_def = (meters or {}).get(meter_id, {})
    monthly   = resample_meter(df_daily[meter_id], meter_def)

    return {
        "type" : "bar_monthly",
        "unit" : unit,
        "data" : {str(ts.date()): v for ts, v in monthly.items()},
    }