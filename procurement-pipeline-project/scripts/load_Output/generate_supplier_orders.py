"""
Génération des commandes fournisseurs pour toutes les dates
Lit tous les fichiers net_demand et génère les fichiers JSON par fournisseur
"""

import pandas as pd
import json
from pathlib import Path

print("=== Génération des Commandes Fournisseurs pour toutes les dates ===\n")

# Chemins
net_demand_path = Path('data/processed/net_demand')
output_base = Path('data/output/supplier_orders')

# Lire tous les fichiers net_demand
net_demand_files = sorted(net_demand_path.glob('net_demand_*.csv'))

if len(net_demand_files) == 0:
    print("❌ Aucun fichier net_demand trouvé")
    exit(1)

print(f"Nombre de dates à traiter: {len(net_demand_files)}\n")

total_orders = 0
total_suppliers = set()
total_skus = 0
total_quantity = 0

# Traiter chaque date
for demand_file in net_demand_files:
    date_str = demand_file.stem.split('_')[-1]
    print(f"📅 Traitement du {date_str}...")
    
    # Lire net demand
    demand_df = pd.read_csv(demand_file)
    
    if len(demand_df) == 0:
        print(f"   ⚠ Aucune commande pour {date_str}")
        print()
        continue
    
    # Créer répertoire de sortie
    output_dir = output_base / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Grouper par fournisseur
    suppliers = demand_df.groupby('supplier_id')
    
    date_skus = len(demand_df)
    date_quantity = demand_df['order_quantity'].sum()
    
    for supplier_id, group in suppliers:
        total_suppliers.add(supplier_id)
        
        items = []
        for _, row in group.iterrows():
            items.append({
                'sku': row['sku'],
                'product_name': row['product_name'],
                'net_demand': int(row['net_demand']),
                'order_quantity': int(row['order_quantity'])
            })
        
        order = {
            'supplier_id': int(supplier_id),
            'order_date': date_str,
            'order_reference': f"ORD-{date_str}-SUP{int(supplier_id):03d}",
            'total_items': len(items),
            'total_quantity': sum(i['order_quantity'] for i in items),
            'items': items
        }
        
        filename = output_dir / f"supplier_{int(supplier_id):03d}_order_{date_str}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(order, f, indent=2, ensure_ascii=False)
        
        total_orders += 1
    
    total_skus += date_skus
    total_quantity += date_quantity
    
    print(f"   ✓ {len(suppliers)} fournisseurs, {date_skus} SKUs, {int(date_quantity)} unités")
    print()

print("\n" + "="*60)
print("📊 RÉSUMÉ GLOBAL")
print("="*60)
print(f"✅ Dates traitées: {len(net_demand_files)}")
print(f"✅ Fournisseurs distincts: {len(total_suppliers)}")
print(f"✅ Total fichiers générés: {total_orders}")
print(f"✅ Total SKUs commandés: {total_skus}")
print(f"✅ Total unités commandées: {int(total_quantity)}")
print(f"📁 Répertoire de sortie: {output_base}/")
print("="*60)