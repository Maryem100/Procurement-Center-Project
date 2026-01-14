"""
Script de calcul du net demand pour toutes les dates
"""

import pandas as pd
import psycopg2
import yaml
from pathlib import Path
import subprocess
import os

# Chargement configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=== Calcul du Net Demand pour toutes les dates ===\n")

# Connexion PostgreSQL pour charger products une seule fois
conn = psycopg2.connect(
    host='procurement_postgres',
    database='procurement_db',
    user='postgres',
    password='postgres'
)

products_df = pd.read_sql('SELECT sku, supplier_id, pack_size, min_order_quantity as moq, safety_stock FROM products', conn)
conn.close()

print(f"✓ Produits chargés: {len(products_df)}\n")

# Chemins
agg_path = Path('data/processed/aggregated_orders')
stock_path = Path('data/raw/stock')
output_path_local = Path('data/processed/net_demand')
output_path_hdfs = "/procurement/processed/net_demand"

output_path_local.mkdir(parents=True, exist_ok=True)

# Traiter chaque date
agg_files = sorted(agg_path.glob('aggregated_orders_*.csv'))

print(f"Nombre de dates à traiter: {len(agg_files)}\n")

for agg_file in agg_files:
    date_str = agg_file.stem.split('_')[-1]
    print(f"📅 Traitement du {date_str}...")
    
    # 1. Lire agrégation
    orders_agg = pd.read_csv(agg_file)
    
    # 2. Lire stocks correspondants
    stock_date_path = stock_path / date_str
    if not stock_date_path.exists():
        print(f"   ⚠ Pas de stock pour {date_str}, ignoré")
        continue
    
    all_stocks = []
    for csv_file in stock_date_path.glob('*.csv'):
        df = pd.read_csv(csv_file)
        all_stocks.append(df)
    
    stocks_df = pd.concat(all_stocks, ignore_index=True)
    
    # Agréger stocks par SKU
    stocks_agg = stocks_df.groupby('sku').agg({
        'available_quantity': 'sum',
        'reserved_quantity': 'sum'
    }).reset_index()
    
    stocks_agg.rename(columns={
        'available_quantity': 'available_stock',
        'reserved_quantity': 'reserved_stock'
    }, inplace=True)
    
    # 3. Joindre
    result = orders_agg.merge(stocks_agg, on='sku', how='left')
    result = result.merge(products_df[['sku', 'supplier_id', 'pack_size', 'moq', 'safety_stock']], on='sku', how='left')
    
    # 4. Calculer net demand
    result['net_demand'] = result.apply(
        lambda row: max(0, row['total_quantity'] + row['safety_stock'] - 
                        (row['available_stock'] - row['reserved_stock'])),
        axis=1
    )
    
    # 5. Arrondir au pack_size
    result['order_quantity'] = (result['net_demand'] / result['pack_size']).apply(lambda x: int(x) if x > 0 else 0) * result['pack_size']
    
    # Appliquer MOQ
    result['order_quantity'] = result.apply(
        lambda row: max(row['order_quantity'], row['moq']) if row['order_quantity'] > 0 else 0,
        axis=1
    )
    
    # Filtrer SKUs à commander
    to_order = result[result['order_quantity'] > 0].copy()
    
    print(f"   SKUs à commander: {len(to_order)}")
    print(f"   Quantité totale: {to_order['order_quantity'].sum()}")
    
    # 6. Sauvegarder localement
    output_file_local = output_path_local / f"net_demand_{date_str}.csv"
    to_order.to_csv(output_file_local, index=False)
    print(f"   ✓ Sauvegardé: {output_file_local}")
    
    print()

print(f"\n✅ Net demand calculé pour {len(agg_files)} dates")
print(f"📁 Fichiers locaux: {output_path_local}/")