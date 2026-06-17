"""
src/connectors/base.py

Classe abstraite BaseConnector.
Chaque source de données (CSV, InfluxDB, API...) implémente cette interface.

Types de meters gérés :
    physical       — lit depuis une source externe
    estimated      — valeurs manuelles dans meters.yml
    tariff         — géré par loader.py
    virtual        — géré par vm_engine.py
    derived        — géré par vm_engine.py
    reference_year — lit une source d'une année, répète sur tout l'index
"""

from abc import ABC, abstractmethod
from datetime import date
import pandas as pd
import numpy as np
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseConnector(ABC):

    def __init__(self, meters_path: str, sources_path: str):
        self.meters_path  = Path(meters_path)
        self.sources_path = Path(sources_path)
        self.meters       = self._load_yaml(self.meters_path)
        self.sources      = self._load_yaml(self.sources_path)

    # ------------------------------------------------------------------
    # Méthode abstraite
    # ------------------------------------------------------------------

    @abstractmethod
    def query(self, binding: dict, start: date, end: date,
              warn_missing: bool = True) -> pd.Series:
        pass

    # ------------------------------------------------------------------
    # Méthode principale
    # ------------------------------------------------------------------

    def load_physical_meters(self,
                             start: date,
                             end: date) -> pd.DataFrame:
        """
        Charge tous les meters physical, estimated et reference_year.
        Les reference_year sont traités en dernier car ils ont besoin
        de l'index complet du DataFrame.
        """
        series_dict = {}

        # Étape 1 — physical + estimated
        for meter_id, meter in self.meters["meters"].items():
            meter_type = meter["type"]

            if meter_type == "physical":
                series = self._load_physical(meter_id, meter, start, end)
                if series is not None:
                    series_dict[meter_id] = series

            elif meter_type == "estimated":
                series = self._load_estimated(meter_id, meter, start, end)
                if series is not None:
                    series_dict[meter_id] = series

            elif meter_type in ("virtual", "derived", "tariff"):
                pass  # traités ailleurs

            else:
                logger.warning(
                    f"Meter '{meter_id}' : type inconnu '{meter_type}', ignoré."
                )

        if not series_dict:
            logger.warning("Aucun meter chargé — vérifier meters.yml et sources.yml.")
            return pd.DataFrame()

        df = pd.DataFrame(series_dict)
        df.index = pd.DatetimeIndex(df.index)
        df.index.name = "date"

        # Étape 2 — reference_year (besoin de l'index complet)
        for meter_id, meter in self.meters["meters"].items():
            if meter["type"] == "reference_year":
                series = self._load_reference_year(meter_id, meter, df.index)
                if series is not None:
                    df[meter_id] = series

        return df

    # ------------------------------------------------------------------
    # Chargement physical
    # ------------------------------------------------------------------

    def _load_physical(self, meter_id, meter, start, end):
        source_ref = meter.get("source_ref")
        if not source_ref:
            logger.error(f"Meter '{meter_id}' : 'source_ref' manquant.")
            return None

        bindings = self.sources.get("bindings", {})
        binding  = bindings.get(source_ref)
        if binding is None:
            logger.error(f"Meter '{meter_id}' : source_ref '{source_ref}' introuvable.")
            return None

        expected_type = self._source_type()
        binding_type  = binding.get("source_type", "")
        if binding_type != expected_type:
            logger.warning(
                f"Meter '{meter_id}' : source_type '{binding_type}' "
                f"ne correspond pas au connecteur '{expected_type}', ignoré."
            )
            return None

        try:
            series      = self.query(binding, start, end)
            series.name = meter_id
            return series
        except Exception as e:
            logger.error(f"Meter '{meter_id}' : erreur chargement — {e}")
            return None

    # ------------------------------------------------------------------
    # Chargement estimated
    # ------------------------------------------------------------------

    def _load_estimated(self, meter_id, meter, start, end):
        idx = pd.date_range(start=start, end=end, freq="D")

        if "values" in meter:
            monthly = {}
            for month_str, val in meter["values"].items():
                monthly[pd.Timestamp(month_str)] = float(val)
            monthly_series = pd.Series(monthly).sort_index()
            daily_series   = monthly_series.resample("D").ffill()
            daily_series   = daily_series.reindex(idx)

        elif "default_value" in meter:
            daily_series = pd.Series(
                data  = float(meter["default_value"]),
                index = idx
            )
        else:
            logger.warning(f"Meter estimé '{meter_id}' : ni 'values' ni 'default_value'.")
            daily_series = pd.Series(data=float("nan"), index=idx)

        daily_series.name       = meter_id
        daily_series.index.name = "date"
        return daily_series

    # ------------------------------------------------------------------
    # Chargement reference_year
    # ------------------------------------------------------------------

    def _load_reference_year(self,
                              meter_id: str,
                              meter: dict,
                              full_index: pd.DatetimeIndex) -> pd.Series | None:
        """
        Lit une source d'une seule année de référence et la répète
        sur tout l'index du DataFrame par correspondance mois/jour.

        Si method: degree_days est défini, calcule les DJ depuis
        la température lue. Sinon, retourne la valeur brute.
        """
        source_ref = meter.get("source_ref")
        if not source_ref:
            logger.error(f"Meter reference_year '{meter_id}' : 'source_ref' manquant.")
            return None

        bindings = self.sources.get("bindings", {})
        binding  = bindings.get(source_ref)
        if binding is None:
            logger.error(f"Meter '{meter_id}' : source_ref '{source_ref}' introuvable.")
            return None

        expected_type = self._source_type()
        if binding.get("source_type", "") != expected_type:
            logger.warning(f"Meter '{meter_id}' : source_type incompatible, ignoré.")
            return None

        # Lit toute la source sans filtre de date
        # On utilise une plage très large pour capturer n'importe quelle année
        try:
            start_ref = date(1990, 1, 1)
            end_ref   = date(2030, 12, 31)
            ref_series = self.query(binding, start_ref, end_ref, warn_missing=False)
            # Supprime les NaN — ne garde que les valeurs réelles
            ref_series = ref_series.dropna()
        except Exception as e:
            logger.error(f"Meter reference_year '{meter_id}' : erreur lecture — {e}")
            return None

        if ref_series.empty:
            logger.error(f"Meter reference_year '{meter_id}' : aucune donnée trouvée.")
            return None

        logger.info(
            f"Meter reference_year '{meter_id}' : "
            f"{len(ref_series)} jours lus "
            f"({ref_series.index[0].date()} → {ref_series.index[-1].date()})"
        )

        # Construit un dict {(month, day): value} depuis l'année de référence
        ref_dict = {}
        for ts, val in ref_series.items():
            key = (ts.month, ts.day)
            ref_dict[key] = val

        # Applique la méthode si définie
        method = meter.get("method")
        params = meter.get("params", {})

        if method == "degree_days":
            base_heat = float(params.get("base_heat", 20.0))
            base_cool = float(params.get("base_cool", 12.0))

            values = []
            for ts in full_index:
                temp = ref_dict.get((ts.month, ts.day), float("nan"))
                if pd.notna(temp) and temp < base_cool:
                    dj = max(0.0, base_heat - temp)
                else:
                    dj = 0.0
                values.append(round(dj, 2))

        else:
            # Valeur brute répétée
            values = [
                ref_dict.get((ts.month, ts.day), float("nan"))
                for ts in full_index
            ]

        series = pd.Series(values, index=full_index, name=meter_id)
        series.index.name = "date"

        logger.info(
            f"Meter reference_year '{meter_id}' : "
            f"{sum(1 for v in values if not pd.isna(v))} jours remplis "
            f"sur {len(full_index)}"
        )
        return series

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @abstractmethod
    def _source_type(self) -> str:
        pass

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)