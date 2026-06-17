"""
src/connectors/csv_connector.py

Connecteur CSV — implémente BaseConnector pour des sources de type fichier CSV.

Usage direct (test) :
    python -m src.connectors.csv_connector
"""

from datetime import date
import pandas as pd
import logging
from pathlib import Path

from src.connectors.base import BaseConnector
from src.utils import resolve_ref

logger = logging.getLogger(__name__)


class CSVConnector(BaseConnector):
    """
    Connecteur pour sources de données CSV.

    Chaque binding dans sources.yml peut contenir :
        source_type          : csv
        base_path            : chemin vers le dossier contenant les CSV
        file                 : nom du fichier CSV
        date_column          : nom de la colonne date
        value_column         : nom de la colonne valeur
        unit                 : unité brute (informatif)
        conversion_factor_ref: référence pointée vers energy_carriers.yml
                               ex: energy_carriers.natural_gas.m3_to_pci
                               Si présent, la valeur est multipliée par ce facteur.
    """

    def _source_type(self) -> str:
        return "csv"

    def query(self,
              binding: dict,
              start: date,
              end: date,
              warn_missing: bool = True) -> pd.Series:
        """
        Lit un fichier CSV et retourne une Series journalière
        filtrée sur la période [start, end].

        Si 'conversion_factor_ref' est présent dans le binding,
        applique le facteur de conversion correspondant.
        """
        base_path = Path(binding["base_path"])
        file_path = base_path / binding["file"]
        date_col  = binding["date_column"]
        value_col = binding["value_column"]

        if not file_path.exists():
            raise FileNotFoundError(f"Fichier CSV introuvable : {file_path}")

        df = pd.read_csv(
            file_path,
            parse_dates=[date_col],
            dayfirst=False
        )

        # Vérifie que les colonnes attendues existent
        for col in [date_col, value_col]:
            if col not in df.columns:
                raise ValueError(
                    f"Colonne '{col}' absente dans {file_path.name}. "
                    f"Colonnes disponibles : {list(df.columns)}"
                )

        df = df[[date_col, value_col]].copy()
        df = df.rename(columns={date_col: "date", value_col: "value"})
        df = df.set_index("date")
        df.index = pd.DatetimeIndex(df.index)
        df = df.sort_index()

        # Filtre sur la période demandée
        mask   = (df.index.date >= start) & (df.index.date <= end)
        series = df.loc[mask, "value"].astype(float)

        # Réindexe sur l'index journalier complet — NaN si jour manquant
        full_idx = pd.date_range(start=start, end=end, freq="D")
        series   = series.reindex(full_idx)

        if warn_missing and series.isna().any():
            n_missing = series.isna().sum()
            logger.warning(
                f"{file_path.name} : {n_missing} jour(s) manquant(s) "
                f"sur la période → NaN"
            )

        # Conversion si conversion_factor_ref présent
        conversion_ref = binding.get("conversion_factor_ref")
        if conversion_ref:
            try:
                factor = resolve_ref(conversion_ref)
                series = series * factor
                logger.info(
                    f"{file_path.name} : conversion appliquée "
                    f"({conversion_ref} = {factor})"
                )
            except Exception as e:
                logger.error(
                    f"{file_path.name} : échec de la conversion "
                    f"'{conversion_ref}' — {e}"
                )

        series.index.name = "date"
        return series


# ----------------------------------------------------------------------
# Test intégré
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level   = logging.INFO,
        format  = "%(levelname)s — %(message)s"
    )

    METERS_PATH  = "projects/maison_yverdon/config/meters.yml"
    SOURCES_PATH = "projects/maison_yverdon/config/sources.yml"
    START        = date(2025, 1, 1)
    END          = date(2025, 12, 31)

    print("\n" + "="*60)
    print("  TEST CSVConnector")
    print(f"  Période : {START} → {END}")
    print("="*60 + "\n")

    for p in [METERS_PATH, SOURCES_PATH]:
        if not Path(p).exists():
            print(f"ERREUR : fichier introuvable → {p}")
            sys.exit(1)

    connector = CSVConnector(METERS_PATH, SOURCES_PATH)
    df        = connector.load_physical_meters(START, END)

    if df.empty:
        print("ERREUR : DataFrame vide — vérifier meters.yml et sources.yml.")
        sys.exit(1)

    print(f"Meters chargés     : {list(df.columns)}")
    print(f"Période effective  : {df.index[0].date()} → {df.index[-1].date()}")
    print(f"Nombre de jours    : {len(df)}")
    print(f"Valeurs manquantes :\n{df.isna().sum()}\n")

    print("--- Premières lignes ---")
    print(df.head())
    print("\n--- Totaux mensuels ---")
    print(df.resample("MS").sum().to_string())

    print("\n✓ Test terminé sans erreur.")