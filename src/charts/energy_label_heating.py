"""
src/charts/energy_label_heating.py

Étiquette énergie enveloppe bâtiment (SIA 2031).
Retourne les données pour toutes les années disponibles.
"""

import logging

logger = logging.getLogger(__name__)

CHART_META = {
    "type"       : "energy_label_heating",
    "js_file"    : "energy_label_heating.js",
    "description": "Étiquette énergie enveloppe bâtiment",
    "aggregation": "yearly",
    "unit"       : "%",
}


def compute(df_daily, inputs: dict, meta: dict, **kwargs) -> dict:
    building = kwargs.get("building", {})

    heat_meter   = inputs.get("heat_meter",   "heat_demand_measured")
    dj_meter     = inputs.get("dj_meter",     "dj_20_12")
    dj_ref_meter = inputs.get("dj_ref_meter", "dj_reference_daily")
    year_input   = inputs.get("year")

    for m in [heat_meter, dj_meter, dj_ref_meter]:
        if m not in df_daily.columns:
            raise ValueError(f"energy_label : meter '{m}' absent du DataFrame.")

    sre = float(building.get("params", {}).get("sre", 0))
    if sre <= 0:
        raise ValueError("energy_label : SRE invalide dans building.yml.")

    qh_li_ref = float(building.get("heating", {}).get("qh_li", 0))
    if qh_li_ref <= 0:
        raise ValueError("energy_label : 'heating.qh_li' absent dans building.yml.")

    years_available = inputs.get("years", [])
    if not years_available:
        raise ValueError("energy_label : input 'years' manquant dans dashboard.yml.")

    # Calcule les données pour chaque année
    years_data = {}
    for year in years_available:
        df_year = df_daily[df_daily.index.year == year]
        if df_year.empty:
            continue

        e_annuelle   = float(df_year[heat_meter].sum())
        dj_reels     = float(df_year[dj_meter].sum())
        dj_reference = float(building.get("heating", {}).get("dj_reference", 0))
        if dj_reference <= 0:
            raise ValueError("energy_label : 'heating.dj_reference' absent dans building.yml.")

        if dj_reels <= 0 or e_annuelle <= 0:
            continue

        qh_effectif = round(e_annuelle / sre, 1)
        qh_li_norm  = round(e_annuelle / sre * (dj_reference / dj_reels), 1)
        ratio_pct   = round(qh_li_norm / qh_li_ref * 100, 1)

        logger.info(
            f"energy_label {year} : "
            f"e_annuelle={e_annuelle:.1f} kWh, "
            f"dj_reels={dj_reels:.0f} Kd, "
            f"dj_reference={dj_reference:.0f} Kd, "
            f"qh_eff={qh_effectif} kWh/m²·an, "
            f"qh_li_norm={qh_li_norm} kWh/m²·an, "
            f"ratio={ratio_pct}%"
)

        years_data[str(year)] = {
            "qh_effectif" : qh_effectif,
            "qh_li_norm"  : qh_li_norm,
            "ratio_pct"   : ratio_pct,
            "dj_reels"    : round(dj_reels, 0),
            "dj_reference": round(dj_reference, 0),
        }

    if not years_data:
        raise ValueError("energy_label : aucune donnée valide trouvée.")

    # Année par défaut — celle demandée ou la dernière disponible
    default_year = str(year_input) if year_input and str(year_input) in years_data \
                   else str(years_available[-1])

    default = years_data[default_year]

    logger.info(
        f"energy_label {default_year} : "
        f"Qh_eff={default['qh_effectif']} kWh/m²·an, "
        f"ratio={default['ratio_pct']}%"
    )

    return {
        "type"           : "energy_label_heating",
        "years_available": [int(y) for y in years_data.keys()],
        "years_data"     : years_data,
        "qh_li_ref"      : qh_li_ref,
        "sre"            : sre,
        # Valeurs de l'année par défaut au niveau racine
        "qh_effectif"    : default["qh_effectif"],
        "qh_li_norm"     : default["qh_li_norm"],
        "ratio_pct"      : default["ratio_pct"],
        "dj_reels"       : default["dj_reels"],
        "dj_reference"   : default["dj_reference"],
        "year"           : int(default_year),
    }