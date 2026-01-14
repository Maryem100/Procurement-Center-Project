"""
Orchestration du pipeline - Transfert HDFS corrigé
Utilise webhdfs ou copy direct sans docker
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
import os

class ProcurementPipeline:
    
    def __init__(self):
        self.start_time = datetime.now()
        self.steps_completed = 0
        self.total_steps = 6
        # Configuration HDFS
        self.hdfs_host = os.getenv('HDFS_NAMENODE', 'namenode')
        self.hdfs_port = os.getenv('HDFS_PORT', '9000')
        
    def print_header(self):
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║          PIPELINE DE PROCUREMENT - EXÉCUTION COMPLÈTE        ║
║          Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}                         ║
║          HDFS: {self.hdfs_host}:{self.hdfs_port}
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def print_step(self, step_num, description):
        print(f"\n{'='*70}")
        print(f"  ÉTAPE {step_num}/{self.total_steps}: {description}")
        print(f"{'='*70}")
    
    def run_python_script(self, script_path):
        """Exécute un script Python"""
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout)
            if result.stderr:
                print(f"⚠️  Warnings: {result.stderr}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ ERREUR: {e.stderr}")
            return False
    
    def transfer_to_hdfs_subprocess(self, local_path, hdfs_path, description):
        """Transfère via subprocess en exécutant hadoop directement"""
        print(f"\n📤 Transfert vers HDFS: {description}")
        
        local_path = Path(local_path)
        if not local_path.exists():
            print(f"⚠️  Chemin local inexistant: {local_path}")
            return False
        
        try:
            # 1. Créer le répertoire HDFS
            cmd_mkdir = [
                'hadoop', 'fs', '-mkdir', '-p', hdfs_path
            ]
            result = subprocess.run(cmd_mkdir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  Erreur mkdir HDFS: {result.stderr}")
            else:
                print(f"   ✓ Répertoire créé: {hdfs_path}")
            
            # 2. Transférer les fichiers
            if local_path.is_dir():
                # Copier tous les fichiers du répertoire
                for file in local_path.glob('*'):
                    if file.is_file():
                        cmd_put = [
                            'hadoop', 'fs', '-put', '-f',
                            str(file), f"{hdfs_path}/"
                        ]
                        result = subprocess.run(cmd_put, capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"   ✓ {file.name} transféré")
                        else:
                            print(f"   ❌ Erreur transfert {file.name}: {result.stderr}")
            else:
                # Copier un seul fichier
                cmd_put = [
                    'hadoop', 'fs', '-put', '-f',
                    str(local_path), hdfs_path
                ]
                result = subprocess.run(cmd_put, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"   ✓ Fichier transféré: {local_path.name}")
                else:
                    print(f"   ❌ Erreur transfert: {result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    def verify_hdfs_content(self, hdfs_path):
        """Vérifie le contenu HDFS"""
        try:
            cmd = ['hadoop', 'fs', '-ls', hdfs_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                file_count = len([l for l in lines if l and not l.startswith('total')])
                print(f"   ✓ Vérification HDFS: {file_count} éléments dans {hdfs_path}")
                return True
            else:
                print(f"   ⚠️  Impossible de vérifier: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ⚠️  Erreur vérification: {e}")
            return False
    
    def run(self):
        """Exécute le pipeline complet"""
        self.print_header()
        
        # ÉTAPE 1: Agrégation des commandes
        self.print_step(1, "Agrégation des commandes clients")
        if self.run_python_script("scripts/transformation/aggregate_orders.py"):
            self.steps_completed += 1
            
            # Transfert vers HDFS
            if self.transfer_to_hdfs_subprocess(
                "data/processed/aggregated_orders",
                "/procurement/processed/aggregated_orders",
                "Commandes agrégées"
            ):
                self.verify_hdfs_content("/procurement/processed/aggregated_orders")
        
        # ÉTAPE 2: Calcul du net demand
        self.print_step(2, "Calcul du net demand")
        if self.run_python_script("scripts/transformation/calculate_net_demand.py"):
            self.steps_completed += 1
            
            # Transfert vers HDFS
            if self.transfer_to_hdfs_subprocess(
                "data/processed/net_demand",
                "/procurement/processed/net_demand",
                "Net demand"
            ):
                self.verify_hdfs_content("/procurement/processed/net_demand")
        
        # ÉTAPE 3: Génération des commandes fournisseurs
        self.print_step(3, "Génération des commandes fournisseurs")
        if self.run_python_script("scripts/transformation/generate_supplier_orders.py"):
            self.steps_completed += 1
            
            # Transfert vers HDFS
            if self.transfer_to_hdfs_subprocess(
                "data/output/supplier_orders",
                "/procurement/output/supplier_orders",
                "Commandes fournisseurs"
            ):
                self.verify_hdfs_content("/procurement/output/supplier_orders")
        
        # ÉTAPE 4: Vérification finale HDFS
        self.print_step(4, "Vérification de l'architecture HDFS complète")
        try:
            cmd = ['hadoop', 'fs', '-du', '-h', '/procurement']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
                self.steps_completed += 1
        except Exception as e:
            print(f"⚠️  Erreur vérification: {e}")
        
        # ÉTAPE 5: Résumé des fichiers générés
        self.print_step(5, "Résumé des fichiers générés")
        self.print_summary()
        self.steps_completed += 1
        
        # ÉTAPE 6: Statistiques finales
        self.print_step(6, "Statistiques du pipeline")
        self.print_final_stats()
        self.steps_completed += 1
        
        # Résumé final
        self.print_final_summary()
    
    def print_summary(self):
        """Affiche un résumé des fichiers générés"""
        
        # Compter les fichiers locaux
        agg_path = Path("data/processed/aggregated_orders")
        demand_path = Path("data/processed/net_demand")
        orders_path = Path("data/output/supplier_orders")
        
        agg_files = len(list(agg_path.glob("*.csv"))) if agg_path.exists() else 0
        demand_files = len(list(demand_path.glob("*.csv"))) if demand_path.exists() else 0
        order_files = len(list(orders_path.glob("*.json"))) if orders_path.exists() else 0
        
        print(f"""
