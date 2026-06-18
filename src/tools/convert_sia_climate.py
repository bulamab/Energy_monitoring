"""
src/tools/convert_sia_climate.py

Convertit un fichier SIA Design Reference Year (format horaire)
en CSV journalier utilisable par le CSVConnector.

Usage :
    python -m src.tools.convert_sia_climate \
        --input  reference/climate/sia_yverdon_hourly.csv \
        --output reference/climate/sia_yverdon_daily.csv \
        --base-heat 20 \
        --base-cool 12 \
        --year 2002

Le fichier SIA a un index temporel en heures depuis le début de l'année
(Time=0.0 → 1er janvier 00h00, résolution 0.5h ou 1h).

Colonnes produites :
    date                 — YYYY-MM-DD
    temperature_mean_C   — température moyenne journalière
    dj_20_12             — degrés-jours journaliers base 20/12
    radiation_diffuse_Wm2 — rayonnement diffus horizontal moyen
    radiation_direct_Wm2  — rayonnement direct normal moyen
    relhum_mean_pct      — humidité relative moyenne
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def convert_sia(input_path: str,
                output_path: str,
                base_heat: float = 20.0,
                base_cool: float = 12.0,
                year: int = 2002) -> pd.DataFrame:

    print(f"Lecture : {input_path}")

    df = pd.read_csv(input_path, sep="\t")
    # La colonne Time peut s'appeler "#Time" selon le fichier SIA
    if "#Time" in df.columns:
        df = df.rename(columns={"#Time": "Time"})

    print(f"  Colonnes : {list(df.columns)}")
    print(f"  Lignes   : {len(df)}")

    # Reconstruit l'index depuis Time (heures depuis début d'année)
    base_date = pd.Timestamp(f"{year}-01-01 00:00")
    df.index  = df["Time"].apply(lambda h: base_date + pd.Timedelta(hours=h))
    df.index.name = "timestamp"

    # Supprime les éventuels doublons de timestamp avant agrégation
    df = df[~df.index.duplicated(keep='first')]

    # Agrégation journalière
    daily = pd.DataFrame()

    if "TAir" not in df.columns:
        raise ValueError("Colonne 'TAir' manquante dans le fichier SIA.")

    daily["temperature_mean_C"]    = df["TAir"].resample("D").mean().round(2)

    if "IDiffHor" in df.columns:
        daily["radiation_diffuse_Wm2"] = df["IDiffHor"].resample("D").mean().round(1)

    if "IDirNorm" in df.columns:
        daily["radiation_direct_Wm2"]  = df["IDirNorm"].resample("D").mean().round(1)

    if "RelHum" in df.columns:
        daily["relhum_mean_pct"]       = df["RelHum"].resample("D").mean().round(1)

    # DJ journaliers
    temp = daily["temperature_mean_C"]
    dj   = np.where(temp < base_cool, np.maximum(0, base_heat - temp), 0.0)
    daily["dj_20_12"] = np.round(dj, 2)

    daily.index = pd.to_datetime(
        [f"{year}-{ts.month:02d}-{ts.day:02d}" for ts in daily.index]
    )
    daily.index.name = "date"

    # Statistiques
    print(f"\n  Température moyenne annuelle : {daily['temperature_mean_C'].mean():.1f} °C")
    print(f"  DJ annuels base {base_heat:.0f}/{base_cool:.0f} : {daily['dj_20_12'].sum():.0f} Kd")

    # Sauvegarde
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_path, date_format="%Y-%m-%d")
    print(f"\n  Fichier sauvegardé : {output_path}")

    return daily


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convertit un fichier SIA DRY en CSV journalier."
    )
    parser.add_argument("--input",     required=True)
    parser.add_argument("--output",    required=True)
    parser.add_argument("--base-heat", type=float, default=20.0)
    parser.add_argument("--base-cool", type=float, default=12.0)
    parser.add_argument("--year",      type=int,   default=2002)

    args = parser.parse_args()

    daily = convert_sia(
        args.input, args.output,
        args.base_heat, args.base_cool, args.year
    )

    print("\n--- Aperçu ---")
    print(daily.head(10).to_string())
    print("\n--- DJ mensuels ---")
    print(daily["dj_20_12"].resample("MS").sum().round(1).to_string())