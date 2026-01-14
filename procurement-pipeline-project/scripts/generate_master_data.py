"""
Script de génération des Master Data
Génère les données pour: Suppliers, Warehouses, Products
"""

import pandas as pd
from faker import Faker
import random
import psycopg2
from psycopg2.extras import execute_batch
import yaml
import os

# Initialisation
fake = Faker('fr_FR')
Faker.seed(42)
random.seed(42)

# Chargement de la configuration
config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Configuration de la base de données
db_config = config['database']['postgresql']
data_gen_config = config['data_generation']

# Connexion à PostgreSQL
conn = psycopg2.connect(
    host=db_config['host'],
    port=db_config['port'],
    database=db_config['database'],
    user=db_config['user'],
    password=db_config['password']
)
cur = conn.cursor()

print("=== Génération des Master Data ===\n")

# 1. Génération des Suppliers
print("1. Génération des fournisseurs...")
suppliers = []
num_suppliers = data_gen_config['num_suppliers']

for i in range(1, num_suppliers + 1):
    supplier = {
        'supplier_name': fake.company(),
        'supplier_code': f'SUP{i:03d}',
        'contact_email': fake.company_email(),
        'contact_phone': fake.phone_number(),
        'lead_time_days': random.randint(1, 5)
    }
    suppliers.append(supplier)

# Insertion des suppliers
insert_supplier_query = """
    INSERT INTO suppliers (supplier_name, supplier_code, contact_email, contact_phone, lead_time_days)
    VALUES (%(supplier_name)s, %(supplier_code)s, %(contact_email)s, %(contact_phone)s, %(lead_time_days)s)
"""
execute_batch(cur, insert_supplier_query, suppliers)
conn.commit()
print(f"   ✓ {num_suppliers} fournisseurs créés")

# 2. Génération des Warehouses
print("\n2. Génération des entrepôts...")
warehouses = []
num_warehouses = data_gen_config['num_warehouses']
cities = ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Bordeaux', 'Nantes']

for i in range(1, num_warehouses + 1):
    warehouse = {
        'warehouse_name': f'Entrepôt {cities[i-1] if i <= len(cities) else fake.city()}',
        'warehouse_code': f'WH{i:02d}',
        'city': cities[i-1] if i <= len(cities) else fake.city(),
        'capacity': random.randint(10000, 50000)
    }
    warehouses.append(warehouse)

# Insertion des warehouses
insert_warehouse_query = """
    INSERT INTO warehouses (warehouse_name, warehouse_code, city, capacity)
    VALUES (%(warehouse_name)s, %(warehouse_code)s, %(city)s, %(capacity)s)
"""
execute_batch(cur, insert_warehouse_query, warehouses)
conn.commit()
print(f"   ✓ {num_warehouses} entrepôts créés")

# 3. Génération des Products
print("\n3. Génération des produits...")
products = []
num_products = data_gen_config['num_products']

categories = ['Fruits & Légumes', 'Viandes & Poissons', 'Produits Laitiers', 
              'Épicerie Salée', 'Épicerie Sucrée', 'Boissons', 'Surgelés', 
              'Hygiène & Beauté', 'Entretien', 'Bébé']

product_names = {
    'Fruits & Légumes': ['Pommes', 'Bananes', 'Tomates', 'Carottes', 'Laitue', 'Oranges'],
    'Viandes & Poissons': ['Poulet', 'Boeuf', 'Saumon', 'Thon', 'Porc', 'Crevettes'],
    'Produits Laitiers': ['Lait', 'Yaourt', 'Fromage', 'Beurre', 'Crème', 'Oeufs'],
    'Épicerie Salée': ['Pâtes', 'Riz', 'Huile', 'Sel', 'Conserves', 'Sauce tomate'],
    'Épicerie Sucrée': ['Chocolat', 'Biscuits', 'Confiture', 'Céréales', 'Miel', 'Sucre'],
    'Boissons': ['Eau', 'Jus', 'Soda', 'Café', 'Thé', 'Vin'],
    'Surgelés': ['Pizza', 'Glace', 'Légumes surgelés', 'Poisson pané', 'Frites'],
    'Hygiène & Beauté': ['Shampoing', 'Savon', 'Dentifrice', 'Déodorant', 'Crème'],
    'Entretien': ['Lessive', 'Liquide vaisselle', 'Éponges', 'Nettoyant', 'Papier toilette'],
    'Bébé': ['Couches', 'Lingettes', 'Lait infantile', 'Petits pots', 'Biberon']
}

for i in range(1, num_products + 1):
    category = random.choice(categories)
    product_name = random.choice(product_names.get(category, ['Produit']))
    
    product = {
        'sku': f'SKU{i:05d}',
        'product_name': f'{product_name} {fake.word().capitalize()}',
        'category': category,
        'supplier_id': random.randint(1, num_suppliers),
        'unit_price': round(random.uniform(0.5, 50.0), 2),
        'pack_size': random.choice([1, 6, 12, 24]),
        'case_size': random.choice([6, 12, 24, 48]),
        'min_order_quantity': random.choice([1, 2, 5, 10]),
        'safety_stock': random.randint(10, 100)
    }
    products.append(product)

# Insertion des products
insert_product_query = """
    INSERT INTO products (sku, product_name, category, supplier_id, unit_price, 
                         pack_size, case_size, min_order_quantity, safety_stock)
    VALUES (%(sku)s, %(product_name)s, %(category)s, %(supplier_id)s, %(unit_price)s,
            %(pack_size)s, %(case_size)s, %(min_order_quantity)s, %(safety_stock)s)
"""
execute_batch(cur, insert_product_query, products)
conn.commit()
print(f"   ✓ {num_products} produits créés")

# Fermeture de la connexion
cur.close()
conn.close()

print("\n=== Master Data générées avec succès ! ===")
print(f"Total: {num_suppliers} fournisseurs, {num_warehouses} entrepôts, {num_products} produits")