📊 Fichiers générés:
   • Commandes agrégées: {agg_files} fichiers
   • Net demand: {demand_files} fichiers
   • Commandes fournisseurs: {order_files} fichiers JSON
        """)
    
    def print_final_stats(self):
        """Affiche les statistiques finales"""
        
        net_demand_path = Path("data/processed/net_demand")
        net_demand_files = sorted(net_demand_path.glob("*.csv")) if net_demand_path.exists() else []
        
        total_skus = 0
        total_quantity = 0
        
        try:
            import pandas as pd
            for f in net_demand_files:
                df = pd.read_csv(f)
                if len(df) > 0:
                    total_skus += len(df)
                    if 'order_quantity' in df.columns:
                        total_quantity += df['order_quantity'].sum()
        except Exception as e:
            print(f"⚠️  Erreur lecture stats: {e}")
        
        print(f"""
📈 Statistiques du pipeline:
   • Total SKUs commandés: {total_skus}
   • Total unités commandées: {int(total_quantity)}
   • Dates traitées: {len(net_demand_files)}
        """)
    
    def print_final_summary(self):
        """Affiche le résumé final"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    RÉSUMÉ FINAL                              ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ Étapes complétées: {self.steps_completed}/{self.total_steps}                                ║
║  ⏱️  Durée totale: {duration:.2f} secondes                            ║
║  📅 Date de fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}                     ║
╠══════════════════════════════════════════════════════════════╣
║  📁 Données stockées dans:                                   ║
║     • Local: data/processed/ et data/output/                 ║
║     • HDFS: /procurement/processed/ et /procurement/output/  ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        if self.steps_completed == self.total_steps:
            print("\n🎉 PIPELINE EXÉCUTÉ AVEC SUCCÈS ! 🎉\n")
        else:
            print(f"\n⚠️  Pipeline complété avec {self.total_steps - self.steps_completed} erreur(s)\n")

if __name__ == "__main__":
    pipeline = ProcurementPipeline()
    try:
        pipeline.run()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)