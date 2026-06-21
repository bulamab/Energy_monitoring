"""
src/charts/calendar_heatmap.py

Heatmap calendaire — une valeur par jour sur une année (style GitHub
contributions), avec sélection d'année. Aucun resampling nécessaire :
les valeurs journalières sont transmises telles quelles.

Inputs requis :
    meter : str  — meter à afficher
    unit  : str
    years : list — années sélectionnables

Inputs optionnels :
    color_scale : list — couleurs hex pour le dégradé, faible → fort
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

CHART_META = {
    "type"       : "calendar_heatmap",
    "description": "Heatmap calendaire — une valeur par jour, intensité de couleur",
    "js_file"    : "calendar_heatmap.js",
    "required"   : ["meter", "unit", "years"],
    "optional"   : ["color_scale"],
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict, **kwargs) -> dict:
    meter_id    = inputs.get("meter")
    unit        = inputs.get("unit", "")
    years       = inputs.get("years")
    color_scale = inputs.get("color_scale")

    if not meter_id:
        raise ValueError("calendar_heatmap : 'meter' manquant.")
    if not years:
        raise ValueError("calendar_heatmap : 'years' manquant ou vide.")
    if meter_id not in df_daily.columns:
        raise ValueError(f"calendar_heatmap : meter '{meter_id}' absent du DataFrame.")

    values_by_year = {}
    all_values = []

    for year in years:
        df_year = df_daily[df_daily.index.year == int(year)]
        if df_year.empty:
            logger.warning(f"calendar_heatmap : aucune donnée pour l'année {year}.")
            values_by_year[str(year)] = []
            continue

        series = df_year[meter_id]
        points = [
            [ts.strftime("%Y-%m-%d"), round(float(v), 2)]
            for ts, v in series.items()
            if pd.notna(v)
        ]
        values_by_year[str(year)] = points
        all_values.extend(v for _, v in points)

    vmin = round(min(all_values), 2) if all_values else 0
    vmax = round(max(all_values), 2) if all_values else 1

    return {
        "type"           : "calendar_heatmap",
        "unit"           : unit,
        "years_available": years,
        "min"            : vmin,
        "max"            : vmax,
        "color_scale"    : color_scale,
        "data"           : {"values": values_by_year},
    }