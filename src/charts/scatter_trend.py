"""
src/charts/scatter_trend.py

Scatter plot avec courbe de tendance linéaire.
Typiquement utilisé pour la signature énergétique (chaleur = f(T_ext)).

Inputs requis :
    x_meter : str       — meter pour l'axe X
    y_meter : str       — meter pour l'axe Y
    x_label : str       — label axe X
    y_label : str       — label axe Y
    unit_x  : str       — unité axe X
    unit_y  : str       — unité axe Y
    years   : list[int] — années à afficher

Inputs optionnels :
    resolution : str    — daily (défaut) | monthly
    trendline  : bool   — afficher la régression linéaire (défaut: true)
"""

import pandas as pd
import numpy as np
from src.utils import resample_meter

CHART_META = {
    "type"       : "scatter_trend",
    "description": "Scatter plot avec courbe de tendance — signature énergétique",
    "js_file"    : "scatter_trend.js",
    "display"    : {
        "colors": ["#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#e74c3c"]
    },
    "required"   : ["x_meter", "y_meter", "x_label", "y_label",
                    "unit_x", "unit_y", "years"],
    "optional"   : ["resolution", "trendline", "x_min", "x_max", "y_min", "y_max"],
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict,
            meters: dict = None) -> dict:

    x_meter    = inputs.get("x_meter")
    y_meter    = inputs.get("y_meter")
    x_label    = inputs.get("x_label", x_meter)
    y_label    = inputs.get("y_label", y_meter)
    unit_x     = inputs.get("unit_x", "")
    unit_y     = inputs.get("unit_y", "")
    years      = inputs.get("years", [])
    resolution = inputs.get("resolution", "daily")
    trendline  = inputs.get("trendline", True)
    x_min      = inputs.get("x_min", None)
    x_max      = inputs.get("x_max", None)
    y_min      = inputs.get("y_min", None)
    y_max      = inputs.get("y_max", None)

    for mid in [x_meter, y_meter]:
        if mid not in df_daily.columns:
            raise ValueError(f"scatter_trend : meter '{mid}' absent du DataFrame.")

    # Agrégation selon résolution
    freq = "MS" if resolution == "monthly" else "D"
    x_meter_def = (meters or {}).get(x_meter, {})
    y_meter_def = (meters or {}).get(y_meter, {})

    x_series = resample_meter(df_daily[x_meter], x_meter_def, freq=freq)
    y_series = resample_meter(df_daily[y_meter], y_meter_def, freq=freq)

    # Combine en DataFrame et filtre les NaN
    combined = pd.DataFrame({"x": x_series, "y": y_series}).dropna()

    # Filtre sur les plages définies
    if x_min is not None:
        combined = combined[combined["x"] >= float(x_min)]
    if x_max is not None:
        combined = combined[combined["x"] <= float(x_max)]
    if y_min is not None:
        combined = combined[combined["y"] >= float(y_min)]
    if y_max is not None:
        combined = combined[combined["y"] <= float(y_max)]

    # Points par année
    points_by_year = {}
    for year in years:
        mask       = combined.index.year == year
        year_data  = combined[mask]
        if not year_data.empty:
            points_by_year[str(year)] = [
                {"x": round(float(x), 2), "y": round(float(y), 2)}
                for x, y in zip(year_data["x"], year_data["y"])
            ]

    # Régression linéaire sur tous les points des années sélectionnées
    trendline_data = None
    equation       = None

    if trendline and points_by_year:
        all_x = []
        all_y = []
        for pts in points_by_year.values():
            all_x.extend([p["x"] for p in pts])
            all_y.extend([p["y"] for p in pts])

        all_x = np.array(all_x)
        all_y = np.array(all_y)

        if len(all_x) >= 2:
            # Régression linéaire y = ax + b
            coeffs  = np.polyfit(all_x, all_y, 1)
            a, b    = coeffs[0], coeffs[1]

            # R²
            y_pred  = np.polyval(coeffs, all_x)
            ss_res  = np.sum((all_y - y_pred) ** 2)
            ss_tot  = np.sum((all_y - np.mean(all_y)) ** 2)
            r2      = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Points de la droite de tendance (min → max x)
            x_min, x_max = float(all_x.min()), float(all_x.max())
            trendline_data = [
                {"x": round(x_min, 2), "y": round(float(np.polyval(coeffs, x_min)), 2)},
                {"x": round(x_max, 2), "y": round(float(np.polyval(coeffs, x_max)), 2)},
            ]

            sign_b = "+" if b >= 0 else "-"
            equation = {
                "a"    : round(float(a), 2),
                "b"    : round(abs(float(b)), 2),
                "sign_b": sign_b,
                "r2"   : round(float(r2), 3),
                "text" : f"y = {round(float(a), 2)}x {sign_b} {round(abs(float(b)), 2)}  (R² = {round(float(r2), 3)})"
            }

    return {
        "type"      : "scatter_trend",
        "unit_x"    : unit_x,
        "unit_y"    : unit_y,
        "x_label"   : x_label,
        "y_label"   : y_label,
        "resolution": resolution,
        "data"      : {
            "points"   : points_by_year,
            "trendline": trendline_data,
            "equation" : equation,
        }
    }