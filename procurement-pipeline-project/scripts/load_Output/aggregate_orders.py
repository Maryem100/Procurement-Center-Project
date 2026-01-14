"""
Script d'agrégation des commandes pour toutes les dates
Calcule la demande totale par SKU pour chaque jour
"""

import pandas as pd
import os
from pathlib import Path
import subprocess
import yaml

# Chargement configuration
config_path = 'config/config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Chemins
orders_path = "data/raw/orders"
output_path_local = "data/processed/aggregated_orders"
output_path_hdfs = "/procurement/processed/aggregated_orders"

os.makedirs(output_path_local, exist_ok=True)

print("=== Agrégation des commandes pour toutes les dates ===\n")

# Traiter toutes les dates
date_folders = sorted([d for d in Path(orders_path).iterdir() if d.is_dir()])

print(f"Nombre de dates à traiter: {len(date_folders)}\n")

for date_folder in date_folders:
    date_str = date_folder.name
    print(f"📅 Traitement du {date_str}...")
    
    # Lire tous les CSV du jour
    all_orders = []
    csv_files = list(date_folder.glob("*.csv"))
    
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        all_orders.append(df)
    
    # Concaténer
    orders_df = pd.concat(all_orders, ignore_index=True)
    print(f"   Total lignes: {len(orders_df)}")
    
    # Agrégation par SKU
    aggregated = orders_df.groupby('sku').agg({
        'quantity': 'sum',
        'product_name': 'first'
    }).reset_index()
    
    aggregated.columns = ['sku', 'total_quantity', 'product_name']
    print(f"   SKUs distincts: {len(aggregated)}")
    
    # Sauvegarder localement
    output_file_local = f"{output_path_local}/aggregated_orders_{date_str}.csv"
    aggregated.to_csv(output_file_local, index=False)
    print(f"   ✓ Sauvegardé: {output_file_local}")
    
    # Transférer vers HDFS
    hdfs_command = f"docker exec procurement_namenode hdfs dfs -put -f /data/processed/aggregated_orders/aggregated_orders_{date_str}.csv {output_path_hdfs}/"
    result = subprocess.run(hdfs_command, shell=True, capture_output=True)
    
    if result.returncode == 0:
        print(f"   ✓ Transféré vers HDFS: {output_path_hdfs}/")
    else:
        print(f"   ⚠ Erreur transfert HDFS")
    
    print()

print(f"✅ Agrégation complète pour {len(date_folders)} dates")
print(f"📁 Fichiers locaux: {output_path_local}/")
print(f"📁 Fichiers HDFS: {output_path_hdfs}/")