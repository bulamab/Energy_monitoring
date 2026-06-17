"""
src/charts/__init__.py

Registre auto-découverte des types de graphiques.

Pour ajouter un nouveau type de graphique :
1. Créer src/charts/mon_type.py avec CHART_META + compute()
2. Créer src/dashboard/charts/mon_type.js avec render()
C'est tout — le registre se met à jour automatiquement.
"""

import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHART_HANDLERS = {}
CHART_META     = {}

# Scanne tous les fichiers .py du dossier (sauf __init__.py)
_charts_dir = Path(__file__).parent

for _path in sorted(_charts_dir.glob("*.py")):
    if _path.name.startswith("_"):
        continue

    _module_name = f"src.charts.{_path.stem}"
    try:
        _module = importlib.import_module(_module_name)

        if hasattr(_module, "CHART_META") and hasattr(_module, "compute"):
            _meta  = _module.CHART_META
            _ctype = _meta["type"]
            CHART_HANDLERS[_ctype] = _module.compute
            CHART_META[_ctype]     = _meta
            logger.debug(f"Chart enregistré : '{_ctype}'")
        else:
            logger.warning(
                f"Module '{_path.name}' ignoré — "
                f"CHART_META ou compute() manquant."
            )
    except Exception as e:
        logger.error(f"Erreur chargement chart '{_path.name}' : {e}")

logger.info(f"Charts disponibles : {list(CHART_HANDLERS.keys())}")