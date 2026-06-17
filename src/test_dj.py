from datetime import date
from src.engine.loader import Loader
import logging
logging.basicConfig(level=logging.WARNING)

loader = Loader(project='maison_yverdon')
df = loader.load(start=date(2025,1,1), end=date(2025,12,31))

col = 'dj_reference_daily'
if col in df.columns:
    print(df[col].head(10))
    print('Somme:', df[col].sum())
    print('NaN:', df[col].isna().sum())
else:
    print('Colonne absente')

# test_dj.py — ajoute ces lignes
import pandas as pd
sia = pd.read_csv('reference/climate/PAY_dry_Daily.csv', index_col='date')
print(sia.head(10))
print('temperature_mean_C min/max:', sia['temperature_mean_C'].min(), sia['temperature_mean_C'].max())

# Vérifie le dict de référence construit
from src.connectors.csv_connector import CSVConnector
conn = CSVConnector('projects/maison_yverdon/config/meters.yml',
                    'projects/maison_yverdon/config/sources.yml')
from datetime import date
ref = conn.query(
    conn.sources['bindings']['sia_daily'],
    date(2000,1,1), date(2004,12,31),
    warn_missing=False
)
print('Série SIA janvier:', ref.head(10))