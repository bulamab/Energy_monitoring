"""
src/engine/loader.py

Loader — orchestre le pipeline de chargement des données :
    1. Lit config.yml (résolution, timezone)
    2. Instancie le bon connecteur selon source_type
    3. Charge les meters physiques et estimés
    4. Injecte les colonnes de tarifs (type: tariff)
    5. Calcule les meters virtuels

Usage direct (test) :
    python -m src.engine.loader

Usage depuis l'API ou un script :
    from src.engine.loader import Loader
    loader = Loader(project="maison_yverdon")
    df = loader.load(start=date(2025,1,1), end=date(2025,12,31))
"""

import logging
import yaml
from datetime import date
from pathlib import Path

import pandas as pd

from src.connectors.csv_connector import CSVConnector
from src.engine.vm_engine import VirtualMeterEngine

logger = logging.getLogger(__name__)

CONNECTORS = {
    "csv": CSVConnector,
}


class Loader:
    """
    Point d'entrée unique du backend.

    Paramètres
    ----------
    project : str
        Nom du projet — doit correspondre à un dossier dans projects/
    config_path : str
        Chemin vers config.yml (défaut : config.yml à la racine)
    """

    def __init__(self,
                 project: str,
                 config_path: str = "config.yml"):

        self.project      = project
        self.config       = self._load_yaml(Path(config_path))
        self.project_dir  = Path("projects") / project / "config"

        self.meters_path   = self.project_dir / "meters.yml"
        self.sources_path  = self.project_dir / "sources.yml"
        self.building_path = self.project_dir / "building.yml"

        self._check_files()

        self.meters   = self._load_yaml(self.meters_path)["meters"]
        self.building = self._load_yaml(self.building_path)

        self.source_type = self._detect_source_type()
        logger.info(f"Projet '{project}' — source_type détecté : {self.source_type}")

    # ------------------------------------------------------------------
    # Méthode principale
    # ------------------------------------------------------------------

    def load(self, start: date, end: date) -> pd.DataFrame:
        """
        Charge et retourne le DataFrame complet pour la période demandée.

        Étapes :
        1. Meters physiques + estimés (connecteur)
        2. Tarifs (type: tariff) injectés depuis financial.yml
        3. Meters virtuels (vm_engine)

        Retourne
        --------
        pd.DataFrame
            Index  : DatetimeIndex journalier
            Colonnes : tous les meter_ids
        """
        logger.info(f"Chargement : {start} → {end}")

        # Étape 1 — connecteur
        connector_class = CONNECTORS.get(self.source_type)
        if connector_class is None:
            raise ValueError(
                f"source_type '{self.source_type}' non supporté. "
                f"Disponibles : {list(CONNECTORS.keys())}"
            )

        connector = connector_class(
            meters_path  = str(self.meters_path),
            sources_path = str(self.sources_path)
        )

        df = connector.load_physical_meters(start, end)

        if df.empty:
            raise RuntimeError(
                "Aucune donnée chargée — vérifier meters.yml, sources.yml et les CSV."
            )

        logger.info(f"Meters physiques/estimés : {list(df.columns)}")

        # Étape 2 — tarifs
        df = self._inject_tariffs(df, start, end)

        # Étape 3 — meters virtuels
        engine = VirtualMeterEngine(str(self.meters_path), building_path=str(self.building_path))
        df     = engine.resolve(df)

        logger.info(f"Meters après résolution : {list(df.columns)}")

        return df

    # ------------------------------------------------------------------
    # Injection des tarifs
    # ------------------------------------------------------------------

    def _inject_tariffs(self,
                        df: pd.DataFrame,
                        start: date,
                        end: date) -> pd.DataFrame:
        """
        Pour chaque meter de type 'tariff' dans meters.yml :
        1. Résout le provider depuis building.yml
        2. Lit les valeurs depuis financial.yml
        3. Crée une Series journalière alignée sur l'index du DataFrame
        """
        for meter_id, meter in self.meters.items():
            if meter.get("type") != "tariff":
                continue

            try:
                series      = self._resolve_tariff(meter_id, meter, df.index)
                df[meter_id] = series
                logger.info(f"Tarif injecté : '{meter_id}'")
            except Exception as e:
                logger.error(f"Tarif '{meter_id}' : erreur — {e}")

        return df

    def _resolve_tariff(self,
                        meter_id: str,
                        meter: dict,
                        index: pd.DatetimeIndex) -> pd.Series:
        """
        Résout un meter de type tariff vers une Series alignée sur l'index.

        Chemin de résolution :
        provider_ref → building.yml → financial.yml → tariff_key → values
        """
        provider_ref = meter.get("provider_ref")
        if not provider_ref:
            raise ValueError(f"Meter tariff '{meter_id}' : 'provider_ref' manquant.")

        tariff_key = meter.get("tariff_key", "tariff")

        # Résout provider_ref depuis building.yml
        # Ex: "building.energy_providers.electricity"
        #   → building["energy_providers"]["electricity"]["provider_ref"]
        #   → "financial.yverdon_energies_electricity"
        parts    = provider_ref.split(".")
        node     = self.building
        for key in parts[1:]:           # ignore "building"
            node = node[key]

        financial_ref = node.get("provider_ref")
        if not financial_ref:
            raise ValueError(
                f"Meter tariff '{meter_id}' : 'provider_ref' introuvable "
                f"dans building.yml à '{provider_ref}'."
            )

        # Lit financial.yml
        parts         = financial_ref.split(".")
        file_name     = parts[0]                    # financial
        provider_key  = parts[1]                    # yverdon_energies_electricity

        financial_path = Path("reference") / f"{file_name}.yml"
        financial_data = self._load_yaml(financial_path)

        provider_data = financial_data.get(provider_key)
        if not provider_data:
            raise ValueError(
                f"Meter tariff '{meter_id}' : provider '{provider_key}' "
                f"introuvable dans {financial_path}."
            )

        tariff_data = provider_data.get(tariff_key)
        if not tariff_data:
            raise ValueError(
                f"Meter tariff '{meter_id}' : clé '{tariff_key}' "
                f"introuvable pour provider '{provider_key}'."
            )

        annual_values = tariff_data.get("values", {})
        if not annual_values:
            raise ValueError(
                f"Meter tariff '{meter_id}' : 'values' vide pour '{tariff_key}'."
            )

        # Construit une Series annuelle → resamplée journalière
        annual = pd.Series({
            pd.Timestamp(str(year) + "-01-01"): float(val)
            for year, val in annual_values.items()
        }).sort_index()

        # Propage la valeur annuelle sur tous les jours
        daily = annual.resample("D").ffill()
        daily = daily.reindex(index, method="ffill")

        daily.name       = meter_id
        daily.index.name = "date"
        return daily

    # ------------------------------------------------------------------
    # Agrégation mensuelle
    # ------------------------------------------------------------------

    def resample_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrège le DataFrame journalier en mensuel selon la règle par meter :
        - sum  : défaut — énergies (kWh, m3)
        - mean : températures, rayonnement, tarifs (degC, W/m2, CHF/kWh)
        """
        mean_cols = [
            mid for mid, m in self.meters.items()
            if m.get("aggregation", "sum") == "mean"
            and mid in df.columns
        ]

        # Les tarifs sont toujours en mean
        tariff_cols = [
            mid for mid, m in self.meters.items()
            if m.get("type") == "tariff"
            and mid in df.columns
        ]

        mean_cols = list(set(mean_cols + tariff_cols))
        sum_cols  = [c for c in df.columns if c not in mean_cols]

        parts = []
        if sum_cols:
            parts.append(df[sum_cols].resample("MS").sum())
        if mean_cols:
            parts.append(df[mean_cols].resample("MS").mean())

        result = pd.concat(parts, axis=1)
        return result[df.columns]   # remet les colonnes dans l'ordre original

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _detect_source_type(self) -> str:
        sources  = self._load_yaml(self.sources_path)
        bindings = sources.get("bindings", {})
        if not bindings:
            raise ValueError("sources.yml : aucun binding défini.")
        first_binding = next(iter(bindings.values()))
        source_type   = first_binding.get("source_type")
        if not source_type:
            raise ValueError("sources.yml : 'source_type' manquant dans le premier binding.")
        return source_type

    def _check_files(self):
        for path in [self.meters_path, self.sources_path, self.building_path]:
            if not path.exists():
                raise FileNotFoundError(
                    f"Fichier de configuration introuvable : {path}"
                )

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


# ----------------------------------------------------------------------
# Test intégré
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(levelname)s — %(message)s"
    )

    PROJECT = "maison_yverdon"
    START   = date(2025, 1, 1)
    END     = date(2025, 12, 31)

    print("\n" + "="*60)
    print("  TEST Loader")
    print(f"  Projet  : {PROJECT}")
    print(f"  Période : {START} → {END}")
    print("="*60 + "\n")

    try:
        loader = Loader(project=PROJECT)
        df     = loader.load(start=START, end=END)
    except Exception as e:
        print(f"ERREUR : {e}")
        sys.exit(1)

    print(f"\nMeters disponibles : {list(df.columns)}")
    print(f"Jours chargés      : {len(df)}")
    print(f"Valeurs manquantes :\n{df.isna().sum()}\n")

    print("--- Totaux/moyennes mensuels ---")
    monthly = loader.resample_monthly(df)
    print(monthly.to_string())

    print("\n✓ Test Loader terminé sans erreur.")