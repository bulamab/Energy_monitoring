"""
src/charts/bullet.py

Jauge bullet — ratio annuel entre deux compteurs, avec sélection d'année.
Zones qualitatives (rouge/orange/vert) et ligne cible optionnelles.

Inputs requis :
    numerator   : str  — meter au numérateur (ex: pv_self_consumption)
    denominator : str  — meter au dénominateur (ex: pv_production)
    years       : list — années sélectionnables

Inputs optionnels :
    unit   : str   — défaut "%"
    target : float — valeur cible, ligne repère verticale
    min    : float — borne basse axe (défaut 0)
    max    : float — borne haute axe (défaut 100)
    ranges : list  — zones qualitatives [{to, color}], triées croissant
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

CHART_META = {
    "type"       : "bullet",
    "description": "Jauge bullet — ratio annuel entre deux compteurs",
    "js_file"    : "bullet.js",
    "unit"       : "%",
    "required"   : ["numerator", "denominator", "years"],
    "optional"   : ["unit", "target", "min", "max", "ranges"],
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict, **kwargs) -> dict:
    num_id = inputs.get("numerator")
    den_id = inputs.get("denominator")   # optionnel désormais
    years  = inputs.get("years")

    if not num_id:
        raise ValueError("bullet : 'numerator' requis.")
    if not years:
        raise ValueError("bullet : 'years' manquant ou vide.")

    required_meters = [num_id] + ([den_id] if den_id else [])
    for m in required_meters:
        if m not in df_daily.columns:
            raise ValueError(f"bullet : meter '{m}' absent du DataFrame.")

    axis_min = float(inputs.get("min", 0))
    axis_max = float(inputs.get("max", 100))
    target   = inputs.get("target")
    ranges   = inputs.get("ranges")

    if ranges:
        prev = axis_min
        for r in sorted(ranges, key=lambda x: x["to"]):
            if r["to"] <= prev:
                raise ValueError(f"bullet : zones non croissantes ('to'={r['to']} <= {prev}).")
            prev = r["to"]
        if abs(prev - axis_max) > 1e-6:
            logger.warning(f"bullet : dernière zone 'to'={prev} != max={axis_max}.")

    values = {}
    for year in years:
        df_year = df_daily[df_daily.index.year == int(year)]
        if df_year.empty:
            logger.warning(f"bullet : aucune donnée pour l'année {year}.")
            values[str(year)] = None
            continue

        num = float(df_year[num_id].sum())

        if den_id:
            den = float(df_year[den_id].sum())
            values[str(year)] = round(num / den * 100, 1) if den > 0 else None
        else:
            values[str(year)] = round(num, 1)

    default_unit = "%" if den_id else ""
    return {
        "type"           : "bullet",
        "unit"           : inputs.get("unit", default_unit),
        "years_available": years,
        "min"            : axis_min,
        "max"            : axis_max,
        "target"         : target,
        "ranges"         : ranges,
        "data"           : {"values": values},
    }