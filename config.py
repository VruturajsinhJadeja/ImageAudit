# config.py

# =============================================================================
# SUPERSET CONNECTION
# =============================================================================
SUPERSET_URL = "https://salesboard.salescode.ai"
USERNAME = "admin"
PASSWORD = "Magarpatta11!"

DB_ID = 35
DB_SCHEMA = "db_havellsdemo"

# =============================================================================
# QUERY & COLUMNS
# =============================================================================
COL_ID = "sku_code"

# Define the list of columns to validate
IMAGE_COLUMNS = [
    "blob_key", 
    "blob_key_a", 
    "blob_key_b", 
    "blob_key_c", 
    "blob_key_f", 
    "blob_key_l"
]

# Construct Query
_cols = ", ".join(IMAGE_COLUMNS)
SQL_QUERY = f"""
SELECT 
    {COL_ID}, 
    {_cols}
FROM 
    ck_productdetails 
"""

# =============================================================================
# VALIDATION THRESHOLDS
# =============================================================================
# 1. Size Constraints (KB)
CHECK_SIZE = True
MIN_SIZE_KB = 15
MAX_SIZE_KB = 50

# 2. Exact Dimension Constraints (Pixels)
CHECK_DIMS = True
EXPECTED_WIDTH = 500
EXPECTED_HEIGHT = 500

# =============================================================================
# SYSTEM
# =============================================================================
OUTPUT_FOLDER = "reports"
TIMEOUT_SECONDS = 15
MAX_THREADS = 10