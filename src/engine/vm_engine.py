"""
src/engine/vm_engine.py

VirtualMeterEngine — calcule les meters de type 'virtual' depuis un DataFrame
contenant les meters physiques et estimés.

Les meters virtuels sont définis par une formule dans meters.yml :
    formula: "pv_production - grid_out"
    formula: "gas_in * eta_boiler"
    formula: "(gas_in * eta_boiler) - dhw_demand_estimated"

Les constantes peuvent être définies inline ou référencées depuis
les fichiers de référence :
    constants:
      eta_boiler: 0.85
      kwh_per_m3:
        ref: energy_carriers.natural_gas.m3_to_pci

Algorithme : tri topologique de Kahn — résout l'ordre de calcul
et détecte les dépendances circulaires.

Usage direct (test) :
    python -m src.engine.vm_engine
"""

import re
import logging
import numpy as np
from collections import deque

import pandas as pd
import yaml
from pathlib import Path

from src.utils import resolve_ref

logger = logging.getLogger(__name__)


class VirtualMeterEngine:
    """
    Calcule les meters virtuels et les ajoute au DataFrame.

    Paramètres
    ----------
    meters_path : str
        Chemin vers meters.yml
    """

    def __init__(self, meters_path: str, building_path: str = None):
        self.meters_path  = Path(meters_path)
        self.building_path = building_path
        self.meters       = self._load_yaml(self.meters_path)["meters"]

    # ------------------------------------------------------------------
    # Méthode principale
    # ------------------------------------------------------------------

    def resolve(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule tous les meters virtuels et les ajoute au DataFrame.

        Paramètres
        ----------
        df : pd.DataFrame
            DataFrame contenant les meters physiques et estimés.
            Index : DatetimeIndex journalier.

        Retourne
        --------
        pd.DataFrame
            DataFrame enrichi avec les colonnes virtuelles calculées.
        """
        df = df.copy()

        # Construit le graphe de dépendances
        graph = self._build_graph()

        # Tri topologique → ordre de calcul garanti
        order = self._topological_sort(graph)

        for meter_id in order:
            meter = self.meters[meter_id]

            if meter["type"] not in ("virtual", "derived"):
                continue  # physical, estimated, tariff, reference_year déjà dans df

            if meter_id in df.columns:
                continue

            # Vérifie que toutes les dépendances sont disponibles
            deps    = self._get_dependencies(meter)
            missing = [d for d in deps if d not in df.columns]
            if missing:
                logger.error(
                    f"Meter virtuel '{meter_id}' : dépendances manquantes "
                    f"{missing} — ignoré."
                )
                continue

            try:
                if meter["type"] == "derived":
                    df[meter_id] = self._compute_derived(df, meter_id, meter)
                    logger.info(f"Meter derived calculé : '{meter_id}'")
                else:
                    df[meter_id] = self._compute(df, meter_id, meter)
                    logger.info(f"Meter virtuel calculé : '{meter_id}'")
            except Exception as e:
                logger.error(f"Meter '{meter_id}' : erreur — {e}")

        return df

    # ------------------------------------------------------------------
    # Calcul d'un meter virtuel
    # ------------------------------------------------------------------

    def _compute(self,
                 df: pd.DataFrame,
                 meter_id: str,
                 meter: dict) -> pd.Series:
        """
        Évalue la formule définie dans meters.yml via pandas.eval().
        Les constantes sont injectées comme variables locales.
        """
        formula = meter.get("formula")
        if not formula:
            raise ValueError(
                f"Meter '{meter_id}' : champ 'formula' manquant."
            )

        constants = self._resolve_constants(
            meter.get("constants", {}),
            meter_id
        )

        try:
            result = df.eval(formula, local_dict=constants)
            # Remplace inf et -inf par NaN — JSON ne supporte pas ces valeurs
            import numpy as np
            result = result.replace([np.inf, -np.inf], np.nan)
            return result
        except Exception as e:
            raise ValueError(
                f"Meter '{meter_id}' : erreur dans la formule "
                f"'{formula}' — {e}"
            )

    def _resolve_constants(self,
                           constants: dict,
                           meter_id: str) -> dict:
        """
        Résout les constantes définies dans meters.yml.

        Supporte :
        - Valeur numérique directe : eta_boiler: 0.85
        - Référence vers fichier de référence :
            kwh_per_m3:
              ref: energy_carriers.natural_gas.m3_to_pci
        """
        resolved = {}
        for name, val in constants.items():
            if isinstance(val, dict) and "ref" in val:
                try:
                    resolved[name] = resolve_ref(val["ref"], building_path=self.building_path)
                    logger.info(
                        f"Meter '{meter_id}' : constante '{name}' "
                        f"résolue depuis '{val['ref']}' = {resolved[name]}"
                    )
                except Exception as e:
                    raise ValueError(
                        f"Meter '{meter_id}' : impossible de résoudre "
                        f"la constante '{name}' — {e}"
                    )
            else:
                try:
                    resolved[name] = float(val)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Meter '{meter_id}' : constante '{name}' "
                        f"n'est pas numérique : {val!r}"
                    )
        return resolved

    def _compute_derived(self,
                         df: pd.DataFrame,
                         meter_id: str,
                         meter: dict) -> pd.Series:
        """
        Calcule un meter de type 'derived' — opérations non supportées
        par pandas.eval() comme les conditions, clip, etc.

        Méthodes supportées :
            degree_days : degrés-jours de chauffage
        """
        method = meter.get("method")
        params = meter.get("params", {})

        if method == "hours_per_timestep":
            return self._method_hours_per_timestep(df, meter_id)
        elif method == "degree_days":
            return self._method_degree_days(df, meter_id, params)
        else:
            raise ValueError(
                f"Meter derived '{meter_id}' : méthode inconnue '{method}'. "
                f"Méthodes supportées : hours_per_timestep, degree_days"
            )

    def _method_hours_per_timestep(self,
                                df: pd.DataFrame,
                                meter_id: str) -> pd.Series:
        """
        Nombre d'heures par pas de temps.
        - Résolution journalière : 24.0 par jour
        - Résolution mensuelle  : jours_du_mois × 24
        Détecté automatiquement depuis la fréquence de l'index.
        """
        freq = pd.infer_freq(df.index)

        if freq in ("MS", "ME", "M", "BMS"):
            # Mensuel — nombre de jours du mois × 24
            hours = df.index.days_in_month * 24.0
        else:
            # Journalier (ou autre) — 24h par défaut
            hours = pd.Series(24.0, index=df.index)

        series = pd.Series(hours, index=df.index, name=meter_id)
        logger.info(f"hours_per_timestep : fréquence détectée '{freq}', "
                    f"min={series.min():.0f}h, max={series.max():.0f}h")
        return series

    def _method_degree_days(self,
                            df: pd.DataFrame,
                            meter_id: str,
                            params: dict) -> pd.Series:
        """
        Degrés-jours de chauffage journaliers.
        DJ_jour = max(0, T_base_heat - T_ext) si T_ext < T_base_cool
                  0 sinon

        Paramètres YAML :
            temp_meter  : meter_id de la température extérieure
            base_heat   : température de chauffe (défaut: 20°C)
            base_cool   : seuil d'activation chauffage (défaut: 12°C)
        """
        temp_meter = params.get("temp_meter", "temp_ext")
        base_heat  = float(params.get("base_heat", 20.0))
        base_cool  = float(params.get("base_cool", 12.0))

        if temp_meter not in df.columns:
            raise ValueError(
                f"degree_days : meter température '{temp_meter}' absent du DataFrame."
            )

        temp = df[temp_meter]

        # DJ journalier : max(0, base_heat - T_ext) si T_ext < base_cool
        dj = np.where(
            temp < base_cool,
            np.maximum(0, base_heat - temp),
            0.0
        )

        series = pd.Series(dj, index=df.index, name=meter_id)
        return series.round(2)

    # ------------------------------------------------------------------
    # Tri topologique de Kahn
    # ------------------------------------------------------------------

    def _build_graph(self) -> dict:
        """
        Construit le graphe de dépendances {meter_id: [dépendances]}.
        """
        graph = {}
        for mid, meter in self.meters.items():
            if meter["type"] in ("virtual", "derived"):
                graph[mid] = self._get_dependencies(meter)
            else:
                graph[mid] = []  # physical, estimated, tariff, reference_year : pas de dépendances
        return graph

    def _topological_sort(self, graph: dict) -> list:
        """
        Algorithme de Kahn.
        Retourne l'ordre de calcul ou lève une erreur si cycle détecté.
        """
        in_degree = {mid: len(deps) for mid, deps in graph.items()}
        queue     = deque(mid for mid, deg in in_degree.items() if deg == 0)
        order     = []

        while queue:
            mid = queue.popleft()
            order.append(mid)
            for other, deps in graph.items():
                if mid in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        if len(order) != len(graph):
            cyclic = [mid for mid in graph if mid not in order]
            raise ValueError(
                f"Dépendances circulaires détectées : {cyclic}"
            )

        return order

    def _get_dependencies(self, meter: dict) -> list:
        """
        Extrait les dépendances d'un meter virtual ou derived.
        """
        if meter.get("type") == "derived":
            # Les dépendances sont dans params
            params = meter.get("params", {})
            deps   = []
            for key in ["temp_meter", "meter"]:
                val = params.get(key)
                if val and val in self.meters:
                    deps.append(val)
            return deps

        # Virtual — extrait depuis la formule
        formula   = meter.get("formula", "")
        constants = set(meter.get("constants", {}).keys())
        tokens    = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula)
        return [
            t for t in tokens
            if t in self.meters and t not in constants
        ]

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


# ----------------------------------------------------------------------
# Test intégré
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from datetime import date
    from src.connectors.csv_connector import CSVConnector

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(levelname)s — %(message)s"
    )

    METERS_PATH  = "projects/maison_yverdon/config/meters.yml"
    SOURCES_PATH = "projects/maison_yverdon/config/sources.yml"
    START        = date(2025, 1, 1)
    END          = date(2025, 12, 31)

    print("\n" + "="*60)
    print("  TEST VirtualMeterEngine")
    print(f"  Période : {START} → {END}")
    print("="*60 + "\n")

    for p in [METERS_PATH, SOURCES_PATH]:
        if not Path(p).exists():
            print(f"ERREUR : fichier introuvable → {p}")
            sys.exit(1)

    # Étape 1 — charge les meters physiques
    connector = CSVConnector(METERS_PATH, SOURCES_PATH)
    df        = connector.load_physical_meters(START, END)
    print(f"Meters physiques chargés : {list(df.columns)}\n")

    # Étape 2 — calcule les meters virtuels
    engine = VirtualMeterEngine(METERS_PATH)
    df     = engine.resolve(df)

    print(f"\nMeters après résolution : {list(df.columns)}")
    print(f"Valeurs manquantes :\n{df.isna().sum()}\n")

    print("--- Totaux mensuels ---")
    monthly = df.resample("MS").sum()
    print(monthly.to_string())

    print("\n✓ Test terminé sans erreur.")