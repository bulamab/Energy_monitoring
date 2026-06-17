"""
src/utils.py

Fonctions utilitaires partagées entre tous les modules.
"""

import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_ref(ref: str,
                reference_dir: str = "reference/",
                building_path: str = None) -> float:
    """
    Résout une référence pointée vers un fichier YAML.

    Deux préfixes supportés :
    - "energy_carriers.xxx" → reference/energy_carriers.yml
    - "financial.xxx"       → reference/financial.yml
    - "building.xxx"        → building.yml du projet (nécessite building_path)

    Exemples :
        resolve_ref("energy_carriers.natural_gas.m3_to_pci")
        resolve_ref("building.equipment.pv.surface_m2",
                    building_path="projects/maison_yverdon/config/building.yml")

    Paramètres
    ----------
    ref          : str  — référence pointée
    reference_dir: str  — dossier des fichiers de référence
    building_path: str  — chemin vers building.yml (requis si ref commence par "building.")

    Retourne
    --------
    float — valeur numérique résolue

    Lève
    ----
    FileNotFoundError : fichier YAML introuvable
    KeyError          : clé absente
    ValueError        : valeur non numérique ou building_path manquant
    """
    parts     = ref.split(".")
    prefix    = parts[0]           # "energy_carriers", "financial", "building", etc.
    keys      = parts[1:]          # chemin dans le fichier

    # --- Résolution depuis building.yml ---
    if prefix == "building":
        if not building_path:
            raise ValueError(
                f"resolve_ref : référence '{ref}' nécessite building_path."
            )
        path = Path(building_path)
        if not path.exists():
            raise FileNotFoundError(
                f"resolve_ref : building.yml introuvable → {path}"
            )

    # --- Résolution depuis reference/ ---
    else:
        path = Path(reference_dir) / f"{prefix}.yml"
        if not path.exists():
            raise FileNotFoundError(
                f"resolve_ref : fichier introuvable → {path}\n"
                f"Référence demandée : '{ref}'"
            )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(
                f"resolve_ref : clé '{key}' introuvable dans '{ref}'\n"
                f"Clés disponibles : {list(value.keys()) if isinstance(value, dict) else 'N/A'}"
            )
        value = value[key]
    

    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"resolve_ref : valeur non numérique pour '{ref}' : {value!r}"
        )





def resample_meter(series: "pd.Series",
                   meter_def: dict,
                   freq: str = "MS") -> "pd.Series":
    """
    Agrège une Series selon la règle d'agrégation définie dans meters.yml.

    Paramètres
    ----------
    series     : pd.Series — série journalière à agréger
    meter_def  : dict      — définition du meter depuis meters.yml
    freq       : str       — fréquence cible (défaut: "MS" = mensuel)

    Retourne
    --------
    pd.Series agrégée selon aggregation: sum (défaut) ou mean
    """
    agg = meter_def.get("aggregation", "sum")
    if agg == "mean":
        return series.resample(freq).mean().round(4)
    else:
        return series.resample(freq).sum().round(2)

# ----------------------------------------------------------------------
# Test intégré
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level  = logging.INFO,
        format = "%(levelname)s — %(message)s"
    )

    print("\n" + "="*60)
    print("  TEST resolve_ref")
    print("="*60 + "\n")

    tests_reference = [
        ("energy_carriers.natural_gas.m3_to_pci", None),
        ("energy_carriers.natural_gas.m3_to_pcs", None),
        ("energy_carriers.electricity.primary_energy_factors.mix_prod_CH.value", None),
    ]

    tests_building = [
        ("building.params.sre", "projects/maison_yverdon/config/building.yml"),
        ("building.equipment.pv.surface_m2", "projects/maison_yverdon/config/building.yml"),
        ("building.equipment.pv.peak_power_kwc", "projects/maison_yverdon/config/building.yml"),
    ]

    print("--- Références fichiers de référence ---")
    for ref, bp in tests_reference:
        try:
            val = resolve_ref(ref)
            print(f"  OK  {ref} → {val}")
        except Exception as e:
            print(f"  ERREUR  {ref} → {e}")

    print("\n--- Références building.yml ---")
    for ref, bp in tests_building:
        try:
            val = resolve_ref(ref, building_path=bp)
            print(f"  OK  {ref} → {val}")
        except Exception as e:
            print(f"  ERREUR  {ref} → {e}")

    print("\n✓ Test terminé.")