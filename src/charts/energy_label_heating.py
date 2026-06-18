"""
src/charts/energy_label.py

Étiquette énergie enveloppe bâtiment (SIA 2031).

Calcule :
  - qh_effectif : kWh/m²·an brut
  - qh_li_norm  : kWh/m²·an normalisé par DJ
  - qh_li_ref   : kWh/m²·an référence SIA (depuis building.yml)
  - ratio_pct   : qh_li_norm / qh_li_ref × 100

Inputs dashboard.yml :
  heat_meter   : meter chaleur chauffage (défaut: heat_demand_measured)
  dj_meter     : meter DJ réels          (défaut: dj_20_12)
  dj_ref_meter : meter DJ référence      (défaut: dj_reference_daily)
  year         : année à afficher
"""

import logging

logger = logging.getLogger(__name__)

CHART_META = {
    "type"       : "energy_label_heating",
    "js_file"    : "energy_label_heating.js",
    "display_ref": "energy_label_heating",
    "aggregation": "yearly",
    "unit"       : "%",
    "description": "Étiquette énergie enveloppe bâtiment",
}


def compute(df_daily, inputs: dict, meta: dict, **kwargs) -> dict:
    """
    Paramètres
    ----------
    df_daily : pd.DataFrame — données journalières complètes
    inputs   : dict — inputs depuis dashboard.yml
    meta     : dict — CHART_META du chart
    **kwargs : building (dict) — contenu de building.yml
    """
    building = kwargs.get("building", {})

    heat_meter   = inputs.get("heat_meter",   "heat_demand_measured")
    dj_meter     = inputs.get("dj_meter",     "dj_20_12")
    dj_ref_meter = inputs.get("dj_ref_meter", "dj_reference_daily")
    year         = inputs.get("year")

    # Vérifie que les meters existent
    for m in [heat_meter, dj_meter, dj_ref_meter]:
        if m not in df_daily.columns:
            raise ValueError(f"energy_label_heating : meter '{m}' absent du DataFrame.")

    # Filtre sur l'année demandée
    if year:
        mask    = df_daily.index.year == int(year)
        df_year = df_daily[mask]
    else:
        year    = int(df_daily.index.year[-1])
        df_year = df_daily[df_daily.index.year == year]

    if df_year.empty:
        raise ValueError(f"energy_label : aucune donnée pour l'année {year}.")

    # Paramètres bâtiment
    sre = float(building.get("params", {}).get("sre", 0))
    if sre <= 0:
        raise ValueError("energy_label : SRE invalide ou absente dans building.yml.")

    qh_li_ref = float(building.get("heating", {}).get("qh_li", 0))
    if qh_li_ref <= 0:
        raise ValueError(
            "energy_label : 'heating.qh_li' absent ou invalide dans building.yml."
        )

    # Calculs
    e_annuelle   = float(df_year[heat_meter].sum())
    dj_reels     = float(df_year[dj_meter].sum())
    dj_reference = float(df_year[dj_ref_meter].sum())

    if dj_reels <= 0:
        raise ValueError("energy_label : DJ réels = 0, vérifier dj_20_12.")

    qh_effectif = round(e_annuelle / sre, 1)
    qh_li_norm  = round(e_annuelle / sre * (dj_reference / dj_reels), 1)
    ratio_pct   = round(qh_li_norm / qh_li_ref * 100, 1)

    logger.info(
        f"energy_label {year} : "
        f"Qh_eff={qh_effectif} kWh/m²·an, "
        f"Qh_li={qh_li_norm} kWh/m²·an, "
        f"ratio={ratio_pct}%"
    )

    return {
        "type"        : "energy_label_heating",
        "qh_effectif" : qh_effectif,
        "qh_li_norm"  : qh_li_norm,
        "qh_li_ref"   : qh_li_ref,
        "ratio_pct"   : ratio_pct,
        "dj_reels"    : round(dj_reels, 0),
        "dj_reference": round(dj_reference, 0),
        "sre"         : sre,
        "year"        : int(year),
    }