"""
src/charts/bar_stacked.py

Histogramme empilé — plusieurs meters, résolution paramétrable.

Inputs requis :
    meters     : list — [{meter, label, sign?}]
    unit       : str

Inputs optionnels :
    resolution : str  — monthly (défaut) | yearly | weekly
    line:
      type  : cumulative_sum | meter | reference
      label : str
      color : str
      unit  : str
      axis  : primary | secondary
      meter : str   (si type=meter)
      value : float (si type=reference)
"""

import pandas as pd
from src.utils import resample_meter

CHART_META = {
    "type"       : "bar_stacked",
    "description": "Histogramme empilé — résolution paramétrable",
    "js_file"    : "bar_stacked.js",
    "display"    : {
        "colors": ["#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#e74c3c", "#1abc9c"]
    },
    "required"   : ["meters", "unit"],
    "optional"   : ["resolution", "line"],
}

MONTH_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

FREQ_MAP = {
    "monthly": "MS",
    "yearly" : "YS",
    "weekly" : "W-MON",
}


def compute(df_daily: pd.DataFrame, inputs: dict, meta: dict,
            meters: dict = None) -> dict:

    meters_cfg = inputs.get("meters", [])
    unit       = inputs.get("unit", "")
    line_cfg   = inputs.get("line")
    resolution = inputs.get("resolution", "monthly")

    if not meters_cfg:
        raise ValueError("bar_stacked : input 'meters' manquant ou vide.")

    freq = FREQ_MAP.get(resolution, "MS")

    for cfg in meters_cfg:
        mid = cfg.get("meter")
        if not mid:
            raise ValueError("bar_stacked : 'meter' manquant dans un élément.")
        if mid not in df_daily.columns:
            raise ValueError(f"bar_stacked : meter '{mid}' absent du DataFrame.")

    # Agrège chaque meter selon sa règle + résolution demandée
    monthly_dict = {}
    for cfg in meters_cfg:
        mid       = cfg["meter"]
        meter_def = (meters or {}).get(mid, {})
        monthly_dict[mid] = resample_meter(df_daily[mid], meter_def, freq=freq)

    ref_index = list(monthly_dict.values())[0].index

    # --- Labels de l'axe X selon résolution ---
    if resolution == "yearly":
        x_labels        = [str(ts.year) for ts in ref_index]
        years_available = None
        groups          = {None: ref_index}

    elif resolution == "weekly":
        years_available = sorted(ref_index.year.unique().tolist())
        x_labels        = [f"S{ts.isocalendar()[1]}" for ts in
                           ref_index[ref_index.year == years_available[-1]]]
        groups          = {str(y): ref_index[ref_index.year == y]
                           for y in years_available}

    else:  # monthly
        years_available = sorted(ref_index.year.unique().tolist())
        x_labels        = MONTH_LABELS
        groups          = {str(y): ref_index[ref_index.year == y]
                           for y in years_available}

    # --- Construit les séries ---
    if resolution == "yearly":
        series = {"all": {}}
        for cfg in meters_cfg:
            mid  = cfg["meter"]
            sign = -1 if cfg.get("sign") == "negative" else 1
            series["all"][mid] = [
                round(float(v) * sign, 2) if pd.notna(v) else None
                for v in monthly_dict[mid].values
            ]
    else:
        series = {}
        for year_key, idx in groups.items():
            series[year_key] = {}
            for cfg in meters_cfg:
                mid       = cfg["meter"]
                sign      = -1 if cfg.get("sign") == "negative" else 1
                m         = monthly_dict[mid]
                year_data = m[m.index.isin(idx)]
                n_slots   = len(x_labels)
                values    = [None] * n_slots
                for i, ts in enumerate(idx):
                    if i < n_slots and ts in year_data.index:
                        v = year_data[ts]
                        values[i] = round(float(v) * sign, 2) if pd.notna(v) else None
                series[year_key][mid] = values

    # --- Ligne optionnelle ---
    line_data = None
    if line_cfg:
        line_type  = line_cfg.get("type", "cumulative_sum")
        line_data  = {}
        group_keys = ["all"] if resolution == "yearly" else list(groups.keys())

        for year_key in group_keys:
            year_series = series[year_key]

            if line_type == "cumulative_sum":
                cumul = []
                total = 0.0
                for i in range(len(x_labels)):
                    s = sum((year_series[mid][i] or 0) for mid in year_series)
                    total += s
                    cumul.append(round(total, 2))
                line_data[year_key] = cumul

            elif line_type == "meter":
                meter_id = line_cfg.get("meter")
                if not meter_id or meter_id not in df_daily.columns:
                    raise ValueError(f"bar_stacked line : meter '{meter_id}' introuvable.")
                meter_def = (meters or {}).get(meter_id, {})
                m_agg     = resample_meter(df_daily[meter_id], meter_def, freq=freq)

                if resolution == "yearly":
                    line_data[year_key] = [
                        round(float(v), 2) if pd.notna(v) else None
                        for v in m_agg.values
                    ]
                else:
                    idx_year  = groups[year_key]
                    year_data = m_agg[m_agg.index.isin(idx_year)]
                    values    = [None] * len(x_labels)
                    for i, ts in enumerate(idx_year):
                        if i < len(x_labels) and ts in year_data.index:
                            v = year_data[ts]
                            values[i] = round(float(v), 2) if pd.notna(v) else None
                    line_data[year_key] = values

            elif line_type == "reference":
                ref_val = float(line_cfg.get("value", 0))
                line_data[year_key] = [round(ref_val, 2)] * len(x_labels)

    labels = {cfg["meter"]: cfg.get("label", cfg["meter"]) for cfg in meters_cfg}
    signs  = {cfg["meter"]: -1 if cfg.get("sign") == "negative" else 1
              for cfg in meters_cfg}

    result = {
        "type"           : "bar_stacked",
        "unit"           : unit,
        "resolution"     : resolution,
        "years_available": years_available,
        "data"           : {
            "x_labels": x_labels,
            "series"  : series,
            "labels"  : labels,
            "signs"   : signs,
        }
    }

    if line_data is not None:
        result["data"]["line"] = {
            "values": line_data,
            "label" : line_cfg.get("label", "Cumul"),
            "color" : line_cfg.get("color", "#2c3e50"),
            "type"  : line_cfg.get("type", "cumulative_sum"),
            "unit"  : line_cfg.get("unit", ""),
            "axis"  : line_cfg.get("axis", "primary"),
        }

    return result