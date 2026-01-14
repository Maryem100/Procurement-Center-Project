import os
import json
import subprocess
from datetime import datetime

ARCHIVE_DATE = datetime.now().strftime("%Y-%m-%d")

EXCEPTIONS_FILE = "/app/logs/exceptions_pipeline.json"

exceptions = {
    "date": ARCHIVE_DATE,
    "timestamp": datetime.now().isoformat(),
    "errors": [],
    "warnings": []
}

# ===================== HELPERS =====================
def hdfs_ls(path):
    try:
        result = subprocess.run(
            ["hadoop", "fs", "-ls", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            return []
        return result.stdout.strip().split("\n")[1:]
    except Exception:
        return []

def local_exists(path):
    return os.path.exists(path) and len(os.listdir(path)) > 0

# ===================== CHECK 1 : LOCAL ARCHIVE =====================
LOCAL_ARCHIVE = f"/app/output/archives/{ARCHIVE_DATE}"

if not os.path.exists(LOCAL_ARCHIVE):
    exceptions["errors"].append({
        "type": "LOCAL_ARCHIVE_MISSING",
        "message": f"Archive locale absente : {LOCAL_ARCHIVE}"
    })
elif not local_exists(LOCAL_ARCHIVE):
    exceptions["warnings"].append({
        "type": "LOCAL_ARCHIVE_EMPTY",
        "message": f"Archive locale vide : {LOCAL_ARCHIVE}"
    })

# ===================== CHECK 2 : SHARED VOLUME =====================
SHARED_ARCHIVE = f"/shared/archive/{ARCHIVE_DATE}"

if not os.path.exists(SHARED_ARCHIVE):
    exceptions["errors"].append({
        "type": "SHARED_ARCHIVE_MISSING",
        "message": f"Archive volume partagé absente : {SHARED_ARCHIVE}"
    })
elif not local_exists(SHARED_ARCHIVE):
    exceptions["warnings"].append({
        "type": "SHARED_ARCHIVE_EMPTY",
        "message": f"Archive volume partagé vide : {SHARED_ARCHIVE}"
    })

# ===================== CHECK 3 : HDFS RAW =====================
RAW_HDFS = f"/raw/orders/{ARCHIVE_DATE}"
raw_files = hdfs_ls(RAW_HDFS)

if not raw_files:
    exceptions["warnings"].append({
        "type": "HDFS_RAW_EMPTY",
        "message": f"Aucun fichier RAW détecté dans {RAW_HDFS}"
    })

# ===================== CHECK 4 : HDFS PROCESSED =====================
PROCESSED_HDFS = f"/processed/net_demand/{ARCHIVE_DATE}"
processed_files = hdfs_ls(PROCESSED_HDFS)

if not processed_files:
    exceptions["errors"].append({
        "type": "HDFS_PROCESSED_MISSING",
        "message": f"Données PROCESSED absentes dans {PROCESSED_HDFS}"
    })

# ===================== CHECK 5 : HDFS OUTPUT =====================
OUTPUT_HDFS = f"/output/supplier_orders/{ARCHIVE_DATE}"
output_files = hdfs_ls(OUTPUT_HDFS)

if not output_files:
    exceptions["errors"].append({
        "type": "HDFS_OUTPUT_MISSING",
        "message": f"Aucun fichier OUTPUT détecté dans {OUTPUT_HDFS}"
    })

# ===================== CHECK 6 : FICHIERS CRITIQUES =====================
required_files = [
    "net_demand.json",
    "supplier_a_orders.json",
    "supplier_b_orders.json",
    "supplier_c_orders.json"
]

if os.path.exists(LOCAL_ARCHIVE):
    existing_files = os.listdir(LOCAL_ARCHIVE)
    for file in required_files:
        if file not in existing_files:
            exceptions["errors"].append({
                "type": "MISSING_FILE",
                "message": f"Fichier critique manquant : {file}"
            })

# ===================== SAVE REPORT =====================
os.makedirs("/app/logs", exist_ok=True)

with open(EXCEPTIONS_FILE, "w") as f:
    json.dump(exceptions, f, indent=4, ensure_ascii=False)

# ===================== CONSOLE OUTPUT =====================
if exceptions["errors"]:
    print("❌ EXCEPTIONS CRITIQUES DÉTECTÉES")
    print(f"   Voir : {EXCEPTIONS_FILE}")
    exit(1)

if exceptions["warnings"]:
    print("⚠️ WARNINGS DÉTECTÉS")
    print(f"   Voir : {EXCEPTIONS_FILE}")

print("✅ Aucune exception critique détectée")
exit(0)
